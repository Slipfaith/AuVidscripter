# Business logic related to transcription
import os
import warnings
from pathlib import Path
from datetime import timedelta
from PySide6.QtCore import QThread, Signal
import whisper


class TranscriptionThread(QThread):
    """Thread that performs transcription of multiple files."""

    progress = Signal(int)
    status = Signal(str)
    finished = Signal(str, str)  # file_path, srt_path
    error = Signal(str, str)  # file_path, error_message
    current_file = Signal(str)
    overall_progress = Signal(int, int)  # current, total

    def __init__(self, file_paths, model_size):
        super().__init__()
        self.file_paths = file_paths
        self.model_size = model_size
        self.is_running = True

    def run(self):
        try:
            self.status.emit("Загрузка модели...")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = whisper.load_model(self.model_size)

            total_files = len(self.file_paths)

            for index, file_path in enumerate(self.file_paths):
                if not self.is_running:
                    break

                self.current_file.emit(os.path.basename(file_path))
                self.overall_progress.emit(index + 1, total_files)

                try:
                    self.status.emit(
                        f"Транскрибирование: {os.path.basename(file_path)}"
                    )
                    self.progress.emit(30)

                    result = model.transcribe(file_path, language="en", fp16=False)

                    self.progress.emit(80)
                    self.status.emit("Создание SRT файла...")

                    srt_content = self.create_srt(result["segments"])

                    input_path = Path(file_path)
                    srt_path = input_path.with_suffix(".srt")

                    with open(srt_path, "w", encoding="utf-8") as f:
                        f.write(srt_content)

                    self.progress.emit(100)
                    self.finished.emit(file_path, str(srt_path))

                except Exception as e:  # noqa: BLE001
                    self.error.emit(file_path, str(e))

        except Exception as e:  # noqa: BLE001
            self.error.emit("", f"Общая ошибка: {str(e)}")

    def stop(self):
        self.is_running = False

    def create_srt(self, segments):
        srt_content = ""
        for i, segment in enumerate(segments, 1):
            start_time = self.format_timestamp(segment["start"])
            end_time = self.format_timestamp(segment["end"])
            text = segment["text"].strip()

            srt_content += f"{i}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{text}\n\n"

        return srt_content

    def format_timestamp(self, seconds):
        td = timedelta(seconds=seconds)
        hours = td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        seconds = td.seconds % 60
        milliseconds = td.microseconds // 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
