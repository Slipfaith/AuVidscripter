# Business logic related to transcription
import os
import warnings
from pathlib import Path
from datetime import timedelta
from PySide6.QtCore import QThread, Signal

try:
    import whisper
except ImportError:  # pragma: no cover - optional dependency
    whisper = None


class TranscriptionThread(QThread):
    """Thread that performs transcription of multiple files."""

    progress = Signal(int)
    status = Signal(str)
    finished = Signal(str, str)  # file_path, output_path
    error = Signal(str, str)  # file_path, error_message
    current_file = Signal(str)
    overall_progress = Signal(int, int)  # current, total

    def __init__(self, file_paths, model_size, output_format="srt", backend="whisper"):
        super().__init__()
        self.file_paths = file_paths
        self.model_size = model_size
        self.output_format = output_format
        self.backend = backend
        self.is_running = True

    def run(self):
        try:
            self.status.emit("Загрузка модели...")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if self.backend == "faster-whisper":
                    from faster_whisper import WhisperModel
                    model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8",
                    )
                else:
                    if whisper is None:
                        raise RuntimeError(
                            "whisper package is not installed, выбрать 'faster-whisper'"
                        )
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

                    if self.backend == "faster-whisper":
                        segments, _ = model.transcribe(file_path, language="en")
                        result_segments = [
                            {"start": s.start, "end": s.end, "text": s.text}
                            for s in segments
                        ]
                    else:
                        result = model.transcribe(file_path, language="en", fp16=False)
                        result_segments = result["segments"]

                    self.progress.emit(80)
                    self.status.emit("Создание файла...")

                    input_path = Path(file_path)
                    if self.output_format == "txt":
                        content = self.create_txt(result_segments)
                        output_path = input_path.with_suffix(".txt")
                    else:
                        content = self.create_srt(result_segments)
                        output_path = input_path.with_suffix(".srt")

                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    self.progress.emit(100)
                    self.finished.emit(file_path, str(output_path))

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

    def create_txt(self, segments):
        """Return plain text without time codes from segments."""
        return "\n".join(segment["text"].strip() for segment in segments)

    def format_timestamp(self, seconds):
        td = timedelta(seconds=seconds)
        hours = td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        seconds = td.seconds % 60
        milliseconds = td.microseconds // 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
