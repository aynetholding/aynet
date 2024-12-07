import ccxt 
import logging
import sqlite3
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

class BitmexTrader:
    def __init__(self, api_key, api_secret, testnet=True, db_path="trading_bot.db"):
        self.exchange = ccxt.bitmex({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            }
        })

        if testnet:
            self.exchange.set_sandbox_mode(True)

        self.symbol = "XBTUSD"
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        self.positions = {}
        self.orders = {}
        self.orderbook = {}
        self.last_orderbook_update = None
        self.last_order_time = None

        self.balance = {
            'free': 0,
            'used': 0,
            'total': 0
        }

        self.db = self.initialize_database(db_path)
        self.initialize_exchange()

    def initialize_database(self, db_path):
        try:
            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()
            
            # Orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    symbol TEXT,
                    side TEXT,
                    price REAL,
                    amount REAL,
                    stop_price REAL,
                    status TEXT,
                    order_type TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Positions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    side TEXT,
                    size REAL,
                    entry_price REAL,
                    exit_price REAL,
                    pnl REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    symbol TEXT,
                    side TEXT,
                    price REAL,
                    amount REAL,
                    cost REAL,
                    pnl REAL,
                    slippage REAL
                )
            """)
            
            connection.commit()
            return connection
            
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")
            raise

    def initialize_exchange(self):
        try:
            self.exchange.load_markets()
            self.update_balance()
            self.logger.info("Exchange initialized successfully")
        except Exception as e:
            self.logger.error(f"Exchange initialization error: {e}")
            raise

    def update_balance(self):
        try:
            balance = self.exchange.fetch_balance()
            
            if not isinstance(balance, dict):
                raise ValueError("Invalid balance response")

            self.balance = {
                'free': float(balance.get('BTC', {}).get('free', 0)),
                'used': float(balance.get('BTC', {}).get('used', 0)), 
                'total': float(balance.get('BTC', {}).get('total', 0))
            }
            
            self.logger.info(f"Balance updated: {self.balance}")
            return self.balance
            
        except Exception as e:
            self.logger.error(f"Balance update error: {e}")
            raise

    def fetch_orderbook(self, limit=10):
        try:
            now = datetime.now()
            if (self.last_orderbook_update and 
                now - self.last_orderbook_update < timedelta(seconds=1)):
                return self.orderbook

            orderbook = self.exchange.fetch_order_book(self.symbol, limit=limit)
            
            self.orderbook = {
                'bids': orderbook['bids'],
                'asks': orderbook['asks'],
                'timestamp': now,
                'datetime': now.isoformat()
            }
            
            self.last_orderbook_update = now
            return self.orderbook
            
        except Exception as e:
            self.logger.error(f"OrderBook fetch error: {e}")
            return None

    def calculate_slippage(self, side, amount, expected_price):
        try:
            orderbook = self.fetch_orderbook()
            if not orderbook:
                return None

            executed_price = expected_price
            remaining = amount

            if side == 'buy':
                for ask_price, ask_volume in orderbook['asks']:
                    if remaining <= 0:
                        break
                    if ask_volume >= remaining:
                        executed_price = ask_price
                        break
                    remaining -= ask_volume
            else:
                for bid_price, bid_volume in orderbook['bids']:
                    if remaining <= 0:
                        break
                    if bid_volume >= remaining:
                        executed_price = bid_price
                        break
                    remaining -= bid_volume

            slippage = abs(executed_price - expected_price) / expected_price * 100
            return slippage
            
        except Exception as e:
            self.logger.error(f"Slippage calculation error: {e}")
            return None

    def place_order(self, side, amount, price=None, order_type='market'):
        try:
            if amount <= 0:
                raise ValueError("Amount must be positive")

            params = {'ordType': order_type}
            
            if order_type == 'limit':
                if price is None or np.isnan(price):
                    raise ValueError("Price must be specified for limit orders")
                params['price'] = float(price)

            if order_type == 'market':
                orderbook = self.fetch_orderbook()
                expected_price = orderbook['asks'][0][0] if side == 'buy' else orderbook['bids'][0][0]
                slippage = self.calculate_slippage(side, amount, expected_price)
                if slippage and slippage > 0.1:
                    self.logger.warning(f"High slippage detected: {slippage}%")

            self.logger.info(f"Placing {order_type} order: Side={side}, Amount={amount}, Price={price}")
            
            order = self.exchange.create_order(
                symbol=self.symbol,
                type=order_type,
                side=side,
                amount=float(amount),
                params=params
            )
            
            self.last_order_time = datetime.now()
            self.save_order_to_db(order)
            
            if order_type == 'market':
                self.save_trade_to_db(order, slippage)
                
            return order
            
        except Exception as e:
            self.logger.error(f"Order placement error: {e}")
            return None

    def place_stop_market(self, side, amount, stop_price, close_on_trigger=False):
        try:
            if stop_price is None or np.isnan(stop_price):
                raise ValueError("Invalid stop price")

            if amount <= 0:
                raise ValueError("Amount must be positive")

            params = {
                'stopPx': float(stop_price),
                'execInst': 'Close' if close_on_trigger else 'LastPrice',
                'ordType': 'Stop'
            }

            self.logger.info(f"Placing stop market: Side={side}, Amount={amount}, StopPrice={stop_price}")
            
            order = self.exchange.create_order(
                symbol=self.symbol,
                type='stop',
                side=side,
                amount=float(amount),
                params=params
            )
            
            self.last_order_time = datetime.now()
            self.save_order_to_db(order, stop_price=stop_price)
            return order
            
        except Exception as e:
            self.logger.error(f"Stop market order error: {e}")
            return None

    def get_position(self):
        try:
            positions = self.exchange.private_get_position()
            
            for position in positions:
                if position['symbol'] == self.symbol:
                    qty = float(position.get('currentQty', 0))
                    if qty != 0:
                        return {
                            'size': abs(qty),
                            'side': 'buy' if qty > 0 else 'sell',
                            'entry_price': float(position.get('avgEntryPrice', 0)),
                            'leverage': float(position.get('leverage', 0)),
                            'unrealized_pnl': float(position.get('unrealisedPnl', 0)),
                            'liquidation_price': float(position.get('liquidationPrice', 0)),
                            'timestamp': datetime.now()
                        }
                        
            return None
            
        except Exception as e:
            self.logger.error(f"Position fetch error: {e}")
            return None

    def close_position(self):
        try:
            position = self.get_position()
            if position:
                close_side = 'sell' if position['side'] == 'buy' else 'buy'
                order = self.place_order(
                    side=close_side,
                    amount=position['size'],
                    order_type='market'
                )
                if order:
                    self.save_position_to_db(position, order)
                return order
            return None
            
        except Exception as e:
            self.logger.error(f"Position closing error: {e}")
            return None

    def save_order_to_db(self, order, stop_price=None):
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO orders (id, symbol, side, price, amount, stop_price, status, order_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(order['id']),
                self.symbol,
                order['side'],
                float(order.get('price', 0)),
                float(order['amount']),
                float(stop_price) if stop_price else None,
                order['status'],
                order.get('type', 'market')
            ))
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Order save error: {e}")

    def save_position_to_db(self, position, close_order):
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO positions (symbol, side, size, entry_price, exit_price, pnl)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self.symbol,
                position['side'],
                float(position['size']),
                float(position['entry_price']),
                float(close_order.get('price', 0)),
                float(position['unrealized_pnl'])
            ))
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Position save error: {e}")

    def save_trade_to_db(self, trade, slippage=None):
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO trades (timestamp, symbol, side, price, amount, cost, pnl, slippage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade['datetime'],
                trade['symbol'],
                trade['side'],
                float(trade['price']),
                float(trade['amount']),
                float(trade.get('cost', 0)),
                float(trade.get('pnl', 0)),
                float(slippage) if slippage else None
            ))
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Trade save error: {e}")
