"""Simple logging setup."""
import logging
import sys


def configure_logging(environment: str = "development") -> None:
    root = logging.getLogger()
    if root.handlers:  # already set up (uvicorn --reload imports the app again)
        return
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"))
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
