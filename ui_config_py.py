"""UI Configuration and scaling utilities."""

from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont, QFontDatabase
import platform


class UIConfig:
    """UI configuration manager."""
    
    def __init__(self):
        self.settings = QSettings("Transcriber", "AudioVideoTranscriber")
        
        # Default values
        self.defaults = {
            'ui_scale': 1.0,
            'theme': 'dark',
            'animations_enabled': True,
            'notifications_enabled': True,
            'font_size': 14,
            'font_family': 'Segoe UI' if platform.system() == 'Windows' else 'SF Pro Display',
        }
        
    def get(self, key, default=None):
        """Get configuration value."""
        if default is None:
            default = self.defaults.get(key)
        return self.settings.value(key, default)
        
    def set(self, key, value):
        """Set configuration value."""
        self.settings.setValue(key, value)
        
    def get_ui_scale(self):
        """Get UI scale factor."""
        return float(self.get('ui_scale', 1.0))
        
    def set_ui_scale(self, scale):
        """Set UI scale factor."""
        self.set('ui_scale', scale)
        
    def get_scaled_size(self, base_size):
        """Get scaled size based on UI scale factor."""
        return int(base_size * self.get_ui_scale())
        
    def get_font(self, size_adjustment=0):
        """Get configured font with optional size adjustment."""
        font = QFont(self.get('font_family'))
        base_size = int(self.get('font_size'))
        scaled_size = self.get_scaled_size(base_size + size_adjustment)
        font.setPointSize(scaled_size)
        return font
        
    def apply_scaling_to_widget(self, widget):
        """Apply UI scaling to a widget and its children."""
        scale = self.get_ui_scale()
        
        # Scale fonts
        font = widget.font()
        font.setPointSize(int(font.pointSize() * scale))
        widget.setFont(font)
        
        # Scale minimum sizes
        if hasattr(widget, 'minimumSize'):
            min_size = widget.minimumSize()
            if min_size.width() > 0:
                widget.setMinimumWidth(int(min_size.width() * scale))
            if min_size.height() > 0:
                widget.setMinimumHeight(int(min_size.height() * scale))
                
        # Apply to children
        for child in widget.findChildren(QWidget):
            self.apply_scaling_to_widget(child)
            
    def is_dark_theme(self):
        """Check if dark theme is enabled."""
        return self.get('theme') == 'dark'
        
    def toggle_theme(self):
        """Toggle between dark and light themes."""
        current = self.get('theme')
        new_theme = 'light' if current == 'dark' else 'dark'
        self.set('theme', new_theme)
        return new_theme
        
    def are_animations_enabled(self):
        """Check if animations are enabled."""
        return bool(self.get('animations_enabled', True))
        
    def are_notifications_enabled(self):
        """Check if notifications are enabled."""
        return bool(self.get('notifications_enabled', True))