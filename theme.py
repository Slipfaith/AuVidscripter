"""Theme configuration for the application."""


class Theme:
    """Color theme configuration."""

    # Main colors
    BACKGROUND = "#2D3436"
    SURFACE = "#34495E"
    SURFACE_HOVER = "#3D4F60"

    # Text colors
    TEXT_PRIMARY = "#DFE6E9"
    TEXT_SECONDARY = "#B2BEC3"
    TEXT_DISABLED = "#7F8C8D"

    # Brand colors
    PRIMARY = "#6C5CE7"
    PRIMARY_HOVER = "#5C4CD7"
    SECONDARY = "#A29BFE"

    # Status colors
    SUCCESS = "#00B894"
    SUCCESS_HOVER = "#00A884"
    WARNING = "#FDCB6E"
    WARNING_HOVER = "#FCBB5E"
    ERROR = "#FF6B6B"
    ERROR_HOVER = "#FF5B5B"
    INFO = "#3498DB"

    # Border colors
    BORDER = "#495A6B"
    BORDER_HOVER = "#6C5CE7"

    # Special effects
    DROP_ZONE_BORDER = "#6C5CE7"
    DROP_ZONE_HOVER = "#A29BFE"
    DROP_ZONE_BG = "rgba(108, 92, 231, 0.1)"
    DROP_ZONE_BG_HOVER = "rgba(162, 155, 254, 0.2)"

    # Font settings
    FONT_FAMILY = "'Segoe UI', Arial, sans-serif"
    FONT_FAMILY_MONO = "'Consolas', 'Monaco', monospace"
    FONT_SIZE_BASE = "14px"
    FONT_SIZE_SMALL = "12px"
    FONT_SIZE_LARGE = "16px"
    FONT_SIZE_TITLE = "20px"

    # Spacing
    PADDING_SMALL = "6px"
    PADDING_MEDIUM = "10px"
    PADDING_LARGE = "16px"

    # Border radius
    RADIUS_SMALL = "4px"
    RADIUS_MEDIUM = "6px"
    RADIUS_LARGE = "8px"
    RADIUS_XLARGE = "12px"

    @classmethod
    def get_stylesheet(cls):
        """Get complete stylesheet for the application."""
        return f"""
            /* Global styles */
            QWidget {{
                background-color: {cls.BACKGROUND};
                color: {cls.TEXT_PRIMARY};
                font-family: {cls.FONT_FAMILY};
                font-size: {cls.FONT_SIZE_BASE};
            }}
            
            /* Main Window */
            QMainWindow {{
                background-color: {cls.BACKGROUND};
            }}
            
            /* Labels */
            QLabel {{
                color: {cls.TEXT_PRIMARY};
                padding: 2px;
            }}
            
            QLabel#dropArea {{
                border: 2px dashed {cls.DROP_ZONE_BORDER};
                border-radius: {cls.RADIUS_LARGE};
                background-color: {cls.DROP_ZONE_BG};
                font-size: {cls.FONT_SIZE_BASE};
                color: {cls.SECONDARY};
                padding: {cls.PADDING_LARGE};
                min-height: 40px;
                max-height: 60px;
            }}
            
            QLabel#fileCounterLabel {{
                font-size: {cls.FONT_SIZE_BASE};
                font-weight: 500;
                color: {cls.TEXT_PRIMARY};
                padding: {cls.PADDING_MEDIUM};
                background-color: {cls.SURFACE};
                border-radius: {cls.RADIUS_MEDIUM};
            }}
            
            QLabel#performanceLabel {{
                font-size: {cls.FONT_SIZE_SMALL};
                color: {cls.SECONDARY};
                font-weight: 500;
            }}
            
            /* ComboBoxes */
            QComboBox {{
                background-color: {cls.SURFACE};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS_MEDIUM};
                padding: {cls.PADDING_SMALL} {cls.PADDING_MEDIUM};
                color: {cls.TEXT_PRIMARY};
                min-width: 120px;
                min-height: 28px;
            }}
            
            QComboBox:hover {{
                border-color: {cls.BORDER_HOVER};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {cls.SURFACE};
                border: 1px solid {cls.BORDER};
                selection-background-color: {cls.PRIMARY};
                selection-color: white;
                padding: 4px;
            }}
            
            /* Buttons */
            QPushButton {{
                border: none;
                border-radius: {cls.RADIUS_MEDIUM};
                padding: {cls.PADDING_SMALL} {cls.PADDING_LARGE};
                font-weight: 500;
                font-size: {cls.FONT_SIZE_BASE};
                min-height: 32px;
            }}
            
            /* Icon-only buttons */
            QPushButton[text="📊"], 
            QPushButton[text="▶"], 
            QPushButton[text="⏹"], 
            QPushButton[text="🗑️"] {{
                font-size: 16px;
                padding: {cls.PADDING_SMALL};
            }}
            
            QPushButton#startButton {{
                background-color: {cls.SUCCESS};
                color: white;
            }}
            
            QPushButton#startButton:hover {{
                background-color: {cls.SUCCESS_HOVER};
            }}
            
            QPushButton#startButton:disabled {{
                background-color: {cls.SURFACE};
                color: {cls.TEXT_DISABLED};
            }}
            
            QPushButton#stopButton {{
                background-color: {cls.WARNING};
                color: {cls.BACKGROUND};
            }}
            
            QPushButton#stopButton:hover {{
                background-color: {cls.WARNING_HOVER};
            }}
            
            QPushButton#stopButton:disabled {{
                background-color: {cls.SURFACE};
                color: {cls.TEXT_DISABLED};
            }}
            
            QPushButton#clearButton {{
                background-color: {cls.ERROR};
                color: white;
            }}
            
            QPushButton#clearButton:hover {{
                background-color: {cls.ERROR_HOVER};
            }}
            
            QPushButton#benchmarkButton {{
                background-color: {cls.PRIMARY};
                color: white;
            }}
            
            QPushButton#benchmarkButton:hover {{
                background-color: {cls.PRIMARY_HOVER};
            }}
            
            /* Progress bars */
            QProgressBar {{
                border: none;
                border-radius: 8px;
                background-color: {cls.SURFACE};
                height: 16px;
                text-align: center;
                color: white;
                font-weight: 500;
                font-size: {cls.FONT_SIZE_SMALL};
            }}
            
            QProgressBar::chunk {{
                border-radius: 8px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 {cls.PRIMARY}, stop:1 {cls.SECONDARY});
            }}
            
            QProgressBar#overallProgress::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 {cls.SUCCESS}, stop:1 #00D4A4);
            }}
            
            /* List widget */
            QListWidget {{
                background-color: {cls.SURFACE};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS_LARGE};
                padding: {cls.PADDING_SMALL};
                outline: none;
            }}
            
            QListWidget::item {{
                padding: {cls.PADDING_SMALL};
                border-radius: {cls.RADIUS_SMALL};
                margin: 2px 0;
            }}
            
            QListWidget::item:hover {{
                background-color: {cls.SURFACE_HOVER};
            }}
            
            QListWidget::item:selected {{
                background-color: rgba(108, 92, 231, 0.3);
                border: 1px solid {cls.PRIMARY};
            }}
            
            /* Text edit */
            QTextEdit {{
                background-color: {cls.SURFACE};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS_LARGE};
                padding: {cls.PADDING_MEDIUM};
                color: {cls.TEXT_PRIMARY};
                font-family: {cls.FONT_FAMILY_MONO};
                font-size: {cls.FONT_SIZE_SMALL};
            }}
            
            /* Group box */
            QGroupBox {{
                font-weight: 600;
                font-size: {cls.FONT_SIZE_BASE};
                color: {cls.SECONDARY};
                border: 2px solid {cls.BORDER};
                border-radius: {cls.RADIUS_LARGE};
                margin-top: 10px;
                padding-top: 10px;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 10px 0 10px;
                background-color: {cls.BACKGROUND};
            }}
            
            /* Scroll bars */
            QScrollBar:vertical {{
                background-color: {cls.SURFACE};
                width: 10px;
                border-radius: 5px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {cls.PRIMARY};
                border-radius: 5px;
                min-height: 20px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {cls.SECONDARY};
            }}
            
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            
            QScrollBar:horizontal {{
                background-color: {cls.SURFACE};
                height: 10px;
                border-radius: 5px;
            }}
            
            QScrollBar::handle:horizontal {{
                background-color: {cls.PRIMARY};
                border-radius: 5px;
                min-width: 20px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background-color: {cls.SECONDARY};
            }}
            
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
            
            /* Splitter */
            QSplitter::handle {{
                background-color: {cls.BORDER};
                width: 2px;
            }}
            
            QSplitter::handle:hover {{
                background-color: {cls.PRIMARY};
            }}
            
            /* Dialog */
            QDialog {{
                background-color: {cls.BACKGROUND};
            }}
            
            /* Message Box */
            QMessageBox {{
                background-color: {cls.BACKGROUND};
            }}
            
            QMessageBox QLabel {{
                color: {cls.TEXT_PRIMARY};
            }}
            
            /* Tool tips */
            QToolTip {{
                background-color: {cls.SURFACE};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.PRIMARY};
                border-radius: {cls.RADIUS_SMALL};
                padding: {cls.PADDING_SMALL};
            }}
        """