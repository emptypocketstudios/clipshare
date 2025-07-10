#!/usr/bin/env python3
"""
ClipShare GUI - A clipboard sharing application with system tray support.
"""

import argparse
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
from typing import Optional, List, Tuple
import queue
import io
import pystray
from PIL import Image, ImageDraw


class ClipboardManager:
    """Handles clipboard operations for different platforms."""
    
    @staticmethod
    def get_clipboard() -> str:
        """Return current clipboard contents."""
        if sys.platform.startswith("linux"):
            try:
                result = subprocess.run([
                    "wl-paste",
                    "-n",
                ], capture_output=True, text=True, check=True)
                return result.stdout
            except (subprocess.CalledProcessError, FileNotFoundError):
                return ""
        elif sys.platform.startswith("win"):
            try:
                result = subprocess.run(
                    ["powershell", "-command", "Get-Clipboard"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return result.stdout
            except (subprocess.CalledProcessError, FileNotFoundError):
                return ""
        else:
            raise NotImplementedError("Unsupported platform")

    @staticmethod
    def set_clipboard(text: str) -> None:
        """Set clipboard contents to text."""
        if sys.platform.startswith("linux"):
            try:
                subprocess.run([
                    "wl-copy",
                ], input=text, text=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        elif sys.platform.startswith("win"):
            try:
                subprocess.run(
                    ["powershell", "-command", "Set-Clipboard"],
                    input=text,
                    text=True,
                    check=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        else:
            raise NotImplementedError("Unsupported platform")


class NetworkManager:
    """Handles network operations for clipboard sharing."""
    
    def __init__(self, gui_callback=None):
        self.gui_callback = gui_callback
    
    def send_clipboard(self, host: str, port: int, text: str) -> bool:
        """Send clipboard text to remote host."""
        try:
            data = text.encode("utf-8")
            length = len(data).to_bytes(4, "big")
            with socket.create_connection((host, port), timeout=5) as sock:
                sock.sendall(length)
                sock.sendall(data)
            
            if self.gui_callback:
                self.gui_callback("sent", f"{host}:{port}", len(text))
            return True
        except Exception as e:
            if self.gui_callback:
                self.gui_callback("error", f"Failed to send to {host}:{port}: {str(e)}", 0)
            return False

    def server_thread(self, port: int) -> None:
        """Listen for clipboard updates on the given port."""
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("", port))
            srv.listen()
            
            if self.gui_callback:
                self.gui_callback("server_started", f"Port {port}", 0)
            
            while True:
                conn, addr = srv.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
        except Exception as e:
            if self.gui_callback:
                self.gui_callback("error", f"Server error on port {port}: {str(e)}", 0)

    def handle_client(self, conn: socket.socket, addr) -> None:
        """Receive clipboard data from a connection."""
        try:
            with conn:
                header = conn.recv(4)
                if not header:
                    return
                size = int.from_bytes(header, "big")
                data = b""
                while len(data) < size:
                    packet = conn.recv(size - len(data))
                    if not packet:
                        break
                    data += packet
                text = data.decode("utf-8", errors="replace")
                ClipboardManager.set_clipboard(text)
                
                if self.gui_callback:
                    self.gui_callback("received", f"{addr[0]}:{addr[1]}", len(text))
        except Exception as e:
            if self.gui_callback:
                self.gui_callback("error", f"Error handling client {addr}: {str(e)}", 0)

    def monitor_clipboard(self, host: str, port: int, interval: float = 1.0) -> None:
        """Monitor clipboard and send updates to host."""
        current = ClipboardManager.get_clipboard()
        while True:
            time.sleep(interval)
            new = ClipboardManager.get_clipboard()
            if new != current:
                self.send_clipboard(host, port, new)
                current = new


class ClipShareGUI:
    """Main GUI application for ClipShare."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ClipShare - Clipboard Network Sharing")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Network manager
        self.network_manager = NetworkManager(self.network_callback)
        
        # Configuration
        self.listen_port: Optional[int] = None
        self.peer_host: Optional[str] = None
        self.peer_port: Optional[int] = None
        self.monitor_interval: float = 1.0
        self.is_monitoring = False
        self.is_serving = False
        
        # System tray
        self.tray_icon = None
        
        # Setup UI
        self.setup_ui()
        
        # Start clipboard monitoring for display
        self.current_clipboard = ""
        self.update_clipboard_display()
        
    def setup_ui(self):
        """Setup the user interface."""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configuration tab
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Configuration")
        self.setup_config_tab(config_frame)
        
        # Activity tab
        activity_frame = ttk.Frame(notebook)
        notebook.add(activity_frame, text="Activity Log")
        self.setup_activity_tab(activity_frame)
        
        # Clipboard tab
        clipboard_frame = ttk.Frame(notebook)
        notebook.add(clipboard_frame, text="Clipboard Content")
        self.setup_clipboard_tab(clipboard_frame)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_config_tab(self, parent):
        """Setup the configuration tab."""
        # Listen section
        listen_frame = ttk.LabelFrame(parent, text="Server Configuration", padding=10)
        listen_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(listen_frame, text="Listen Port:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.listen_port_var = tk.StringVar()
        listen_entry = ttk.Entry(listen_frame, textvariable=self.listen_port_var, width=10)
        listen_entry.grid(row=0, column=1, padx=5)
        
        self.listen_button = ttk.Button(listen_frame, text="Start Server", command=self.toggle_server)
        self.listen_button.grid(row=0, column=2, padx=10)
        
        # Peer section
        peer_frame = ttk.LabelFrame(parent, text="Peer Configuration", padding=10)
        peer_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(peer_frame, text="Peer Address:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.peer_var = tk.StringVar()
        peer_entry = ttk.Entry(peer_frame, textvariable=self.peer_var, width=20)
        peer_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(peer_frame, text="Interval (s):").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.interval_var = tk.StringVar(value="1.0")
        interval_entry = ttk.Entry(peer_frame, textvariable=self.interval_var, width=10)
        interval_entry.grid(row=1, column=1, padx=5, pady=5)
        
        self.monitor_button = ttk.Button(peer_frame, text="Start Monitoring", command=self.toggle_monitoring)
        self.monitor_button.grid(row=0, column=2, rowspan=2, padx=10)
        
        # System tray section
        tray_frame = ttk.LabelFrame(parent, text="System Tray", padding=10)
        tray_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.tray_button = ttk.Button(tray_frame, text="Minimize to Tray", command=self.minimize_to_tray)
        self.tray_button.pack(side=tk.LEFT, padx=5)
        
    def setup_activity_tab(self, parent):
        """Setup the activity log tab."""
        # Activity log
        log_frame = ttk.Frame(parent)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(log_frame, text="Network Activity:").pack(anchor=tk.W)
        
        # Create treeview for activity log
        columns = ("Time", "Type", "Peer", "Size")
        self.activity_tree = ttk.Treeview(log_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.activity_tree.heading(col, text=col)
            self.activity_tree.column(col, width=150)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.activity_tree.yview)
        self.activity_tree.configure(yscrollcommand=scrollbar.set)
        
        self.activity_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Clear button
        clear_button = ttk.Button(parent, text="Clear Log", command=self.clear_activity_log)
        clear_button.pack(pady=5)
        
    def setup_clipboard_tab(self, parent):
        """Setup the clipboard content tab."""
        clipboard_frame = ttk.Frame(parent)
        clipboard_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(clipboard_frame, text="Current Clipboard Content:").pack(anchor=tk.W)
        
        self.clipboard_text = scrolledtext.ScrolledText(clipboard_frame, height=20, wrap=tk.WORD)
        self.clipboard_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(clipboard_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Refresh", command=self.refresh_clipboard).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Clipboard", command=self.clear_clipboard).pack(side=tk.LEFT, padx=5)
        
    def toggle_server(self):
        """Toggle the server on/off."""
        if not self.is_serving:
            try:
                port = int(self.listen_port_var.get())
                self.listen_port = port
                threading.Thread(target=self.network_manager.server_thread, args=(port,), daemon=True).start()
                self.is_serving = True
                self.listen_button.config(text="Stop Server")
                self.status_var.set(f"Server listening on port {port}")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid port number")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start server: {str(e)}")
        else:
            self.is_serving = False
            self.listen_button.config(text="Start Server")
            self.status_var.set("Server stopped")
            
    def toggle_monitoring(self):
        """Toggle clipboard monitoring on/off."""
        if not self.is_monitoring:
            peer_addr = self.peer_var.get().strip()
            if not peer_addr:
                messagebox.showerror("Error", "Please enter peer address (host:port)")
                return
                
            try:
                host, port_str = peer_addr.rsplit(":", 1)
                port = int(port_str)
                interval = float(self.interval_var.get())
                
                self.peer_host = host
                self.peer_port = port
                self.monitor_interval = interval
                
                threading.Thread(
                    target=self.network_manager.monitor_clipboard,
                    args=(host, port, interval),
                    daemon=True
                ).start()
                
                self.is_monitoring = True
                self.monitor_button.config(text="Stop Monitoring")
                self.status_var.set(f"Monitoring clipboard, sending to {host}:{port}")
                
            except ValueError:
                messagebox.showerror("Error", "Invalid peer address format. Use host:port")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start monitoring: {str(e)}")
        else:
            self.is_monitoring = False
            self.monitor_button.config(text="Start Monitoring")
            self.status_var.set("Monitoring stopped")
            
    def network_callback(self, event_type: str, peer: str, size: int):
        """Callback for network events."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if event_type == "sent":
            self.add_activity_log(timestamp, "Sent", peer, f"{size} bytes")
        elif event_type == "received":
            self.add_activity_log(timestamp, "Received", peer, f"{size} bytes")
            # Update clipboard display when we receive data
            self.root.after(100, self.update_clipboard_display)
        elif event_type == "server_started":
            self.add_activity_log(timestamp, "Server Started", peer, "-")
        elif event_type == "error":
            self.add_activity_log(timestamp, "Error", peer, "-")
            
    def add_activity_log(self, timestamp: str, event_type: str, peer: str, size: str):
        """Add entry to activity log."""
        # Use after() to ensure thread-safe GUI updates
        self.root.after(0, lambda: self.activity_tree.insert("", "end", values=(timestamp, event_type, peer, size)))
        
    def clear_activity_log(self):
        """Clear the activity log."""
        for item in self.activity_tree.get_children():
            self.activity_tree.delete(item)
            
    def update_clipboard_display(self):
        """Update the clipboard content display."""
        try:
            new_content = ClipboardManager.get_clipboard()
            if new_content != self.current_clipboard:
                self.current_clipboard = new_content
                self.clipboard_text.delete(1.0, tk.END)
                self.clipboard_text.insert(1.0, new_content)
        except Exception as e:
            print(f"Error updating clipboard display: {e}")
        
        # Schedule next update
        self.root.after(1000, self.update_clipboard_display)
        
    def refresh_clipboard(self):
        """Manually refresh clipboard content."""
        self.update_clipboard_display()
        
    def clear_clipboard(self):
        """Clear the clipboard."""
        ClipboardManager.set_clipboard("")
        self.update_clipboard_display()
        
    def create_tray_icon(self):
        """Create system tray icon."""
        # Create a simple icon
        image = Image.new('RGB', (64, 64), color='blue')
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill='white')
        draw.text((20, 25), "CS", fill='blue')
        
        menu = pystray.Menu(
            pystray.MenuItem("Show", self.show_window),
            pystray.MenuItem("Hide", self.hide_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.quit_application)
        )
        
        self.tray_icon = pystray.Icon("clipshare", image, "ClipShare", menu)
        
    def minimize_to_tray(self):
        """Minimize application to system tray."""
        if self.tray_icon is None:
            self.create_tray_icon()
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        
        self.root.withdraw()
        
    def show_window(self, icon=None, item=None):
        """Show the main window."""
        self.root.after(0, self.root.deiconify)
        
    def hide_window(self, icon=None, item=None):
        """Hide the main window."""
        self.root.after(0, self.root.withdraw)
        
    def quit_application(self, icon=None, item=None):
        """Quit the application."""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.quit)
        
    def on_closing(self):
        """Handle window closing event."""
        if messagebox.askyesno("Quit", "Do you want to minimize to tray instead of quitting?"):
            self.minimize_to_tray()
        else:
            self.quit_application()
            
    def run(self):
        """Run the GUI application."""
        self.root.mainloop()


def main():
    """Main function with command line argument support."""
    parser = argparse.ArgumentParser(description="ClipShare GUI - Share clipboard contents over the network")
    parser.add_argument("--listen", type=int, metavar="PORT", help="Port to listen for incoming updates")
    parser.add_argument("--peer", metavar="HOST:PORT", help="Send clipboard changes to this peer")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--no-gui", action="store_true", help="Run without GUI (original CLI mode)")
    
    args = parser.parse_args()
    
    if args.no_gui:
        # Import and run original CLI version
        import clipshare
        # Modify sys.argv to pass arguments to original script
        original_argv = sys.argv[:]
        sys.argv = ['clipshare.py']
        if args.listen:
            sys.argv.extend(['--listen', str(args.listen)])
        if args.peer:
            sys.argv.extend(['--peer', args.peer])
        if args.interval != 1.0:
            sys.argv.extend(['--interval', str(args.interval)])
        
        # Run original main
        parser_orig = argparse.ArgumentParser(description="Share clipboard contents over the network")
        parser_orig.add_argument("--listen", type=int, metavar="PORT", help="Port to listen for incoming updates")
        parser_orig.add_argument("--peer", metavar="HOST:PORT", help="Send clipboard changes to this peer")
        parser_orig.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")
        args_orig = parser_orig.parse_args()
        
        if args_orig.listen is None and args_orig.peer is None:
            parser_orig.error("must specify --listen and/or --peer")

        network_manager = NetworkManager()
        
        if args_orig.listen is not None:
            threading.Thread(target=network_manager.server_thread, args=(args_orig.listen,), daemon=True).start()

        if args_orig.peer:
            host, sep, p = args_orig.peer.rpartition(":")
            if not sep:
                parser_orig.error("--peer must be in HOST:PORT format")
            network_manager.monitor_clipboard(host, int(p), args_orig.interval)
        else:
            # If only listening, keep the main thread alive.
            while True:
                time.sleep(1)
        return
    
    # Run GUI version
    app = ClipShareGUI()
    
    # Set initial values from command line
    if args.listen:
        app.listen_port_var.set(str(args.listen))
    if args.peer:
        app.peer_var.set(args.peer)
    if args.interval:
        app.interval_var.set(str(args.interval))
    
    # Auto-start if arguments provided
    if args.listen:
        app.root.after(100, app.toggle_server)
    if args.peer:
        app.root.after(200, app.toggle_monitoring)
    
    app.run()


if __name__ == "__main__":
    main()