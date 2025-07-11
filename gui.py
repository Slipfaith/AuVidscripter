class MainWindow(QMainWindow):
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_area.setStyleSheet(f"""
                QLabel#dropArea {{
                    border: 2px dashed {Theme.DROP_ZONE_HOVER};
                    background-color: {Theme.DROP_ZONE_BG_HOVER};
                    color: {Theme.DROP_ZONE_HOVER};
                }}
            """)
            
    def dragLeaveEvent(self, event):
        self.drop_area.setStyleSheet("")
        
    def dropEvent(self, event: QDropEvent):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        valid_extensions = [
            ".mp3", ".mp4", ".wav", ".m4a", ".flac", ".aac",
            ".ogg", ".opus", ".avi", ".mov", ".mkv"
        ]
        
        added_count = 0
        for path in paths:
            if os.path.isfile(path):
                if self.add_file_to_queue(path, valid_extensions):
                    added_count += 1
            elif os.path.isdir(path):
                self.log_text.append(f"📂 Сканирование: {os.path.basename(path)}")
                added_count += self.scan_directory_for_files(path, valid_extensions)
                
        if added_count > 0:
            self.start_button.setEnabled(True)
            
        self.update_file_counter()
        self.drop_area.setStyleSheet("")

    # --- File Management ---
    def add_file_to_queue(self, file_path, valid_extensions):
        """Add file to processing queue."""
        file_ext = Path(file_path).suffix.lower()
        if file_ext in valid_extensions:
            if file_path not in self.file_queue:
                if not os.path.exists(file_path):
                    self.log_text.append(f"❓ Файл не найден: {os.path.basename(file_path)}")
                    return False
                    
                self.file_queue.append(file_path)
                item = FileListItem(file_path)
                self.file_list.addItem(item)
                self.log_text.append(f"✅ Добавлен: {os.path.basename(file_path)}")
                return True
        else:
            self.log_text.append(f"❌ Неподдерживаемый формат: {os.path.basename(file_path)}")
        return False

    def scan_directory_for_files(self, directory, valid_extensions):
        """Scan directory for valid files."""
        found_files = 0
        skipped_files = 0
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = Path(file_path).suffix.lower()
                if file_ext in valid_extensions:
                    if file_path not in self.file_queue:
                        if os.path.exists(file_path):
                            self.file_queue.append(file_path)
                            item = FileListItem(file_path)
                            self.file_list.addItem(item)
                            found_files += 1
                        else:
                            skipped_files += 1
                            
        if found_files > 0:
            self.log_text.append(f"✅ Найдено {found_files} файлов")
        if skipped_files > 0:
            self.log_text.append(f"⚠️ Пропущено {skipped_files} файлов")
            
        return found_files
        
    def clear_file_list(self):
        """Clear file queue."""
        self.file_queue.clear()
        self.file_list.clear()
        self.processed_files.clear()
        self.update_file_counter()
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.overall_progress_bar.setValue(0)
        self.status_label.setText("")
        self.performance_label.hide()
        self.log_text.clear()
        self.log_text.append("✅ Очередь очищена")
        
    def count_errors(self):
        """Count files with error status."""
        return sum(
            1 for i in range(self.file_list.count())
            if self.file_list.item(i).status == "error"
        )
        
    def update_file_counter(self):
        """Update file counter display."""
        total = len(self.file_queue)
        processed = len(self.processed_files)
        errors = self.count_errors()
        self.file_counter_label.setText(
            f"Файлов: {total} | Обработано: {processed} | Ошибок: {errors}"
        )
        
    def show_benchmark_dialog(self):
        """Show benchmark dialog."""
        dialog = BenchmarkDialog(self)
        dialog.exec()

    # --- Processing ---
    def start_processing(self):
        """Start processing files."""
        if not self.file_queue:
            return
            
        self.setAcceptDrops(False)
        self.setEnabled_controls(False)
        self.stop_button.setEnabled(True)
        self.elapsed_timer.start()
        
        # Show taskbar progress
        if hasattr(self, 'taskbar_progress'):
            self.taskbar_progress.setVisible(True)
            self.taskbar_progress.setValue(0)
        
        # Start processing thread
        self.transcription_thread = TranscriptionThread(
            self.file_queue.copy(),
            self.model_combo.currentText(),
            "txt" if self.format_combo.currentText() == "TXT" else "srt",
            backend=self.engine_combo.currentText(),
        )
        
        # Connect signals
        self.transcription_thread.progress.connect(
            lambda v: self.progress_bar.set_value_animated(v)
        )
        self.transcription_thread.status.connect(self.update_status)
        self.transcription_thread.finished.connect(self.on_file_finished)
        self.transcription_thread.error.connect(self.on_file_error)
        self.transcription_thread.current_file.connect(self.update_current_file)
        self.transcription_thread.overall_progress.connect(self.update_overall_progress)
        self.transcription_thread.benchmark_result.connect(self.on_benchmark_result)
        self.transcription_thread.file_not_found.connect(self.on_file_not_found)
        
        self.transcription_thread.start()
        
    def stop_processing(self):
        """Stop processing."""
        if self.transcription_thread and self.transcription_thread.isRunning():
            self.transcription_thread.stop()
            self.log_text.append("⏹️ Остановка...")
            self.status_label.setText("Остановка обработки...")
            
    def cleanup_processing(self):
        """Clean up after processing."""
        if self.transcription_thread:
            self.transcription_thread.wait(5000)
            if self.transcription_thread.isRunning():
                logger.warning("Thread did not finish in time")
            self.transcription_thread = None
        self.reset_ui_state()
        
    def setEnabled_controls(self, enabled):
        """Enable/disable controls."""
        self.model_combo.setEnabled(enabled)
        self.engine_combo.setEnabled(enabled)
        self.format_combo.setEnabled(enabled)
        self.start_button.setEnabled(enabled and bool(self.file_queue))
        self.clear_button.setEnabled(enabled)
        self.benchmark_button.setEnabled(enabled)

    # --- Signal handlers ---
    def update_status(self, status):
        """Update status label."""
        self.status_label.setText(status)
        
    def update_current_file(self, filename):
        """Update current file being processed."""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if os.path.basename(item.file_path) == filename:
                item.status = "processing"
                item.update_appearance()
                self.file_list.scrollToItem(item)
                break
                
    def update_overall_progress(self, current, total):
        """Update overall progress."""
        self.overall_progress_label.setText(f"Общий: {current}/{total}")
        if total > 0:
            progress = int((current / total) * 100)
            self.overall_progress_bar.set_value_animated(progress, 500)
            
            # Update taskbar progress on Windows
            if hasattr(self, 'taskbar_progress'):
                self.taskbar_progress.setValue(progress)
                
    def on_benchmark_result(self, engine_name, time_per_minute):
        """Handle benchmark results."""
        self.benchmark_results[engine_name] = time_per_minute
        self.performance_label.setText(
            f"⚡ {engine_name}: {time_per_minute:.1f}с/мин"
        )
        self.performance_label.show()
        
    def on_file_not_found(self, file_path):
        """Handle missing files."""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.file_path == file_path:
                item.status = "not_found"
                item.update_appearance()
                break
                
    def on_file_finished(self, file_path, output_path):
        """Handle file completion."""
        self.processed_files.append(output_path)
        self.log_text.append(f"✅ Готово: {os.path.basename(output_path)}")
        
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.file_path == file_path:
                item.status = "completed"
                item.update_appearance()
                break
                
        self.update_file_counter()
        self.check_if_all_processed()
        
    def on_file_error(self, file_path, error):
        """Handle file errors."""
        if file_path:
            self.log_text.append(f"❌ Ошибка {os.path.basename(file_path)}: {error}")
            for i in range(self.file_list.count()):
                item = self.file_list.item(i)
                if item.file_path == file_path:
                    item.status = "error"
                    item.update_appearance()
                    break
        else:
            self.log_text.append(f"❌ {error}")
            
        self.update_file_counter()
        self.check_if_all_processed()
        
    def check_if_all_processed(self):
        """Check if all files are processed."""
        total_processed = len(self.processed_files) + self.count_errors()
        if total_processed == len(self.file_queue) and self.transcription_thread:
            QTimer.singleShot(100, self.on_all_processing_complete)
            
    def on_all_processing_complete(self):
        """Handle completion of all processing."""
        elapsed_ms = self.elapsed_timer.elapsed()
        time_str = self.format_time(elapsed_ms)
        
        self.status_label.setText("✅ Обработка завершена!")
        self.log_text.append(f"✨ Завершено! Обработано {len(self.processed_files)} файлов")
        self.log_text.append(f"⏱️ Время: {time_str}")
        
        # Show performance if available
        if self.transcription_thread and self.transcription_thread.backend in self.benchmark_results:
            speed = self.benchmark_results[self.transcription_thread.backend]
            self.log_text.append(f"⚡ Средняя скорость: {speed:.1f}с/мин")
            
        # Show notification
        self.notification_manager.show_notification(
            "Транскрибация завершена",
            f"Обработано {len(self.processed_files)} файлов за {time_str}"
        )
        
        # Update taskbar
        if hasattr(self, 'taskbar_progress'):
            self.taskbar_progress.setValue(100)
            QTimer.singleShot(3000, lambda: self.taskbar_progress.setVisible(False))
            
        self.cleanup_processing()
        
    def format_time(self, ms):
        """Format milliseconds to readable time."""
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        
        if hours > 0:
            return f"{hours}ч {minutes}м {seconds}с"
        elif minutes > 0:
            return f"{minutes}м {seconds}с"
        else:
            return f"{seconds}с"
            
    def reset_ui_state(self):
        """Reset UI to initial state."""
        self.setAcceptDrops(True)
        self.setEnabled_controls(True)
        self.stop_button.setEnabled(False)
        
    def closeEvent(self, event):
        """Handle widget close event."""
        if self.transcription_thread and self.transcription_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                "Идет обработка файлов. Вы действительно хотите выйти?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self._is_closing = True
                if self.transcription_thread:
                    self.transcription_thread.stop()
                    self.transcription_thread.wait(3000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


class MainWindow(QMainWindow):
    """Main application window with horizontal layout."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio/Video Transcriber")
        
        # Set window size - more horizontal
        self.resize(1000, 600)
        self.setMinimumSize(800, 500)
        
        # Apply theme
        self.setStyleSheet(Theme.get_stylesheet())
        
        # Create central widget
        self.central_widget = HorizontalTranscriberWidget()
        self.setCentralWidget(self.central_widget)
        
        # Setup taskbar progress (Windows)
        self.setup_taskbar_progress()
        
        # Center window on screen
        self.center_on_screen()
        
    def setup_taskbar_progress(self):
        """Setup Windows taskbar progress indicator."""
        if TASKBAR_AVAILABLE and platform.system() == 'Windows':
            self.taskbar_button = QWinTaskbarButton(self)
            self.taskbar_button.setWindow(self.windowHandle())
            
            self.taskbar_progress = self.taskbar_button.progress()
            self.taskbar_progress.setVisible(False)
            
            # Pass to central widget
            self.central_widget.taskbar_progress = self.taskbar_progress
            
    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)
        if hasattr(self, 'taskbar_button'):
            self.taskbar_button.setWindow(self.windowHandle())
            
    def center_on_screen(self):
        """Center window on screen."""
        screen = QApplication.primaryScreen()
        if screen:
            center = screen.geometry().center()
            geo = self.frameGeometry()
            geo.moveCenter(center)
            self.move(geo.topLeft())
            
    def closeEvent(self, event: QCloseEvent):
        """Handle application close."""
        # Pass to central widget first
        self.central_widget.closeEvent(event)
        
        if event.isAccepted():
            # Clear model cache
            ModelManager.clear_cache()
            logger.info("Application closed")


def main():
    """Main entry point."""
    # Setup logging
    setup_logging()
    
    # Enable high DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    
    # Enable high DPI scaling
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Set dark palette for window decorations
    dark_palette = app.palette()
    dark_palette.setColor(dark_palette.Window, QColor(Theme.BACKGROUND))
    dark_palette.setColor(dark_palette.WindowText, QColor(Theme.TEXT_PRIMARY))
    dark_palette.setColor(dark_palette.Base, QColor(Theme.SURFACE))
    dark_palette.setColor(dark_palette.AlternateBase, QColor(Theme.SURFACE_HOVER))
    dark_palette.setColor(dark_palette.Text, QColor(Theme.TEXT_PRIMARY))
    dark_palette.setColor(dark_palette.Button, QColor(Theme.SURFACE))
    dark_palette.setColor(dark_palette.ButtonText, QColor(Theme.TEXT_PRIMARY))
    app.setPalette(dark_palette)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Setup taskbar progress after window is shown
    if hasattr(window, 'taskbar_button'):
        window.taskbar_button.setWindow(window.windowHandle())
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()"""GUI components with horizontal layout design."""

import os
import sys
import logging
from pathlib import Path
import platform

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QComboBox,
    QListWidget,
    QGroupBox,
    QListWidgetItem,
    QDialog,
    QFileDialog,
    QMessageBox,
    QGraphicsOpacityEffect,
    QSystemTrayIcon,
    QSplitter,
    QSizePolicy,
)
from PySide6.QtCore import (
    Qt, QTimer, QElapsedTimer, QPropertyAnimation, 
    QEasingCurve, Signal
)
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QCloseEvent,
    QColor
)

# Platform-specific imports for taskbar progress
if platform.system() == 'Windows':
    try:
        from PySide6.QtWinExtras import QWinTaskbarButton, QWinTaskbarProgress
        TASKBAR_AVAILABLE = True
    except ImportError:
        TASKBAR_AVAILABLE = False
else:
    TASKBAR_AVAILABLE = False

from business import TranscriptionThread, BenchmarkThread, ModelManager
from logger_setup import setup_logging
from theme import Theme

logger = logging.getLogger(__name__)


class FileListItem(QListWidgetItem):
    """Custom list item showing file status."""

    SYMBOLS = {
        "pending": "⏳",
        "processing": "⚙️",
        "completed": "✅",
        "error": "❌",
        "not_found": "❓"
    }

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.status = "pending"
        self.update_appearance()

    def update_appearance(self):
        """Update item appearance based on status."""
        filename = os.path.basename(self.file_path)
        symbol = self.SYMBOLS.get(self.status, "")
        
        color_map = {
            "pending": Theme.TEXT_PRIMARY,
            "processing": Theme.INFO,
            "completed": Theme.SUCCESS,
            "error": Theme.ERROR,
            "not_found": Theme.TEXT_DISABLED
        }
        
        self.setText(f"{symbol} {filename}")
        if self.status == "not_found":
            self.setText(f"{symbol} {filename} (не найден)")
        
        self.setForeground(QColor(color_map.get(self.status, Theme.TEXT_PRIMARY)))


class ModernProgressBar(QProgressBar):
    """Custom progress bar with smooth animations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
    def set_value_animated(self, value, duration=300):
        """Set value with animation."""
        self.animation.setDuration(duration)
        self.animation.setStartValue(self.value())
        self.animation.setEndValue(value)
        self.animation.start()


class NotificationManager:
    """Manages system notifications."""
    
    def __init__(self, parent):
        self.parent = parent
        self.tray_icon = None
        
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(parent)
            app = QApplication.instance()
            if app and app.windowIcon():
                self.tray_icon.setIcon(app.windowIcon())
            
    def show_notification(self, title, message, icon=QSystemTrayIcon.Information):
        """Show system notification."""
        if self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()
            self.tray_icon.showMessage(title, message, icon, 5000)
            QTimer.singleShot(5000, self.tray_icon.hide)


class BenchmarkDialog(QDialog):
    """Benchmark dialog with theme support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Бенчмарк производительности")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.init_ui()
        self.test_file = None
        self.benchmark_thread = None

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_label = QLabel("Размер модели:")
        model_layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small"])
        self.model_combo.setCurrentText("tiny")
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        layout.addLayout(model_layout)
        
        # File selection
        self.file_button = QPushButton("📁 Выбрать тестовый файл")
        self.file_button.clicked.connect(self.select_file)
        layout.addWidget(self.file_button)
        
        self.file_label = QLabel("Файл не выбран")
        self.file_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.file_label)
        
        # Progress and status
        self.progress_bar = ModernProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Results
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("Результаты бенчмарка...")
        layout.addWidget(self.results_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("▶ Запустить")
        self.run_button.clicked.connect(self.run_benchmark)
        self.run_button.setEnabled(False)
        self.run_button.setObjectName("startButton")
        button_layout.addWidget(self.run_button)
        
        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите аудио файл",
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.flac);;Video Files (*.mp4 *.avi *.mov)"
        )
        if file_path:
            self.test_file = file_path
            self.file_label.setText(f"✅ {os.path.basename(file_path)}")
            self.file_label.setStyleSheet(f"color: {Theme.SUCCESS};")
            self.run_button.setEnabled(True)

    def run_benchmark(self):
        if not self.test_file or not os.path.exists(self.test_file):
            QMessageBox.warning(self, "Ошибка", "Файл не найден")
            return
            
        self.run_button.setEnabled(False)
        self.model_combo.setEnabled(False)
        self.file_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.results_text.clear()
        
        self.benchmark_thread = BenchmarkThread(
            self.test_file,
            self.model_combo.currentText()
        )
        self.benchmark_thread.status.connect(self.status_label.setText)
        self.benchmark_thread.progress.connect(
            lambda v: self.progress_bar.set_value_animated(v)
        )
        self.benchmark_thread.result.connect(self.on_benchmark_complete)
        self.benchmark_thread.error.connect(self.on_benchmark_error)
        self.benchmark_thread.start()

    def on_benchmark_complete(self, result):
        self.results_text.setText(result)
        self.run_button.setEnabled(True)
        self.model_combo.setEnabled(True)
        self.file_button.setEnabled(True)
        self.status_label.setText("✅ Тест завершен!")

    def on_benchmark_error(self, error):
        self.results_text.setText(f"❌ Ошибка: {error}")
        self.run_button.setEnabled(True)
        self.model_combo.setEnabled(True)
        self.file_button.setEnabled(True)
        self.status_label.setText("Ошибка теста")


class HorizontalTranscriberWidget(QWidget):
    """Main widget with horizontal layout."""

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.init_ui()
        
        # State
        self.transcription_thread = None
        self.file_queue = []
        self.processed_files = []
        self.elapsed_timer = QElapsedTimer()
        self.benchmark_results = {}
        self._is_closing = False
        
        # Notification manager
        self.notification_manager = NotificationManager(self)

    def init_ui(self):
        """Initialize UI with horizontal layout."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Top section - controls
        top_section = self.create_top_section()
        main_layout.addWidget(top_section)
        
        # Middle section - main content with splitter
        middle_section = self.create_middle_section()
        main_layout.addWidget(middle_section, 1)
        
        # Bottom section - status
        bottom_section = self.create_bottom_section()
        main_layout.addWidget(bottom_section)
        
        self.setLayout(main_layout)

    def create_top_section(self):
        """Create top section with controls."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Drop area - compact height
        self.drop_area = QLabel("Перетащите файлы или папки сюда")
        self.drop_area.setObjectName("dropArea")
        self.drop_area.setAlignment(Qt.AlignCenter)
        self.drop_area.setFixedHeight(50)
        layout.addWidget(self.drop_area)
        
        # Options in horizontal layout
        options_layout = QHBoxLayout()
        options_layout.setSpacing(20)
        
        # Model selection
        model_group = QHBoxLayout()
        model_group.addWidget(QLabel("Модель:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("base")
        self.model_combo.setToolTip("Размер модели влияет на качество и скорость")
        self.model_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        model_group.addWidget(self.model_combo)
        options_layout.addLayout(model_group)
        
        # Engine selection
        engine_group = QHBoxLayout()
        engine_group.addWidget(QLabel("Движок:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["whisper", "faster-whisper"])
        self.engine_combo.setCurrentText("faster-whisper")
        self.engine_combo.setToolTip("Faster-Whisper быстрее на GPU")
        self.engine_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        engine_group.addWidget(self.engine_combo)
        options_layout.addLayout(engine_group)
        
        # Format selection
        format_group = QHBoxLayout()
        format_group.addWidget(QLabel("Формат:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["SRT", "TXT"])
        self.format_combo.setToolTip("SRT с тайм-кодами или простой текст")
        self.format_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        format_group.addWidget(self.format_combo)
        options_layout.addLayout(format_group)
        
        # Buttons
        self.benchmark_button = QPushButton("📊 Бенчмарк")
        self.benchmark_button.setObjectName("benchmarkButton")
        self.benchmark_button.clicked.connect(self.show_benchmark_dialog)
        options_layout.addWidget(self.benchmark_button)
        
        options_layout.addStretch()
        
        self.start_button = QPushButton("▶ Начать")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.start_processing)
        self.start_button.setEnabled(False)
        options_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏹ Стоп")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.clicked.connect(self.stop_processing)
        self.stop_button.setEnabled(False)
        options_layout.addWidget(self.stop_button)
        
        self.clear_button = QPushButton("🗑️ Очистить")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.clicked.connect(self.clear_file_list)
        options_layout.addWidget(self.clear_button)
        
        layout.addLayout(options_layout)
        
        widget.setLayout(layout)
        return widget

    def create_middle_section(self):
        """Create middle section with file list and logs."""
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - file queue
        files_widget = QWidget()
        files_layout = QVBoxLayout()
        files_layout.setContentsMargins(0, 0, 0, 0)
        
        files_group = QGroupBox("Очередь файлов")
        files_group_layout = QVBoxLayout()
        
        self.file_list = QListWidget()
        files_group_layout.addWidget(self.file_list)
        
        # File counter
        self.file_counter_label = QLabel("Файлов: 0 | Обработано: 0 | Ошибок: 0")
        self.file_counter_label.setObjectName("fileCounterLabel")
        self.file_counter_label.setAlignment(Qt.AlignCenter)
        files_group_layout.addWidget(self.file_counter_label)
        
        files_group.setLayout(files_group_layout)
        files_layout.addWidget(files_group)
        files_widget.setLayout(files_layout)
        
        # Right side - logs
        logs_widget = QWidget()
        logs_layout = QVBoxLayout()
        logs_layout.setContentsMargins(0, 0, 0, 0)
        
        logs_group = QGroupBox("Логи")
        logs_group_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Логи появятся здесь...")
        logs_group_layout.addWidget(self.log_text)
        
        logs_group.setLayout(logs_group_layout)
        logs_layout.addWidget(logs_group)
        logs_widget.setLayout(logs_layout)
        
        # Add to splitter
        splitter.addWidget(files_widget)
        splitter.addWidget(logs_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        return splitter

    def create_bottom_section(self):
        """Create bottom section with status and progress."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Status
        status_layout = QHBoxLayout()
        self.status_label = QLabel("")
        status_layout.addWidget(self.status_label)
        
        self.performance_label = QLabel("")
        self.performance_label.setObjectName("performanceLabel")
        self.performance_label.hide()
        status_layout.addWidget(self.performance_label)
        
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Progress bars
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(5)
        
        # Current file progress
        file_progress_layout = QHBoxLayout()
        file_progress_layout.addWidget(QLabel("Файл:"))
        self.progress_bar = ModernProgressBar()
        self.progress_bar.setFixedHeight(16)
        file_progress_layout.addWidget(self.progress_bar)
        progress_layout.addLayout(file_progress_layout)
        
        # Overall progress
        overall_progress_layout = QHBoxLayout()
        self.overall_progress_label = QLabel("Общий: 0/0")
        self.overall_progress_label.setFixedWidth(80)
        overall_progress_layout.addWidget(self.overall_progress_label)
        self.overall_progress_bar = ModernProgressBar()
        self.overall_progress_bar.setObjectName("overallProgress")
        self.overall_progress_bar.setFixedHeight(16)
        overall_progress_layout.addWidget(self.overall_progress_bar)
        progress_layout.addLayout(overall_progress_layout)
        
        layout.addLayout(progress_layout)
        
        widget.setLayout(layout)
        return widget