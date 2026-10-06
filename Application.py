"""Start the capillaroscopy analysis tool: ``python3 Application.py``.

The window itself lives in the `gui` package (see gui/app.py), the measurement
in `capillary`, stabilization and the reports in Caper.py.
"""
import logging
import logging.handlers
import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def configure_logging():
    # Rotate the log so a long session cannot grow it without limit (the old
    # log reached tens of megabytes of repeated warnings).
    handler = logging.handlers.RotatingFileHandler(os.path.join(APP_DIR, 'capillaroscopy.log'),
                                                   maxBytes=5_000_000, backupCount=2, encoding='utf-8')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s',
                        handlers=[handler, logging.StreamHandler()])


if __name__ == '__main__':
    sys.path.insert(0, APP_DIR)
    configure_logging()
    from gui.app import main
    main()
