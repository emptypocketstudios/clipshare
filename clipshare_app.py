#!/usr/bin/env python3
"""
ClipShare Application - Main application orchestrator.
"""

import argparse
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from clipboard_manager import ClipboardManager
from network_manager import NetworkManager
from gui_components import ConfigTab, ActivityTab, ClipboardTab, ClientTab
from tray_manager import TrayManager


class ClipShareApp:
    """Main ClipShare application."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ClipShare - Clipboard Network Sharing")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Network manager
        self.network_manager = NetworkManager(
            gui_callback=self.network_callback,
            client_callback=self.client_callback,
            consume_clipboard=True
        )
        
        # Tray manager
        self.tray_manager = TrayManager(
            self.show_window,
            self.hide_window,
            self.quit_application
        )
        
        # Configuration
        self.listen_port: Optional[int] = None
        self.peer_host: Optional[str] = None
        self.peer_port: Optional[int] = None
        self.monitor_interval: float = 1.0
        self.is_monitoring = False
        self.is_serving = False
        
        # Status
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        
        # Clipboard monitoring
        self.current_clipboard = ""
        self.clipboard_monitor_thread = None
        self.clipboard_monitor_running = False
        
        # Client management
        self.client_tab = None
        
        # Setup UI
        self.setup_ui()
        
        # Start efficient clipboard monitoring
        self.start_clipboard_monitor()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Configure grid weights for resizable layout
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Configuration tab
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Configuration")
        self.config_tab = ConfigTab(
            config_frame,
            self.toggle_server,
            self.toggle_monitoring,
            self.minimize_to_tray
        )
        
        # Activity tab
        activity_frame = ttk.Frame(notebook)
        notebook.add(activity_frame, text="Activity Log")
        self.activity_tab = ActivityTab(activity_frame, self.clear_activity_log)
        
        # Clipboard tab
        clipboard_frame = ttk.Frame(notebook)
        notebook.add(clipboard_frame, text="Clipboard Content")
        self.clipboard_tab = ClipboardTab(
            clipboard_frame,
            self.refresh_clipboard,
            self.clear_clipboard
        )
        
        # Client tab
        client_frame = ttk.Frame(notebook)
        notebook.add(client_frame, text="Clients")
        self.client_tab = ClientTab(client_frame)
        
        # Status bar
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=1, column=0, sticky="ew", padx=10)
    
    def start_clipboard_monitor(self):
        """Start efficient clipboard monitoring in background thread."""
        if not self.clipboard_monitor_running:
            self.clipboard_monitor_running = True
            self.clipboard_monitor_thread = threading.Thread(
                target=self._clipboard_monitor_loop,
                daemon=True
            )
            self.clipboard_monitor_thread.start()
    
    def _clipboard_monitor_loop(self):
        """Background thread for clipboard monitoring."""
        while self.clipboard_monitor_running:
            try:
                new_content = ClipboardManager.get_clipboard()
                if new_content != self.current_clipboard:
                    self.current_clipboard = new_content
                    # Update GUI in main thread
                    self.root.after(0, lambda: self.clipboard_tab.update_clipboard_display(new_content))
            except Exception as e:
                print(f"Error in clipboard monitoring: {e}")
            
            # Sleep to reduce CPU usage
            time.sleep(1.5)
    
    def stop_clipboard_monitor(self):
        """Stop clipboard monitoring."""
        self.clipboard_monitor_running = False
        if self.clipboard_monitor_thread and self.clipboard_monitor_thread.is_alive():
            self.clipboard_monitor_thread.join(timeout=1)
    
    def toggle_server(self):
        """Toggle the server on/off."""
        if not self.is_serving:
            try:
                port = int(self.config_tab.listen_port_var.get())
                self.listen_port = port
                
                # Update network manager with current clipboard consumption setting
                self.network_manager.consume_clipboard = self.config_tab.consume_clipboard_var.get()
                
                threading.Thread(target=self.network_manager.server_thread, args=(port,), daemon=True).start()
                self.is_serving = True
                self.config_tab.update_server_button(True)
                self.status_var.set(f"Server listening on port {port}")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid port number")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start server: {str(e)}")
        else:
            self.is_serving = False
            self.config_tab.update_server_button(False)
            self.status_var.set("Server stopped")
    
    def toggle_monitoring(self):
        """Toggle clipboard monitoring on/off."""
        if not self.is_monitoring:
            peer_addr = self.config_tab.peer_var.get().strip()
            if not peer_addr:
                messagebox.showerror("Error", "Please enter peer address (host:port)")
                return
            
            try:
                host, port_str = peer_addr.rsplit(":", 1)
                port = int(port_str)
                interval = float(self.config_tab.interval_var.get())
                
                self.peer_host = host
                self.peer_port = port
                self.monitor_interval = interval
                
                threading.Thread(
                    target=self.network_manager.monitor_clipboard,
                    args=(host, port, interval),
                    daemon=True
                ).start()
                
                self.is_monitoring = True
                self.config_tab.update_monitor_button(True)
                self.status_var.set(f"Monitoring clipboard, sending to {host}:{port}")
                
            except ValueError:
                messagebox.showerror("Error", "Invalid peer address format. Use host:port")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start monitoring: {str(e)}")
        else:
            self.is_monitoring = False
            self.config_tab.update_monitor_button(False)
            self.status_var.set("Monitoring stopped")
    
    def network_callback(self, event_type: str, peer: str, size: int):
        """Callback for network events."""
        timestamp = time.strftime("%H:%M:%S")
        
        if event_type == "sent":
            self.activity_tab.add_activity_log(timestamp, "Sent", peer, f"{size} bytes")
        elif event_type == "received":
            self.activity_tab.add_activity_log(timestamp, "Received", peer, f"{size} bytes")
            # Update clipboard display when we receive data
            self.root.after(100, self.refresh_clipboard)
        elif event_type == "server_started":
            self.activity_tab.add_activity_log(timestamp, "Server Started", peer, "-")
        elif event_type == "error":
            self.activity_tab.add_activity_log(timestamp, "Error", peer, "-")
    
    def client_callback(self, event_type: str, client_addr: str, content: str):
        """Callback for client management events."""
        if self.client_tab:
            if event_type == "add":
                self.client_tab.add_client(client_addr, content)
            elif event_type == "update":
                self.client_tab.update_client_content(client_addr, content)
            elif event_type == "remove":
                self.client_tab.remove_client(client_addr)
    
    def clear_activity_log(self):
        """Clear the activity log."""
        self.activity_tab.clear_activity_log()
    
    def refresh_clipboard(self):
        """Manually refresh clipboard content."""
        try:
            new_content = ClipboardManager.get_clipboard()
            self.current_clipboard = new_content
            self.clipboard_tab.update_clipboard_display(new_content)
        except Exception as e:
            print(f"Error refreshing clipboard: {e}")
    
    def clear_clipboard(self):
        """Clear the clipboard."""
        ClipboardManager.set_clipboard("")
        self.refresh_clipboard()
    
    def minimize_to_tray(self):
        """Minimize application to system tray."""
        self.tray_manager.start_tray()
        self.root.withdraw()
    
    def show_window(self, icon=None, item=None):
        """Show the main window."""
        self.root.after(0, self.root.deiconify)
    
    def hide_window(self, icon=None, item=None):
        """Hide the main window."""
        self.root.after(0, self.root.withdraw)
    
    def quit_application(self, icon=None, item=None):
        """Quit the application."""
        self.stop_clipboard_monitor()
        self.tray_manager.stop_tray()
        self.root.after(0, self.root.quit)
    
    def on_closing(self):
        """Handle window closing event."""
        if messagebox.askyesno("Quit", "Do you want to minimize to tray instead of quitting?"):
            self.minimize_to_tray()
        else:
            self.quit_application()
    
    def run(self):
        """Run the GUI application."""
        try:
            self.root.mainloop()
        finally:
            self.stop_clipboard_monitor()


def main():
    """Main function with command line argument support."""
    parser = argparse.ArgumentParser(description="ClipShare - Share clipboard contents over the network")
    parser.add_argument("--listen", type=int, metavar="PORT", help="Port to listen for incoming updates")
    parser.add_argument("--peer", metavar="HOST:PORT", help="Send clipboard changes to this peer")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--no-gui", action="store_true", help="Run without GUI (CLI mode)")
    
    args = parser.parse_args()
    
    if args.no_gui:
        # Run CLI version
        if args.listen is None and args.peer is None:
            parser.error("must specify --listen and/or --peer")
        
        network_manager = NetworkManager()
        
        if args.listen is not None:
            threading.Thread(target=network_manager.server_thread, args=(args.listen,), daemon=True).start()
        
        if args.peer:
            host, sep, p = args.peer.rpartition(":")
            if not sep:
                parser.error("--peer must be in HOST:PORT format")
            network_manager.monitor_clipboard(host, int(p), args.interval)
        else:
            # If only listening, keep the main thread alive.
            while True:
                time.sleep(1)
        return
    
    # Run GUI version
    app = ClipShareApp()
    
    # Set initial values from command line
    if args.listen:
        app.config_tab.listen_port_var.set(str(args.listen))
    if args.peer:
        app.config_tab.peer_var.set(args.peer)
    if args.interval:
        app.config_tab.interval_var.set(str(args.interval))
    
    # Auto-start if arguments provided
    if args.listen:
        app.root.after(100, app.toggle_server)
    if args.peer:
        app.root.after(200, app.toggle_monitoring)
    
    app.run()


if __name__ == "__main__":
    main() 