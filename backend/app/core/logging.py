import logging
import sys

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure application logging once at startup.

    Phase 1 keeps logging simple and dependency-free. Later phases can switch to
    JSON logging without changing application call sites.
    """

    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
