import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console"],
            "level": "INFO",
        },
        "sqlalchemy": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "sqlalchemy.engine": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "sqlalchemy.pool": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "sqlalchemy.dialects": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "alembic": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
