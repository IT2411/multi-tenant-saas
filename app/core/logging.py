import logging
import sys
from typing import Any, cast

import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


def drop_color_message_key(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Uvicorn logs output a redundant `color_message` field in logs; strip it."""
    event_dict.pop("color_message", None)
    return event_dict


def setup_logging() -> None:
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        drop_color_message_key,
    ]

    formatter_processor: Processor
    if settings.ENVIRONMENT == "production":
        formatter_processor = cast("Processor", structlog.processors.JSONRenderer())
    else:
        formatter_processor = cast("Processor", structlog.dev.ConsoleRenderer(colors=True))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processor=formatter_processor,
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.LOG_LEVEL)

    for _log in ["uvicorn", "uvicorn.error", "uvicorn.access", "asyncpg", "sqlalchemy.engine"]:
        logging.getLogger(_log).handlers.clear()
        logging.getLogger(_log).propagate = True

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
