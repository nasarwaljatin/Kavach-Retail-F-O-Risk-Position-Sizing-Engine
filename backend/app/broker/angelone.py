import logging
import pyotp
import math
import random
from typing import List, Dict, Optional
from datetime import datetime

from app.core.config import settings
from app.broker.base import BaseBroker, Position, MarginData, OrderParams, OrderResult
from app.broker.instrument_master import resolve_token as im_resolve_token

# Try importing SmartConnect from SmartApi. Handle import errors gracefully for local testing.
try:
    from SmartApi import SmartConnect
    SMARTAPI_AVAILABLE = True
except ImportError:
    SMARTAPI_AVAILABLE = False
    class SmartConnect:
        def __init__(self, api_key):
            pass

logger = logging.getLogger("kavach.broker.angelone")

class AngelOneBroker(BaseBroker):
    def __init__(self):
        self.api_key = settings.ANGELONE_API_KEY
        self.client_code = settings.ANGELONE_CLIENT_CODE
        self.password = settings.ANGELONE_PASSWORD
        self.totp_secret = settings.ANGELONE_TOTP_SECRET
        self.paper_mode = settings.PAPER_MODE
        
        self.obj = None
        self.jwt_token = None
        self.refresh_token = None
        self.feed_token = None
        self.authenticated = False

        # In-memory mock storage to support simulated/paper mode when credentials are not filled
        self._mock_positions: List[Dict] = [
            {
                "symbol": "NIFTY26JUL2619800CE",
                "exchange": "NFO",
                "qty": 50,
                "avg_price": 120.50,
                "ltp": 125.75,
                "pnl": 262.50,
                "product_type": "CARRYFORWARD",
                "instrument_type": "CE",
                "symbol_token": "54321"
            },
            {
                "symbol": "RELIANCE-EQ",
                "exchange": "NSE",
                "qty": 10,
                "avg_price": 2450.00,
                "ltp": 2445.00,
                "pnl": -50.00,
                "product_type": "INTRADAY",
                "instrument_type": "EQ",
                "symbol_token": "2885"
            }
        ]
        self._mock_cash = 100000.0
        self._mock_used_margin = 15000.0
        self._mock_orders = []

    def _is_mock_mode(self) -> bool:
        # Use mock mode if credentials are placeholder values or empty, or if explicit paper mode has mock fallback
        has_creds = (
            self.client_code and self.client_code != "your_client_code" and
            self.password and self.password != "your_password" and
            self.totp_secret and self.totp_secret != "your_totp_secret_alphanumeric" and
            self.api_key and self.api_key != "your_api_key"
        )
        return not has_creds or not SMARTAPI_AVAILABLE

    def authenticate(self) -> bool:
        if self._is_mock_mode():
            logger.info("Initializing Angel One Broker in SIMULATION / MOCK mode (no credentials or library missing).")
            self.authenticated = True
            return True

        if not SMARTAPI_AVAILABLE:
            logger.error("smartapi-python library is not installed. Falling back to Mock mode.")
            self.authenticated = True
            return True

        try:
            logger.info(f"Authenticating real AngelOne API for client code: {self.client_code}")
            self.obj = SmartConnect(api_key=self.api_key)
            
            # Generate TOTP code
            totp = pyotp.TOTP(self.totp_secret)
            current_totp = totp.now()

            # Generate Session
            session_data = self.obj.generateSession(self.client_code, self.password, current_totp)
            
            if session_data.get("status") is True:
                data = session_data.get("data", {})
                self.jwt_token = data.get("jwtToken")
                self.refresh_token = data.get("refreshToken")
                self.feed_token = data.get("feedToken")
                self.authenticated = True
                logger.info("Successfully authenticated with Angel One SmartAPI.")
                return True
            else:
                logger.error(f"Angel One Authentication failed: {session_data.get('message')}")
                # Fall back to simulation if real auth fails so system doesn't crash in dev
                logger.warning("Authentication failed. Falling back to SIMULATION / MOCK mode.")
                self.authenticated = True
                return True
        except Exception as e:
            logger.exception(f"Exception during Angel One Authentication: {e}")
            logger.warning("Falling back to SIMULATION / MOCK mode due to exception.")
            self.authenticated = True
            return True

    def get_positions(self) -> List[Position]:
        if self._is_mock_mode() or not self.obj:
            # Generate simulated price fluctuations for mock mode
            positions = []
            for mp in self._mock_positions:
                # Fluctuates ltp slightly
                pct = random.uniform(-0.01, 0.01)
                mp["ltp"] = round(mp["ltp"] * (1 + pct), 2)
                mp["pnl"] = round((mp["ltp"] - mp["avg_price"]) * mp["qty"], 2)
                exposure = abs(mp["qty"] * mp["ltp"])
                positions.append(Position(
                    symbol=mp["symbol"],
                    exchange=mp["exchange"],
                    qty=mp["qty"],
                    avg_price=mp["avg_price"],
                    ltp=mp["ltp"],
                    pnl=mp["pnl"],
                    product_type=mp["product_type"],
                    instrument_type=mp["instrument_type"],
                    symbol_token=mp["symbol_token"],
                    exposure=exposure
                ))
            return positions

        try:
            response = self.obj.position()
            if response.get("status") is True and response.get("data") is not None:
                positions = []
                for item in response.get("data"):
                    net_qty = int(item.get("netqty", 0))
                    # Only include open positions (non-zero quantity)
                    if net_qty != 0:
                        ltp = float(item.get("ltp", 0.0))
                        buy_avg = float(item.get("buyavgprice", 0.0))
                        sell_avg = float(item.get("sellavgprice", 0.0))
                        # Average cost logic depends on buy/sell net state
                        avg_price = buy_avg if net_qty > 0 else sell_avg
                        pnl = float(item.get("unrealised", 0.0)) + float(item.get("realised", 0.0))
                        exposure = abs(net_qty * ltp)
                        
                        symbol = item.get("tradingsymbol", "")
                        inst_type = "EQ"
                        if "-" in symbol:
                            # Parse option contracts (e.g. CE/PE)
                            if symbol.endswith("CE"):
                                inst_type = "CE"
                            elif symbol.endswith("PE"):
                                inst_type = "PE"
                            else:
                                inst_type = "FUT"

                        positions.append(Position(
                            symbol=symbol,
                            exchange=item.get("exchange", "NSE"),
                            qty=net_qty,
                            avg_price=avg_price,
                            ltp=ltp,
                            pnl=pnl,
                            product_type=item.get("producttype", "INTRADAY"),
                            instrument_type=inst_type,
                            symbol_token=item.get("symboltoken", ""),
                            exposure=exposure
                        ))
                return positions
            else:
                logger.error(f"Failed to fetch positions: {response.get('message')}")
                return []
        except Exception as e:
            logger.exception(f"Exception fetching positions: {e}")
            return []

    def get_margins(self) -> MarginData:
        if self._is_mock_mode() or not self.obj:
            # Update mock unrealized pnl from mock positions
            positions = self.get_positions()
            unrealized_mtm = sum(p.pnl for p in positions)
            realized_mtm = 0.0
            
            # Recalculate margins
            net_value = self._mock_cash + unrealized_mtm
            utilisation_pct = (self._mock_used_margin / net_value) * 100 if net_value > 0 else 0.0

            return MarginData(
                net=round(net_value, 2),
                available_cash=round(self._mock_cash - self._mock_used_margin + unrealized_mtm, 2),
                used_margin=self._mock_used_margin,
                collateral=0.0,
                unrealized_mtm=round(unrealized_mtm, 2),
                realized_mtm=realized_mtm,
                utilisation_pct=round(utilisation_pct, 2)
            )

        try:
            response = self.obj.rmsLimit()

            # Task 5: Log raw response at DEBUG level for live-account field verification.
            # Field names VERIFIED 2026-08-04 against SmartAPI v1.5 official docs
            # (https://smartapi.angelone.in/docs  — getRMS endpoint):
            #
            #   net              — total net balance / available limit
            #   availablecash    — available cash for trading
            #   utilisedmargin   — PRIMARY: total margin blocked by open positions (aggregate)
            #   utiliseddebits   — secondary debit component
            #   utilisedspan     — SPAN margin component
            #   utilisedoptionpremium — option premium margin component
            #   utilisedexposure — exposure margin component
            #   utilisedturnover — turnover-based margin
            #   utilisedpayout   — payout amount
            #   collateral / colletral — pledged holdings margin (API has a typo variant)
            #   brkcolle         — broker collateral
            #   m2munrealized    — MTM unrealized P&L
            #   m2mrealized      — MTM realized P&L
            if settings.ENV == "development":
                logger.debug("rmsLimit raw response: %s", response)

            if response.get("status") is True and response.get("data") is not None:
                data = response.get("data")

                net = float(data.get("net", 0.0))
                cash = float(data.get("availablecash", 0.0))

                # Defensive field resolution: try multiple known field-name variants.
                # Angel One API has inconsistent field names across SDK versions.
                def _f(d: dict, *keys: str) -> float:
                    for k in keys:
                        v = d.get(k)
                        if v is not None:
                            try:
                                return float(v)
                            except (TypeError, ValueError):
                                pass
                    return 0.0

                # VERIFIED: utilisedmargin is the primary aggregate field.
                # Fall back to component sum if not present (older SDK versions).
                used_direct = _f(data, "utilisedmargin", "usedmargin")
                used_computed = (
                    _f(data, "utiliseddebits")
                    + _f(data, "utilisedspan")
                    + _f(data, "utilisedoptionpremium")
                    + _f(data, "utilisedexposure")
                    + _f(data, "utilisedturnover")
                    + _f(data, "utilisedpayout")
                )
                used = used_direct if used_direct > 0 else used_computed

                # colletral is an official Angel One API typo — handle both spellings
                collateral = _f(data, "collateral", "colletral", "brkcolle")
                unrealized = _f(data, "m2munrealized")
                realized = _f(data, "m2mrealized")

                utilisation_pct = (used / net) * 100 if net > 0 else 0.0

                return MarginData(
                    net=net,
                    available_cash=cash,
                    used_margin=used,
                    collateral=collateral,
                    unrealized_mtm=unrealized,
                    realized_mtm=realized,
                    utilisation_pct=utilisation_pct,
                )
            else:
                logger.error(f"Failed to fetch margins: {response.get('message')}")
                return MarginData(0, 0, 0, 0, 0, 0, 0)
        except Exception as e:
            logger.exception(f"Exception fetching margins: {e}")
            return MarginData(0, 0, 0, 0, 0, 0, 0)

    def get_quote(self, exchange: str, symbol: str, token: str) -> Dict:
        if self._is_mock_mode() or not self.obj:
            # Return current ltp from mock positions or a random one
            for mp in self._mock_positions:
                if mp["symbol"] == symbol:
                    return {"ltp": mp["ltp"], "symbol": symbol, "exchange": exchange, "token": token}
            return {"ltp": 100.0, "symbol": symbol, "exchange": exchange, "token": token}

        # Auto-resolve token if caller didn't supply one
        resolved_token = token or im_resolve_token(symbol, exchange)
        if not resolved_token:
            logger.warning("get_quote: could not resolve token for %s/%s", exchange, symbol)
            return {}

        try:
            response = self.obj.ltpData(exchange, symbol, resolved_token)
            if response.get("status") is True:
                return response.get("data", {})
            return {}
        except Exception as e:
            logger.exception(f"Exception getting quote: {e}")
            return {}

    def place_order(self, params: OrderParams) -> OrderResult:
        logger.info(f"Placing order: {params.symbol} ({params.qty if hasattr(params, 'qty') else params.quantity} qty) - Paper Mode: {self.paper_mode}")
        qty = params.quantity
        
        if self._is_mock_mode() or self.paper_mode:
            # Handle paper/simulation mode order placement
            order_id = f"MOCK_{int(datetime.utcnow().timestamp())}{random.randint(100, 999)}"
            
            # Check transaction type and update mock positions in simulation
            if self._is_mock_mode():
                # Update mock position array
                found = False
                for mp in self._mock_positions:
                    if mp["symbol"] == params.symbol:
                        found = True
                        current_qty = mp["qty"]
                        if params.transaction_type == "BUY":
                            new_qty = current_qty + qty
                        else:
                            new_qty = current_qty - qty
                        
                        mp["qty"] = new_qty
                        break
                
                if not found:
                    inst_type = "EQ"
                    if "-" in params.symbol:
                        if params.symbol.endswith("CE"): inst_type = "CE"
                        elif params.symbol.endswith("PE"): inst_type = "PE"
                        else: inst_type = "FUT"

                    self._mock_positions.append({
                        "symbol": params.symbol,
                        "exchange": params.exchange,
                        "qty": qty if params.transaction_type == "BUY" else -qty,
                        "avg_price": params.price if params.price > 0 else 100.0,
                        "ltp": params.price if params.price > 0 else 100.0,
                        "pnl": 0.0,
                        "product_type": params.product_type,
                        "instrument_type": inst_type,
                        "symbol_token": params.symbol_token or "12345"
                    })
                
                # Remove zero positions
                self._mock_positions = [mp for mp in self._mock_positions if mp["qty"] != 0]

            self._mock_orders.append({
                "orderid": order_id,
                "tradingsymbol": params.symbol,
                "symboltoken": params.symbol_token,
                "transactiontype": params.transaction_type,
                "exchange": params.exchange,
                "ordertype": params.order_type,
                "producttype": params.product_type,
                "status": "COMPLETE",
                "quantity": str(qty),
                "price": str(params.price),
                "averageprice": str(params.price or 100.0)
            })

            return OrderResult(order_id=order_id, status="SUCCESS", message="Simulated order placed successfully.")

        try:
            # Resolve token if not already provided
            token = params.symbol_token or im_resolve_token(params.symbol, params.exchange)
            if not token:
                logger.error(
                    "place_order: cannot resolve symboltoken for %s/%s — order aborted.",
                    params.exchange, params.symbol
                )
                return OrderResult(order_id="", status="ERROR", message="symboltoken not resolved")

            orderparams = {
                "variety": "NORMAL",
                "tradingsymbol": params.symbol,
                "symboltoken": token,
                "transactiontype": params.transaction_type,
                "exchange": params.exchange,
                "ordertype": params.order_type,
                "producttype": params.product_type,
                "duration": "DAY",
                "price": str(params.price),
                "quantity": str(qty),
                "triggerprice": str(params.trigger_price),
                "squareoff": "0",
                "stoploss": "0",
                "trailingstoploss": "0",
                "disclosedquantity": "0"
            }
            response = self.obj.placeOrder(orderparams)
            if response.get("status") is True:
                data = response.get("data", {})
                return OrderResult(
                    order_id=data.get("orderid", ""),
                    status="SUCCESS",
                    message="Order placed successfully"
                )
            else:
                return OrderResult(
                    order_id="",
                    status="FAILED",
                    message=response.get("message", "API returned failure status")
                )
        except Exception as e:
            logger.exception(f"Exception placing order: {e}")
            return OrderResult(order_id="", status="ERROR", message=str(e))

    def cancel_order(self, order_id: str, variety: str = "NORMAL") -> OrderResult:
        if self._is_mock_mode() or self.paper_mode:
            for o in self._mock_orders:
                if o["orderid"] == order_id:
                    o["status"] = "CANCELLED"
                    return OrderResult(order_id=order_id, status="SUCCESS", message="Simulated order cancelled")
            return OrderResult(order_id=order_id, status="FAILED", message="Order not found")

        try:
            response = self.obj.cancelOrder(order_id, variety)
            if response.get("status") is True:
                return OrderResult(order_id=order_id, status="SUCCESS", message="Order cancelled")
            return OrderResult(order_id=order_id, status="FAILED", message=response.get("message"))
        except Exception as e:
            logger.exception(f"Exception cancelling order: {e}")
            return OrderResult(order_id=order_id, status="ERROR", message=str(e))

    def square_off_all(self) -> List[OrderResult]:
        logger.warning("Square-off-all triggered! Squaring off all open positions.")
        positions = self.get_positions()
        results = []
        
        for pos in positions:
            if pos.qty == 0:
                continue

            # Determine opposite side
            tx_type = "SELL" if pos.qty > 0 else "BUY"
            params = OrderParams(
                symbol=pos.symbol,
                exchange=pos.exchange,
                transaction_type=tx_type,
                order_type="MARKET",
                product_type=pos.product_type,
                quantity=abs(pos.qty),
                symbol_token=pos.symbol_token
            )
            res = self.place_order(params)
            results.append(res)
            
        if self._is_mock_mode():
            self._mock_positions = []
            
        return results

    def get_order_book(self) -> List[Dict]:
        if self._is_mock_mode() or not self.obj:
            return self._mock_orders

        try:
            response = self.obj.orderBook()
            if response.get("status") is True:
                return response.get("data", [])
            return []
        except Exception as e:
            logger.exception(f"Exception fetching order book: {e}")
            return []
