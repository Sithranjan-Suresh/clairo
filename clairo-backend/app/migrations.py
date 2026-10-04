"""Programmatic Alembic runner, so a deploy never needs a separate migrate step."""
import logging
import os

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)

_ALEMBIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alembic")


def run_migrations(connection=None) -> None:
    cfg = Config()
    if connection is not None:
        cfg.attributes["connection"] = connection
    cfg.set_main_option("script_location", _ALEMBIC_DIR)
    command.upgrade(cfg, "head")
    logger.info("database migrations applied")
