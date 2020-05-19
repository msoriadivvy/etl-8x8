import logging
import os

import logmatic


DEFAULT_FORMAT = '%(message)s %(levelname)s %(pathname)s %(funcName)s %(lineno)d'
DEFAULT_LEVEL = getattr(logging, os.environ.get('LOG_LEVEL', 'DEBUG').upper(), logging.DEBUG)


def setup_logger(name: str, fmt: str = DEFAULT_FORMAT, level: int = DEFAULT_LEVEL):
    handler = logging.StreamHandler()
    handler.setFormatter(logmatic.JsonFormatter(fmt=fmt))

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
