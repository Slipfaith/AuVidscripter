"""Logging configuration for the application."""

import logging
import warnings


def setup_logging():
    """Configure logging and warning filters."""
    warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")
    logging.getLogger("whisper").setLevel(logging.ERROR)
