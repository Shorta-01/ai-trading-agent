"""Worker entrypoint for placeholder jobs."""

import logging

from portfolio_outlook_worker.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def start_worker() -> None:
    logger.info(
        "Worker gestart in veilige placeholder-modus (paper-only=%s, env=%s).",
        settings.paper_only_mode,
        settings.environment,
    )


if __name__ == "__main__":
    start_worker()
