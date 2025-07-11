#!/usr/bin/env python3
"""
GUI Components - UI components for the ClipShare application.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
from typing import Optional, Dict
from clipboard_manager import ClipboardManager


class ConfigTab:
    """Configuration tab component."""
    
    def __init__(self, parent, toggle_server_callback, toggle_monitoring_callback, minimize_to_tray_callback):
        self.parent = parent
        self.toggle_server_callback = toggle_server_callback
        self.toggle_monitoring_callback = toggle_monitoring_callback
        self.minimize_to_tray_callback = minimize_to_tray_callback
        
        # Variables
        self.listen_port_var = tk.StringVar()
        self.peer_var = tk.StringVar()
        self.interval_var = tk.StringVar(value="1.0")
        self.consume_clipboard_var = tk.BooleanVar(value=True)
        
        # Buttons
        self.listen_button = None
        self.monitor_button = None
        self.tray_button = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the configuration tab UI."""
        # Configure grid weights for resizable layout
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)
        
        # Create canvas with scrollbar for scrollable content
        canvas = tk.Canvas(self.parent)
        scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Main container frame
        main_frame = ttk.Frame(scrollable_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Listen section
        listen_frame = ttk.LabelFrame(main_frame, text="Server Configuration", padding=10)
        listen_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        listen_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(listen_frame, text="Listen Port:").grid(row=0, column=0, sticky=tk.W, padx=5)
        listen_entry = ttk.Entry(listen_frame, textvariable=self.listen_port_var, width=10)
        listen_entry.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.listen_button = ttk.Button(listen_frame, text="Start Server", command=self.toggle_server_callback)
        self.listen_button.grid(row=0, column=2, padx=10)
        
        # Clipboard consumption checkbox
        consume_check = ttk.Checkbutton(
            listen_frame, 
            text="Consume clipboard content from clients", 
            variable=self.consume_clipboard_var
        )
        consume_check.grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=5)
        
        # Peer section
        peer_frame = ttk.LabelFrame(main_frame, text="Peer Configuration", padding=10)
        peer_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        peer_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(peer_frame, text="Peer Address:").grid(row=0, column=0, sticky=tk.W, padx=5)
        peer_entry = ttk.Entry(peer_frame, textvariable=self.peer_var, width=20)
        peer_entry.grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Label(peer_frame, text="Interval (s):").grid(row=1, column=0, sticky=tk.W, padx=5)
        interval_entry = ttk.Entry(peer_frame, textvariable=self.interval_var, width=10)
        interval_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        self.monitor_button = ttk.Button(peer_frame, text="Start Monitoring", command=self.toggle_monitoring_callback)
        self.monitor_button.grid(row=0, column=2, rowspan=2, padx=10)
        
        # System tray section
        tray_frame = ttk.LabelFrame(main_frame, text="System Tray", padding=10)
        tray_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        self.tray_button = ttk.Button(tray_frame, text="Minimize to Tray", command=self.minimize_to_tray_callback)
        self.tray_button.pack(side=tk.LEFT, padx=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def update_server_button(self, is_serving: bool):
        """Update server button text."""
        if self.listen_button:
            self.listen_button.config(text="Stop Server" if is_serving else "Start Server")
    
    def update_monitor_button(self, is_monitoring: bool):
        """Update monitor button text."""
        if self.monitor_button:
            self.monitor_button.config(text="Stop Monitoring" if is_monitoring else "Start Monitoring")


class ActivityTab:
    """Activity log tab component."""
    
    def __init__(self, parent, clear_log_callback):
        self.parent = parent
        self.clear_log_callback = clear_log_callback
        self.activity_tree = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the activity log tab UI."""
        # Configure grid weights for resizable layout
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)
        
        # Activity log
        log_frame = ttk.Frame(self.parent)
        log_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(log_frame, text="Network Activity:").grid(row=0, column=0, sticky="w")
        
        # Create treeview for activity log
        tree_frame = ttk.Frame(log_frame)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        columns = ("Time", "Type", "Peer", "Size")
        self.activity_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.activity_tree.heading(col, text=col)
            # Make columns stretch to fill available width
            if col == "Peer":
                self.activity_tree.column(col, width=200, stretch=True)
            else:
                self.activity_tree.column(col, width=100, stretch=True)
        
        # Vertical scrollbar for treeview
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.activity_tree.yview)
        self.activity_tree.configure(yscrollcommand=v_scrollbar.set)
        
        self.activity_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Clear button
        clear_button = ttk.Button(self.parent, text="Clear Log", command=self.clear_log_callback)
        clear_button.grid(row=1, column=0, pady=5)
    
    def add_activity_log(self, timestamp: str, event_type: str, peer: str, size: str):
        """Add entry to activity log."""
        if self.activity_tree:
            self.activity_tree.insert("", "end", values=(timestamp, event_type, peer, size))
    
    def clear_activity_log(self):
        """Clear the activity log."""
        if self.activity_tree:
            for item in self.activity_tree.get_children():
                self.activity_tree.delete(item)


class ClipboardTab:
    """Clipboard content tab component."""
    
    def __init__(self, parent, refresh_callback, clear_callback):
        self.parent = parent
        self.refresh_callback = refresh_callback
        self.clear_callback = clear_callback
        self.clipboard_text = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the clipboard content tab UI."""
        # Configure grid weights for resizable layout
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)
        
        clipboard_frame = ttk.Frame(self.parent)
        clipboard_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        clipboard_frame.grid_rowconfigure(1, weight=1)
        clipboard_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(clipboard_frame, text="Current Clipboard Content:").grid(row=0, column=0, sticky="w")
        
        # Create text widget with vertical scrollbar
        text_frame = ttk.Frame(clipboard_frame)
        text_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        self.clipboard_text = tk.Text(text_frame, wrap=tk.WORD, undo=True, width=80)
        
        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.clipboard_text.yview)
        self.clipboard_text.configure(yscrollcommand=v_scrollbar.set)
        
        self.clipboard_text.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Buttons
        button_frame = ttk.Frame(clipboard_frame)
        button_frame.grid(row=2, column=0, sticky="ew", pady=5)
        
        ttk.Button(button_frame, text="Refresh", command=self.refresh_callback).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Clipboard", command=self.clear_callback).pack(side=tk.LEFT, padx=5)
    
    def update_clipboard_display(self, content: str):
        """Update the clipboard content display."""
        if self.clipboard_text:
            self.clipboard_text.delete(1.0, tk.END)
            self.clipboard_text.insert(1.0, content)


class ClientTab:
    """Client management tab component."""
    
    def __init__(self, parent):
        self.parent = parent
        self.clients: Dict[str, str] = {}  # client_addr -> clipboard_content
        self.client_tree = None
        self.content_text = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the client management tab UI."""
        # Configure grid weights for resizable layout
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)
        
        # Main frame with split view
        main_frame = ttk.Frame(self.parent)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Left panel - Client list
        left_frame = ttk.LabelFrame(main_frame, text="Connected Clients", padding=5)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Client treeview
        columns = ("Address", "Last Update")
        self.client_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.client_tree.heading(col, text=col)
            if col == "Address":
                self.client_tree.column(col, width=150, stretch=True)
            else:
                self.client_tree.column(col, width=120, stretch=True)
        
        # Vertical scrollbar for client tree
        v_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.client_tree.yview)
        self.client_tree.configure(yscrollcommand=v_scrollbar.set)
        
        self.client_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bind selection event
        self.client_tree.bind("<<TreeviewSelect>>", self.on_client_select)
        
        # Right panel - Client clipboard content
        right_frame = ttk.LabelFrame(main_frame, text="Client Clipboard Content", padding=5)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Content text widget
        text_frame = ttk.Frame(right_frame)
        text_frame.grid(row=0, column=0, sticky="nsew")
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        self.content_text = tk.Text(text_frame, wrap=tk.WORD, undo=True, width=60)
        
        # Vertical scrollbar for content
        content_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=content_scrollbar.set)
        
        self.content_text.grid(row=0, column=0, sticky="nsew")
        content_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Buttons frame
        button_frame = ttk.Frame(self.parent)
        button_frame.grid(row=1, column=0, columnspan=2, pady=5)
        
        ttk.Button(button_frame, text="Refresh All", command=self.refresh_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
    
    def add_client(self, client_addr: str, clipboard_content: str = ""):
        """Add or update a client."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.clients[client_addr] = clipboard_content
        
        # Update treeview
        if self.client_tree:
            # Check if client already exists
            for item in self.client_tree.get_children():
                if self.client_tree.item(item, "values")[0] == client_addr:
                    self.client_tree.delete(item)
                    break
            
            self.client_tree.insert("", "end", values=(client_addr, timestamp))
    
    def remove_client(self, client_addr: str):
        """Remove a client."""
        if client_addr in self.clients:
            del self.clients[client_addr]
        
        # Update treeview
        if self.client_tree:
            for item in self.client_tree.get_children():
                if self.client_tree.item(item, "values")[0] == client_addr:
                    self.client_tree.delete(item)
                    break
    
    def update_client_content(self, client_addr: str, clipboard_content: str):
        """Update clipboard content for a specific client."""
        if client_addr in self.clients:
            self.clients[client_addr] = clipboard_content
            self.add_client(client_addr, clipboard_content)  # This will update the timestamp
    
    def on_client_select(self, event):
        """Handle client selection."""
        if self.client_tree and self.content_text:
            selection = self.client_tree.selection()
            if selection:
                client_addr = self.client_tree.item(selection[0], "values")[0]
                content = self.clients.get(client_addr, "")
                self.content_text.delete(1.0, tk.END)
                self.content_text.insert(1.0, content)
    
    def refresh_all(self):
        """Refresh all client data."""
        # This could be extended to request fresh data from clients
        pass
    
    def clear_all(self):
        """Clear all client data."""
        self.clients.clear()
        if self.client_tree:
            for item in self.client_tree.get_children():
                self.client_tree.delete(item)
        if self.content_text:
            self.content_text.delete(1.0, tk.END) 