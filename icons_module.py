"""Icon management module using Unicode symbols and SVG icons."""

from PySide6.QtGui import QIcon, QPixmap, QPainter, QFont
from PySide6.QtCore import Qt, QSize
from PySide6.QtSvg import QSvgRenderer
import io


class Icons:
    """Provides icons for the application using Unicode symbols."""
    
    # Unicode symbols as constants
    PENDING = "⏳"
    PROCESSING = "⚙"
    COMPLETED = "✓"
    ERROR = "✗"
    NOT_FOUND = "?"
    
    FOLDER = "📁"
    FILE = "📄"
    AUDIO = "🎵"
    VIDEO = "🎬"
    
    START = "▶"
    STOP = "■"
    CLEAR = "🗑"
    BENCHMARK = "📊"
    
    SUCCESS = "✨"
    WARNING = "⚠"
    INFO = "ℹ"
    
    @staticmethod
    def create_svg_icon(svg_content: str, color: str = "#DFE6E9") -> QIcon:
        """Create QIcon from SVG content."""
        svg_bytes = svg_content.encode('utf-8')
        svg_renderer = QSvgRenderer(svg_bytes)
        
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        svg_renderer.render(painter)
        painter.end()
        
        return QIcon(pixmap)
    
    @staticmethod
    def get_file_icon() -> QIcon:
        """Get file icon."""
        svg = '''<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
        </svg>'''
        return Icons.create_svg_icon(svg)
    
    @staticmethod
    def get_folder_icon() -> QIcon:
        """Get folder icon."""
        svg = '''<svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M10,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V8C22,6.89 21.1,6 20,6H12L10,4Z"/>
        </svg>'''
        return Icons.create_svg_icon(svg)
    
    @staticmethod
    def get_play_icon() -> QIcon:
        """Get play icon."""
        svg = '''<svg viewBox="0 0 24 24" fill="#00B894">
            <path d="M8,5.14V19.14L19,12.14L8,5.14Z"/>
        </svg>'''
        return Icons.create_svg_icon(svg)
    
    @staticmethod
    def get_stop_icon() -> QIcon:
        """Get stop icon."""
        svg = '''<svg viewBox="0 0 24 24" fill="#FDCB6E">
            <path d="M18,18H6V6H18V18Z"/>
        </svg>'''
        return Icons.create_svg_icon(svg)
    
    @staticmethod
    def get_clear_icon() -> QIcon:
        """Get clear/delete icon."""
        svg = '''<svg viewBox="0 0 24 24" fill="#FF6B6B">
            <path d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"/>
        </svg>'''
        return Icons.create_svg_icon(svg)
    
    @staticmethod
    def get_benchmark_icon() -> QIcon:
        """Get benchmark icon."""
        svg = '''<svg viewBox="0 0 24 24" fill="#6C5CE7">
            <path d="M22,21H2V3H4V19H6V10H10V19H12V6H16V19H18V14H22V21Z"/>
        </svg>'''
        return Icons.create_svg_icon(svg)
    
    @staticmethod
    def get_check_icon(color: str = "#00B894") -> QIcon:
        """Get check/success icon."""
        svg = f'''<svg viewBox="0 0 24 24" fill="{color}">
            <path d="M9,20.42L2.79,14.21L5.62,11.38L9,14.77L18.88,4.88L21.71,7.71L9,20.42Z"/>
        </svg>'''
        return Icons.create_svg_icon(svg)
    
    @staticmethod
    def get_error_icon() -> QIcon:
        """Get error icon."""
        svg = '''<svg viewBox="0 0 24 24" fill="#FF6B6B">
            <path d="M12,2C17.53,2 22,6.47 22,12C22,17.53 17.53,22 12,22C6.47,22 2,17.53 2,12C2,6.47 6.47,2 12,2M15.59,7L12,10.59L8.41,7L7,8.41L10.59,12L7,15.59L8.41,17L12,13.41L15.59,17L17,15.59L13.41,12L17,8.41L15.59,7Z"/>
        </svg>'''
        return Icons.create_svg_icon(svg)
    
    @staticmethod
    def get_processing_icon() -> QIcon:
        """Get processing/gear icon."""
        svg = '''<svg viewBox="0 0 24 24" fill="#3498DB">
            <path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z"/>
        </svg>'''
        return Icons.create_svg_icon(svg)