"""Entry point for the Audio/Video Transcriber application."""

import os

# Set environment variables for better rendering
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

from gui import main

if __name__ == "__main__":
    main()