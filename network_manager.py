#!/usr/bin/env python3
"""
Network Manager - Handles network operations for clipboard sharing.
"""

import socket
import threading
import time
from typing import Optional, Callable
from clipboard_manager import ClipboardManager


class NetworkManager:
    """Handles network operations for clipboard sharing."""
    
    def __init__(self, gui_callback: Optional[Callable] = None, client_callback: Optional[Callable] = None, consume_clipboard: bool = True):
        self.gui_callback = gui_callback
        self.client_callback = client_callback
        self.consume_clipboard = consume_clipboard
        self.clients = {}  # Track connected clients
    
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
        client_addr = f"{addr[0]}:{addr[1]}"
        
        # Add client to tracking
        if self.client_callback:
            self.client_callback("add", client_addr, "")
        
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
                
                # Update client content
                if self.client_callback:
                    self.client_callback("update", client_addr, text)
                
                # Only set clipboard if consumption is enabled
                if self.consume_clipboard:
                    ClipboardManager.set_clipboard(text)
                
                if self.gui_callback:
                    self.gui_callback("received", client_addr, len(text))
        except Exception as e:
            if self.gui_callback:
                self.gui_callback("error", f"Error handling client {client_addr}: {str(e)}", 0)
        finally:
            # Remove client when connection closes
            if self.client_callback:
                self.client_callback("remove", client_addr, "")

    def monitor_clipboard(self, host: str, port: int, interval: float = 1.0) -> None:
        """Monitor clipboard and send updates to host."""
        current = ClipboardManager.get_clipboard()
        while True:
            time.sleep(interval)
            try:
                new = ClipboardManager.get_clipboard()
                if new != current and new.strip():  # Only send non-empty content
                    self.send_clipboard(host, port, new)
                    current = new
            except Exception as e:
                # Log error but continue monitoring
                if self.gui_callback:
                    self.gui_callback("error", f"Clipboard monitoring error: {str(e)}", 0)
                time.sleep(interval)  # Wait before retrying 