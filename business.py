# Business logic related to transcription
import os
import warnings
import time
import logging
import subprocess
import json
import shutil
from pathlib import Path
from datetime import timedelta
from PySide6.QtCore import QThread, Signal

try:
    import whisper
except ImportError:  # pragma: no cover - optional dependency
    whisper = None

# Настройка логгера
logger = logging.getLogger(__name__)

# Глобальный кэш для моделей
MODEL_CACHE = {}


class ModelManager:
    """Менеджер для кэширования и управления моделями."""

    @staticmethod
    def get_model(model_size, backend="whisper"):
        """Получить модель из кэша или загрузить новую."""
        cache_key = f"{backend}_{model_size}"

        if cache_key in MODEL_CACHE:
            logger.info(f"Используется кэшированная модель: {cache_key}")
            return MODEL_CACHE[cache_key]

        logger.info(f"Загрузка новой модели: {cache_key}")

        # Подавляем предупреждения о symlinks и pkg_resources
        os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            if backend == "faster-whisper":
                from faster_whisper import WhisperModel
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute_type = "float16" if device == "cuda" else "int8"

                model = WhisperModel(
                    model_size,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=os.cpu_count(),
                    num_workers=4,
                )
            else:
                if whisper is None:
                    raise RuntimeError(
                        "whisper package is not installed, выберите 'faster-whisper'"
                    )
                model = whisper.load_model(model_size)

        MODEL_CACHE[cache_key] = model
        return model

    @staticmethod
    def clear_cache():
        """Очистить кэш моделей для освобождения памяти."""
        global MODEL_CACHE
        MODEL_CACHE.clear()
        logger.info("Кэш моделей очищен")


class FFProbeChecker:
    """Проверка доступности ffprobe."""

    _is_available = None

    @classmethod
    def is_available(cls):
        """Проверить доступность ffprobe (с кэшированием результата)."""
        if cls._is_available is not None:
            return cls._is_available

        try:
            result = subprocess.run(
                ['ffprobe', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            cls._is_available = result.returncode == 0
            if cls._is_available:
                logger.info("ffprobe доступен")
            else:
                logger.warning("ffprobe недоступен")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"Ошибка проверки ffprobe: {e}")
            cls._is_available = False

        return cls._is_available


class TranscriptionThread(QThread):
    """Thread that performs transcription of multiple files."""

    progress = Signal(int)
    status = Signal(str)
    finished = Signal(str, str)  # file_path, output_path
    error = Signal(str, str)  # file_path, error_message
    current_file = Signal(str)
    overall_progress = Signal(int, int)  # current, total
    benchmark_result = Signal(str, float)  # engine_name, time_per_minute
    file_not_found = Signal(str)  # file_path that was not found

    def __init__(self, file_paths, model_size, output_format="srt", backend="whisper", language="auto"):
        super().__init__()
        self.file_paths = file_paths
        self.model_size = model_size
        self.output_format = output_format
        self.backend = backend
        self.language = language
        self.is_running = True
        self.total_audio_duration = 0
        self.total_processing_time = 0
        self._should_stop = False

    def run(self):
        try:
            self.status.emit("Загрузка модели...")

            # Определяем устройство для информирования пользователя
            try:
                import torch
                device_info = "GPU (CUDA)" if torch.cuda.is_available() else "CPU"
            except ImportError:
                device_info = "CPU"

            start_load_time = time.time()

            try:
                model = ModelManager.get_model(self.model_size, self.backend)
            except Exception as e:
                logger.error(f"Ошибка загрузки модели: {e}")
                self.error.emit("", f"Не удалось загрузить модель: {str(e)}")
                return

            load_time = time.time() - start_load_time
            self.status.emit(f"Модель загружена ({device_info}) за {load_time:.1f}с")

            total_files = len(self.file_paths)

            for index, file_path in enumerate(self.file_paths):
                if self._should_stop:
                    logger.info("Обработка остановлена пользователем")
                    break

                # Проверяем существование файла перед обработкой
                if not os.path.exists(file_path):
                    logger.warning(f"Файл не найден: {file_path}")
                    self.file_not_found.emit(file_path)
                    self.error.emit(file_path, "Файл был удален или перемещен")
                    continue

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
                            language=None if self.language == "auto" else self.language,
                            beam_size=1,
                            vad_filter=True,
                            vad_parameters=dict(
                                min_silence_duration_ms=500,
                            ),
                        )
                        result_segments = [
                            {"start": s.start, "end": s.end, "text": s.text}
                            for s in segments
                        ]
                        if hasattr(info, 'duration') and info.duration:
                            audio_duration = info.duration
                        # Log detected language if auto
                        if self.language == "auto" and hasattr(info, 'language'):
                            logger.info(f"Определен язык: {info.language}")
                    else:
                        result = model.transcribe(
                            file_path,
                            language=None if self.language == "auto" else self.language,
                            fp16=False
                        )
                        result_segments = result["segments"]
                        if "segments" in result and result["segments"]:
                            last_segment = result["segments"][-1]
                            audio_duration = last_segment["end"]
                        # Log detected language if auto
                        if self.language == "auto" and "language" in result:
                            logger.info(f"Определен язык: {result['language']}")

                    processing_time = time.time() - start_time

                    # Добавляем к общей статистике
                    if audio_duration > 0:
                        self.total_audio_duration += audio_duration
                        self.total_processing_time += processing_time

                    self.progress.emit(80)

                    # Создаем выходной файл
                    input_path = Path(file_path)
                    if self.output_format == "txt":
                        content = self.create_txt(result_segments)
                        output_path = input_path.with_suffix(".txt")
                    else:
                        content = self.create_srt(result_segments)
                        output_path = input_path.with_suffix(".srt")

                    # Безопасное сохранение файла
                    try:
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(content)
                    except IOError as e:
                        logger.error(f"Ошибка записи файла {output_path}: {e}")
                        self.error.emit(file_path, f"Не удалось сохранить файл: {str(e)}")
                        continue

                    self.progress.emit(100)
                    self.finished.emit(file_path, str(output_path))

                except Exception as e:
                    logger.error(f"Ошибка обработки файла {file_path}: {e}", exc_info=True)
                    self.error.emit(file_path, str(e))

            # Отправляем результаты бенчмарка
            if self.total_audio_duration > 0 and self.total_processing_time > 0:
                time_per_minute = (self.total_processing_time / self.total_audio_duration) * 60
                self.benchmark_result.emit(self.backend, time_per_minute)

        except Exception as e:
            logger.error(f"Общая ошибка в потоке транскрибации: {e}", exc_info=True)
            self.error.emit("", f"Общая ошибка: {str(e)}")

    def stop(self):
        """Мягкая остановка потока."""
        self._should_stop = True
        self.is_running = False
        logger.info("Запрошена остановка транскрибации")

    def get_audio_duration(self, file_path):
        """Получает длительность аудио файла в секундах."""
        # Сначала проверяем доступность ffprobe
        if not FFProbeChecker.is_available():
            logger.warning("ffprobe недоступен, длительность не определена")
            return 0

        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                file_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # Таймаут 30 секунд
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data['format']['duration'])
                logger.debug(f"Длительность {file_path}: {duration}с")
                return duration
            else:
                logger.warning(f"ffprobe вернул код ошибки {result.returncode} для {file_path}")
                return 0

        except subprocess.TimeoutExpired:
            logger.error(f"Таймаут при получении длительности для {file_path}")
            return 0
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON от ffprobe для {file_path}: {e}")
            return 0
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении длительности для {file_path}: {e}")
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

                model = ModelManager.get_model(self.model_size, "faster-whisper")

                # Прогрев модели
                self.status.emit("Прогрев Faster-Whisper...")
                warmup_segments, _ = model.transcribe(
                    self.test_file,
                    language="en",
                    beam_size=1,
                    vad_filter=True,
                )
                _ = list(warmup_segments)

                # Реальный тест
                self.status.emit("Тестирование Faster-Whisper (основной запуск)...")
                start_time = time.time()
                segments, info = model.transcribe(
                    self.test_file,
                    language="en",
                    beam_size=1,
                    vad_filter=True,
                )
                _ = list(segments)
                transcribe_time = time.time() - start_time

                audio_duration = info.duration if hasattr(info, 'duration') else 60
                time_per_minute = (transcribe_time / audio_duration) * 60

                results.append(f"🚀 Faster-Whisper ({device_info}):")
                results.append(f"   Транскрипция: {transcribe_time:.2f}с")
                results.append(f"   Скорость: {time_per_minute:.2f}с на минуту аудио")
                results.append(f"   Реальное время: {audio_duration / transcribe_time:.1f}x")

            except Exception as e:
                results.append(f"❌ Faster-Whisper: {str(e)}")

            self.progress.emit(50)

            # Тестируем оригинальный whisper
            if whisper is not None:
                try:
                    self.status.emit("Тестирование OpenAI Whisper...")
                    self.progress.emit(75)

                    model = ModelManager.get_model(self.model_size, "whisper")

                    # Прогрев модели
                    self.status.emit("Прогрев OpenAI Whisper...")
                    _ = model.transcribe(self.test_file, language=None, fp16=False)

                    # Реальный тест
                    self.status.emit("Тестирование OpenAI Whisper (основной запуск)...")
                    start_time = time.time()
                    result = model.transcribe(self.test_file, language=None, fp16=False)
                    transcribe_time = time.time() - start_time

                    if result["segments"]:
                        audio_duration = result["segments"][-1]["end"]
                    else:
                        audio_duration = 60

                    time_per_minute = (transcribe_time / audio_duration) * 60

                    results.append(f"\n🐢 OpenAI Whisper ({device_info}):")
                    results.append(f"   Транскрипция: {transcribe_time:.2f}с")
                    results.append(f"   Скорость: {time_per_minute:.2f}с на минуту аудио")
                    results.append(f"   Реальное время: {audio_duration / transcribe_time:.1f}x")

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
            logger.error(f"Ошибка бенчмарка: {e}", exc_info=True)
            self.error.emit(f"Ошибка бенчмарка: {str(e)}")