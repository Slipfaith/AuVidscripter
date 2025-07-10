"""GUI components of the application."""

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QComboBox,
    QListWidget,
    QHBoxLayout,
    QGroupBox,
    QListWidgetItem,
)
from PySide6.QtCore import Qt, QTimer, QElapsedTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from business import TranscriptionThread
from logger_setup import setup_logging


class FileListItem(QListWidgetItem):
    """Custom list item showing file status."""

    def __init__(self, file_path):
        super().__init__(os.path.basename(file_path))
        self.file_path = file_path
        self.status = "pending"  # pending, processing, completed, error
        self.update_appearance()

    def update_appearance(self):
        if self.status == "pending":
            self.setForeground(Qt.black)
            self.setText(f"⏳ {os.path.basename(self.file_path)}")
        elif self.status == "processing":
            self.setForeground(Qt.blue)
            self.setText(f"⚙️ {os.path.basename(self.file_path)}")
        elif self.status == "completed":
            self.setForeground(Qt.darkGreen)
            self.setText(f"✅ {os.path.basename(self.file_path)}")
        elif self.status == "error":
            self.setForeground(Qt.red)
            self.setText(f"❌ {os.path.basename(self.file_path)}")


class DragDropWidget(QWidget):
    """Widget that manages file dropping and processing."""

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.init_ui()
        self.transcription_thread = None
        self.file_queue = []
        self.processed_files = []
        self.elapsed_timer = QElapsedTimer()
        self.total_elapsed_ms = 0

    # --- UI setup -----------------------------------------------------
    def init_ui(self):
        layout = QVBoxLayout()

        self.title_label = QLabel("Audio/Video to SRT Transcriber")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(
            """
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                margin: 20px;
            }
            """
        )
        layout.addWidget(self.title_label)

        options_layout = QHBoxLayout()

        model_group = QVBoxLayout()
        model_label = QLabel("Выберите размер модели:")
        model_group.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("base")
        self.model_combo.setToolTip(
            "tiny: самая быстрая, низкая точность\n"
            "base: баланс скорости и точности\n"
            "small: хорошая точность\n"
            "medium: высокая точность\n"
            "large: максимальная точность, медленная"
        )
        model_group.addWidget(self.model_combo)
        options_layout.addLayout(model_group)

        engine_group = QVBoxLayout()
        engine_label = QLabel("Движок распознавания:")
        engine_group.addWidget(engine_label)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["whisper", "faster-whisper"])
        self.engine_combo.setCurrentText("whisper")
        engine_group.addWidget(self.engine_combo)
        options_layout.addLayout(engine_group)

        format_group = QVBoxLayout()
        format_label = QLabel("Формат результата:")
        format_group.addWidget(format_label)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["SRT", "TXT (без тайм-кодов)"])
        format_group.addWidget(self.format_combo)
        options_layout.addLayout(format_group)

        layout.addLayout(options_layout)

        self.drop_area = QLabel("Перетащите сюда аудио/видео файлы или папки")
        self.drop_area.setAlignment(Qt.AlignCenter)
        self.drop_area.setMinimumHeight(60)
        self.drop_area.setStyleSheet(
            """
            QLabel {
                border: 3px dashed #3498db;
                border-radius: 10px;
                background-color: #ecf0f1;
                font-size: 16px;
                color: #7f8c8d;
                padding: 20px;
            }
            """
        )
        layout.addWidget(self.drop_area)

        self.file_counter_label = QLabel(
            "Файлов в очереди: 0 | Обработано: 0 | Ошибок: 0"
        )
        self.file_counter_label.setAlignment(Qt.AlignCenter)
        self.file_counter_label.setStyleSheet(
            """
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #34495e;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 5px;
                margin: 5px 0;
            }
            """
        )
        layout.addWidget(self.file_counter_label)

        files_group = QGroupBox("Очередь файлов")
        files_layout = QVBoxLayout()

        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(200)
        files_layout.addWidget(self.file_list)

        list_buttons_layout = QHBoxLayout()

        self.clear_list_button = QPushButton("Очистить список")
        self.clear_list_button.clicked.connect(self.clear_file_list)
        self.clear_list_button.setStyleSheet(
            """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            """
        )

        self.start_button = QPushButton("Начать обработку")
        self.start_button.clicked.connect(self.start_processing)
        self.start_button.setEnabled(False)
        self.start_button.setStyleSheet(
            """
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
            """
        )

        self.stop_button = QPushButton("Остановить")
        self.stop_button.clicked.connect(self.stop_processing)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet(
            """
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
            """
        )

        list_buttons_layout.addWidget(self.clear_list_button)
        list_buttons_layout.addWidget(self.start_button)
        list_buttons_layout.addWidget(self.stop_button)
        files_layout.addLayout(list_buttons_layout)

        files_group.setLayout(files_layout)
        layout.addWidget(files_group)

        status_group = QGroupBox("Статус обработки")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            """
            QLabel {
                font-size: 14px;
                color: #2c3e50;
                margin: 5px;
            }
            """
        )
        status_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #3498db;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
            """
        )
        status_layout.addWidget(self.progress_bar)

        self.overall_progress_label = QLabel("Общий прогресс: 0/0")
        self.overall_progress_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.overall_progress_label)

        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid #27ae60;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                border-radius: 3px;
            }
            """
        )
        status_layout.addWidget(self.overall_progress_bar)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setPlaceholderText("Здесь будут отображаться логи...")
        layout.addWidget(self.log_text)

        self.setLayout(layout)

    # --- drag and drop events ---------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_area.setStyleSheet(
                """
                QLabel {
                    border: 3px dashed #2ecc71;
                    border-radius: 10px;
                    background-color: #d5f4e6;
                    font-size: 16px;
                    color: #27ae60;
                    padding: 20px;
                }
                """
            )

    def dragLeaveEvent(self, event):  # noqa: D401
        self.drop_area.setStyleSheet(
            """
            QLabel {
                border: 3px dashed #3498db;
                border-radius: 10px;
                background-color: #ecf0f1;
                font-size: 16px;
                color: #7f8c8d;
                padding: 20px;
            }
            """
        )

    def dropEvent(self, event: QDropEvent):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        valid_extensions = [
            ".mp3",
            ".mp4",
            ".wav",
            ".m4a",
            ".flac",
            ".aac",
            ".ogg",
            ".opus",
            ".avi",
            ".mov",
            ".mkv",
        ]

        for path in paths:
            if os.path.isfile(path):
                self.add_file_to_queue(path, valid_extensions)
            elif os.path.isdir(path):
                self.log_text.append(f"📂 Сканирование папки: {os.path.basename(path)}")
                self.scan_directory_for_files(path, valid_extensions)

        if self.file_queue:
            self.start_button.setEnabled(True)

        self.update_file_counter()

        self.drop_area.setStyleSheet(
            """
            QLabel {
                border: 3px dashed #3498db;
                border-radius: 10px;
                background-color: #ecf0f1;
                font-size: 16px;
                color: #7f8c8d;
                padding: 20px;
            }
            """
        )

    # --- queue management -------------------------------------------
    def add_file_to_queue(self, file_path, valid_extensions):
        file_ext = Path(file_path).suffix.lower()
        if file_ext in valid_extensions:
            if file_path not in self.file_queue:
                self.file_queue.append(file_path)
                item = FileListItem(file_path)
                self.file_list.addItem(item)
                self.log_text.append(
                    f"📁 Добавлен в очередь: {os.path.basename(file_path)}"
                )
        else:
            self.log_text.append(
                f"❌ Неподдерживаемый формат: {os.path.basename(file_path)}"
            )

    def scan_directory_for_files(self, directory, valid_extensions):
        found_files = 0
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = Path(file_path).suffix.lower()
                if file_ext in valid_extensions:
                    if file_path not in self.file_queue:
                        self.file_queue.append(file_path)
                        item = FileListItem(file_path)
                        self.file_list.addItem(item)
                        found_files += 1
        if found_files > 0:
            self.log_text.append(
                f"✅ Найдено {found_files} файлов в папке {os.path.basename(directory)}"
            )
        else:
            self.log_text.append(
                f"⚠️ Не найдено подходящих файлов в папке {os.path.basename(directory)}"
            )

    def clear_file_list(self):  # noqa: D401
        self.file_queue.clear()
        self.file_list.clear()
        self.processed_files.clear()
        self.update_file_counter()
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.overall_progress_label.setText("Общий прогресс: 0/0")
        self.overall_progress_bar.setValue(0)
        self.status_label.setText("")
        self.log_text.clear()
        self.log_text.append("🗑️ Очередь очищена")

    def update_file_counter(self):  # noqa: D401
        total = len(self.file_queue)
        processed = len(self.processed_files)
        errors = len(
            [
                i
                for i in range(self.file_list.count())
                if self.file_list.item(i).status == "error"
            ]
        )
        self.file_counter_label.setText(
            f"Файлов в очереди: {total} | Обработано: {processed} | Ошибок: {errors}"
        )

    # --- processing --------------------------------------------------
    def start_processing(self):
        if not self.file_queue:
            return
        self.setAcceptDrops(False)
        self.model_combo.setEnabled(False)
        self.engine_combo.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.clear_list_button.setEnabled(False)
        self.elapsed_timer.start()

        self.transcription_thread = TranscriptionThread(
            self.file_queue.copy(),
            self.model_combo.currentText(),
            "txt" if self.format_combo.currentText().startswith("TXT") else "srt",
            backend=self.engine_combo.currentText(),
        )
        self.transcription_thread.progress.connect(self.update_progress)
        self.transcription_thread.status.connect(self.update_status)
        self.transcription_thread.finished.connect(self.on_file_finished)
        self.transcription_thread.error.connect(self.on_file_error)
        self.transcription_thread.current_file.connect(self.update_current_file)
        self.transcription_thread.overall_progress.connect(self.update_overall_progress)
        self.transcription_thread.start()

    def stop_processing(self):
        if self.transcription_thread:
            self.transcription_thread.stop()
            self.log_text.append("⏹️ Остановка обработки...")
            self.reset_ui_state()
            self.drop_area.setVisible(True)

    # --- signals from thread ---------------------------------------
    def update_progress(self, value):  # noqa: D401
        self.progress_bar.setValue(value)

    def update_status(self, status):  # noqa: D401
        self.status_label.setText(status)

    def update_current_file(self, filename):
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if os.path.basename(item.file_path) == filename:
                item.status = "processing"
                item.update_appearance()

    def update_overall_progress(self, current, total):  # noqa: D401
        self.overall_progress_label.setText(f"Общий прогресс: {current}/{total}")
        if total > 0:
            self.overall_progress_bar.setValue(int((current / total) * 100))

    def on_file_finished(self, file_path, output_path):
        self.processed_files.append(output_path)
        self.log_text.append(f"✅ Создан файл: {os.path.basename(output_path)}")
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.file_path == file_path:
                item.status = "completed"
                item.update_appearance()
                break
        self.update_file_counter()
        if not self.transcription_thread or not self.transcription_thread.isRunning():
            QTimer.singleShot(100, self.on_all_processing_complete)

    def on_file_error(self, file_path, error):
        if file_path:
            self.log_text.append(
                f"❌ Ошибка для {os.path.basename(file_path)}: {error}"
            )
            for i in range(self.file_list.count()):
                item = self.file_list.item(i)
                if item.file_path == file_path:
                    item.status = "error"
                    item.update_appearance()
                    break
        else:
            self.log_text.append(f"❌ {error}")
        self.update_file_counter()

    def on_all_processing_complete(self):
        elapsed_ms = self.elapsed_timer.elapsed()
        hours = elapsed_ms // 3600000
        minutes = (elapsed_ms % 3600000) // 60000
        seconds = (elapsed_ms % 60000) // 1000
        if hours > 0:
            time_str = f"{hours}ч {minutes}м {seconds}с"
        elif minutes > 0:
            time_str = f"{minutes}м {seconds}с"
        else:
            time_str = f"{seconds}с"
        self.status_label.setText("Обработка завершена!")
        self.log_text.append(
            f"✨ Обработка завершена! Создано {len(self.processed_files)} файлов"
        )
        self.log_text.append(f"⏱️ Общее время обработки: {time_str}")
        self.reset_ui_state()

    def reset_ui_state(self):  # noqa: D401
        self.setAcceptDrops(True)
        self.model_combo.setEnabled(True)
        self.engine_combo.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.start_button.setEnabled(bool(self.file_queue))
        self.stop_button.setEnabled(False)
        self.clear_list_button.setEnabled(True)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio/Video to SRT Transcriber - Batch Processing")
        self.setGeometry(100, 100, 700, 800)
        self.central_widget = DragDropWidget()
        self.setCentralWidget(self.central_widget)
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f8f9fa;
            }
            """
        )


def main():
    setup_logging()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
