#!/usr/bin/env python3
"""
Tray Manager - Handles system tray functionality.
"""

import threading
import pystray
from PIL import Image, ImageDraw


class TrayManager:
    """Manages system tray icon and menu."""
    
    def __init__(self, show_callback, hide_callback, quit_callback):
        self.show_callback = show_callback
        self.hide_callback = hide_callback
        self.quit_callback = quit_callback
        self.tray_icon = None
        self.tray_thread = None
    
    def create_tray_icon(self):
        """Create system tray icon."""
        # Create a simple icon
        image = Image.new('RGB', (64, 64), color='blue')
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill='white')
        draw.text((20, 25), "CS", fill='blue')
        
        menu = pystray.Menu(
            pystray.MenuItem("Show", self.show_callback),
            pystray.MenuItem("Hide", self.hide_callback),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.quit_callback)
        )
        
        self.tray_icon = pystray.Icon("clipshare", image, "ClipShare", menu)
    
    def start_tray(self):
        """Start the system tray icon."""
        if self.tray_icon is None:
            self.create_tray_icon()
        
        if self.tray_thread is None or not self.tray_thread.is_alive():
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()
    
    def stop_tray(self):
        """Stop the system tray icon."""
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None 