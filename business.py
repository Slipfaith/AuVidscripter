# Business logic related to transcription
import os
import warnings
import time
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
    benchmark_result = Signal(str, float)  # engine_name, time_per_minute

    def __init__(self, file_paths, model_size, output_format="srt", backend="whisper"):
        super().__init__()
        self.file_paths = file_paths
        self.model_size = model_size
        self.output_format = output_format
        self.backend = backend
        self.is_running = True
        self.total_audio_duration = 0
        self.total_processing_time = 0

    def run(self):
        try:
            self.status.emit("Загрузка модели...")

            # Подавляем предупреждения о symlinks и pkg_resources
            os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

            # Определяем устройство для информирования пользователя
            try:
                import torch
                device_info = "GPU (CUDA)" if torch.cuda.is_available() else "CPU"
            except ImportError:
                device_info = "CPU"

            start_load_time = time.time()

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if self.backend == "faster-whisper":
                    from faster_whisper import WhisperModel
                    import torch

                    # Определяем доступное устройство
                    device = "cuda" if torch.cuda.is_available() else "cpu"

                    # Оптимальный compute_type для разных устройств
                    if device == "cuda":
                        compute_type = "float16"  # Быстрее на GPU
                    else:
                        compute_type = "int8"  # Быстрее на CPU

                    model = WhisperModel(
                        self.model_size,
                        device=device,
                        compute_type=compute_type,
                        cpu_threads=os.cpu_count(),  # Используем все ядра CPU
                        num_workers=4,  # Параллельная обработка
                    )
                else:
                    if whisper is None:
                        raise RuntimeError(
                            "whisper package is not installed, выбрать 'faster-whisper'"
                        )
                    model = whisper.load_model(self.model_size)

            load_time = time.time() - start_load_time
            self.status.emit(f"Модель загружена ({device_info}) за {load_time:.1f}с")

            total_files = len(self.file_paths)

            for index, file_path in enumerate(self.file_paths):
                if not self.is_running:
                    break

                self.current_file.emit(os.path.basename(file_path))
                self.overall_progress.emit(index + 1, total_files)

                try:
                    # Получаем длительность аудио
                    audio_duration = self.get_audio_duration(file_path)

                    self.status.emit("Транскрибирование")
                    self.progress.emit(30)

                    start_time = time.time()

                    if self.backend == "faster-whisper":
                        segments, info = model.transcribe(
                            file_path,
                            language="en",
                            beam_size=1,  # Быстрее с beam_size=1
                            vad_filter=True,  # Фильтрация тишины
                            vad_parameters=dict(
                                min_silence_duration_ms=500,
                            ),
                        )
                        result_segments = [
                            {"start": s.start, "end": s.end, "text": s.text}
                            for s in segments
                        ]
                        # Получаем длительность из info если доступно
                        if hasattr(info, 'duration') and info.duration:
                            audio_duration = info.duration
                    else:
                        result = model.transcribe(file_path, language="en", fp16=False)
                        result_segments = result["segments"]
                        # Получаем длительность из результата если доступно
                        if "segments" in result and result["segments"]:
                            last_segment = result["segments"][-1]
                            audio_duration = last_segment["end"]

                    processing_time = time.time() - start_time

                    # Добавляем к общей статистике
                    if audio_duration > 0:
                        self.total_audio_duration += audio_duration
                        self.total_processing_time += processing_time

                    self.progress.emit(80)

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

            # Отправляем результаты бенчмарка
            if self.total_audio_duration > 0 and self.total_processing_time > 0:
                # Время обработки на минуту аудио
                time_per_minute = (self.total_processing_time / self.total_audio_duration) * 60
                self.benchmark_result.emit(self.backend, time_per_minute)

        except Exception as e:  # noqa: BLE001
            self.error.emit("", f"Общая ошибка: {str(e)}")

    def stop(self):
        self.is_running = False

    def get_audio_duration(self, file_path):
        """Получает длительность аудио файла в секундах."""
        try:
            # Пытаемся использовать ffprobe для получения длительности
            import subprocess
            import json

            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                file_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data['format']['duration'])
                return duration
        except:
            pass

        # Если не удалось получить длительность, возвращаем 0
        return 0

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


class BenchmarkThread(QThread):
    """Thread that performs benchmark comparison between whisper and faster-whisper."""

    status = Signal(str)
    progress = Signal(int)
    result = Signal(str)
    error = Signal(str)

    def __init__(self, test_file, model_size="tiny"):
        super().__init__()
        self.test_file = test_file
        self.model_size = model_size

    def run(self):
        try:
            results = []

            # Подавляем предупреждения
            os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
            warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

            # Определяем доступное устройство
            try:
                import torch
                device_info = "GPU (CUDA)" if torch.cuda.is_available() else "CPU"
                has_gpu = torch.cuda.is_available()
            except ImportError:
                device_info = "CPU"
                has_gpu = False

            # Тестируем faster-whisper
            try:
                self.status.emit("Тестирование Faster-Whisper...")
                self.progress.emit(25)

                from faster_whisper import WhisperModel
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute_type = "float16" if device == "cuda" else "int8"

                # Загрузка модели
                start_time = time.time()
                model = WhisperModel(
                    self.model_size,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=os.cpu_count(),
                    num_workers=4,
                )
                load_time = time.time() - start_time

                # Прогрев модели (первый запуск всегда медленнее)
                self.status.emit("Прогрев Faster-Whisper...")
                warmup_segments, _ = model.transcribe(
                    self.test_file,
                    language="en",
                    beam_size=1,
                    vad_filter=True,
                )
                _ = list(warmup_segments)  # Потребляем генератор

                # Реальный тест
                self.status.emit("Тестирование Faster-Whisper (основной запуск)...")
                start_time = time.time()
                segments, info = model.transcribe(
                    self.test_file,
                    language="en",
                    beam_size=1,
                    vad_filter=True,
                )
                # Потребляем генератор
                _ = list(segments)
                transcribe_time = time.time() - start_time

                audio_duration = info.duration if hasattr(info, 'duration') else 60
                time_per_minute = (transcribe_time / audio_duration) * 60

                results.append(f"🚀 Faster-Whisper ({device_info}):")
                results.append(f"   Загрузка модели: {load_time:.2f}с")
                results.append(f"   Транскрипция: {transcribe_time:.2f}с")
                results.append(f"   Скорость: {time_per_minute:.2f}с на минуту аудио")
                results.append(f"   Реальное время: {audio_duration / transcribe_time:.1f}x")

                del model  # Освобождаем память

            except Exception as e:
                results.append(f"❌ Faster-Whisper: {str(e)}")

            self.progress.emit(50)

            # Тестируем оригинальный whisper
            if whisper is not None:
                try:
                    self.status.emit("Тестирование OpenAI Whisper...")
                    self.progress.emit(75)

                    # Загрузка модели
                    start_time = time.time()
                    model = whisper.load_model(self.model_size)
                    load_time = time.time() - start_time

                    # Прогрев модели
                    self.status.emit("Прогрев OpenAI Whisper...")
                    _ = model.transcribe(self.test_file, language="en", fp16=False)

                    # Реальный тест
                    self.status.emit("Тестирование OpenAI Whisper (основной запуск)...")
                    start_time = time.time()
                    result = model.transcribe(self.test_file, language="en", fp16=False)
                    transcribe_time = time.time() - start_time

                    if result["segments"]:
                        audio_duration = result["segments"][-1]["end"]
                    else:
                        audio_duration = 60  # По умолчанию

                    time_per_minute = (transcribe_time / audio_duration) * 60

                    results.append(f"\n🐢 OpenAI Whisper ({device_info}):")
                    results.append(f"   Загрузка модели: {load_time:.2f}с")
                    results.append(f"   Транскрипция: {transcribe_time:.2f}с")
                    results.append(f"   Скорость: {time_per_minute:.2f}с на минуту аудио")
                    results.append(f"   Реальное время: {audio_duration / transcribe_time:.1f}x")

                    del model  # Освобождаем память

                except Exception as e:
                    results.append(f"\n❌ OpenAI Whisper: {str(e)}")
            else:
                results.append(f"\n❌ OpenAI Whisper не установлен")

            self.progress.emit(100)

            # Формируем итоговый отчет
            summary = f"📊 Результаты бенчмарка (модель: {self.model_size})\n"
            summary += f"📁 Тестовый файл: {os.path.basename(self.test_file)}\n"
            summary += f"💻 Устройство: {device_info}\n"
            summary += "─" * 50 + "\n"
            summary += "\n".join(results)

            # Добавляем рекомендации
            summary += "\n\n💡 Рекомендации:\n"
            if not has_gpu:
                summary += "• Для ускорения в 4-5 раз используйте GPU (NVIDIA с CUDA)\n"
            summary += "• Faster-Whisper эффективнее на длинных файлах\n"
            summary += "• Модель 'base' дает лучший баланс скорости и качества\n"
            if device_info == "CPU":
                summary += "• На CPU разница между движками минимальна\n"

            self.result.emit(summary)

        except Exception as e:
            self.error.emit(f"Ошибка бенчмарка: {str(e)}")