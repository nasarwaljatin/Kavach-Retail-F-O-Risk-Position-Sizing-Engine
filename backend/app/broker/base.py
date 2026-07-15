from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class Position:
    symbol: str
    exchange: str
    qty: int
    avg_price: float
    ltp: float
    pnl: float
    product_type: str
    instrument_type: str
    symbol_token: str
    exposure: float  # abs(qty * ltp)

@dataclass
class MarginData:
    net: float
    available_cash: float
    used_margin: float
    collateral: float
    unrealized_mtm: float
    realized_mtm: float
    utilisation_pct: float  # computed as (used_margin / net) * 100

@dataclass
class OrderParams:
    symbol: str
    exchange: str
    transaction_type: str  # BUY/SELL
    order_type: str  # MARKET/LIMIT
    product_type: str
    quantity: int
    price: float = 0.0
    trigger_price: float = 0.0
    symbol_token: str = ""

@dataclass
class OrderResult:
    order_id: str
    status: str
    message: str

class BaseBroker(ABC):
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the broker API and establish a session."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Fetch current open positions from the broker."""
        pass

    @abstractmethod
    def get_margins(self) -> MarginData:
        """Fetch current funds and margin utilization from the broker."""
        pass

    @abstractmethod
    def get_quote(self, exchange: str, symbol: str, token: str) -> Dict:
        """Get the Last Traded Price (LTP) or quote for a symbol."""
        pass

    @abstractmethod
    def place_order(self, params: OrderParams) -> OrderResult:
        """Place an order with the broker."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, variety: str) -> OrderResult:
        """Cancel an active order."""
        pass

    @abstractmethod
    def square_off_all(self) -> List[OrderResult]:
        """Emergency square off all positions by executing opposing market orders."""
        pass

    @abstractmethod
    def get_order_book(self) -> List[Dict]:
        """Fetch the order history / status list for the day."""
        pass
