"""
Broker factory — the single place that decides which broker implementation
the rest of the system talks to.

Nothing in risk_monitor, API routes, or anywhere else should import
AngelOneBroker or PaperBrokerAdapter directly.  All callers use:

    from app.broker.factory import get_broker
    broker = get_broker()
"""

import logging

from app.core.config import settings
from app.broker.base import BaseBroker
from app.broker.angelone import AngelOneBroker
from app.broker.paper import PaperBrokerAdapter

logger = logging.getLogger("kavach.broker.factory")


def get_broker() -> BaseBroker:
    """
    Return the appropriate broker based on PAPER_MODE setting.

    PAPER_MODE=True  → PaperBrokerAdapter(AngelOneBroker())
      - Reads: live data from Angel One (realistic margin/position data)
      - Writes: DB-only paper_orders log, no real orders
    PAPER_MODE=False → AngelOneBroker()
      - Full live trading mode: real orders are placed
    """
    real_broker = AngelOneBroker()

    if settings.PAPER_MODE:
        logger.info(
            "Broker factory: PAPER_MODE=True — using PaperBrokerAdapter. "
            "No real orders will be placed."
        )
        return PaperBrokerAdapter(real_broker)

    logger.info("Broker factory: PAPER_MODE=False — using live AngelOneBroker.")
    return real_broker
