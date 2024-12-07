
# modules/order_manager.py

import ccxt
import logging
from datetime import datetime

class OrderManager:
    def __init__(self, api_key, api_secret, testnet=True):
        self.exchange = ccxt.bitmex({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'test': testnet
        })
        
        self.symbol = "XBTUSDT"
        self.default_stop_percent = 1.5
        self.stop_percent = self.default_stop_percent
        self.active_orders = {}
        self.logger = self.setup_logger()
        self.connection_status = True
        
        # Balance tracking
        self.initial_balance = None
        self.current_balance = None
        self.update_balance()

    def setup_logger(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def update_balance(self):
        """Bakiye güncelleme"""
        try:
            balance = self.exchange.fetch_balance()
            self.current_balance = balance['USDT']['free']
            
            if self.initial_balance is None:
                self.initial_balance = self.current_balance
                
            return {
                'initial': self.initial_balance,
                'current': self.current_balance,
                'pnl': self.current_balance - self.initial_balance
            }
        except Exception as e:
            self.logger.error(f"Bakiye güncelleme hatası: {e}")
            self.check_connection()
            return None

    def place_entry_order(self, side, price, amount):
        """Giriş emri yerleştirme - Stop Market"""
        try:
            order = self.exchange.create_order(
                symbol=self.symbol,
                type='stop_market',
                side=side,
                amount=amount,
                params={
                    'stopPx': price,
                    'execInst': 'Last',  # Last price trigger
                    'closeOnTrigger': False  # Position açmak için
                }
            )
            
            self.active_orders[order['id']] = {
                'type': 'entry',
                'order': order,
                'stop_price': price
            }
            
            self.logger.info(f"Giriş emri yerleştirildi: {order}")
            return order
        except Exception as e:
            self.logger.error(f"Giriş emri hatası: {e}")
            self.check_connection()
            return None

    def place_stop_loss(self, side, price, amount):
        """Stop Loss emri yerleştirme"""
        try:
            opposite_side = 'sell' if side == 'buy' else 'buy'
            order = self.exchange.create_order(
                symbol=self.symbol,
                type='stop_market',
                side=opposite_side,
                amount=amount,
                params={
                    'stopPx': price,
                    'execInst': 'Last',
                    'closeOnTrigger': True  # Position kapatmak için
                }
            )
            
            self.active_orders[order['id']] = {
                'type': 'stop_loss',
                'order': order,
                'stop_price': price
            }
            
            self.logger.info(f"Stop Loss emri yerleştirildi: {order}")
            return order
        except Exception as e:
            self.logger.error(f"Stop Loss emri hatası: {e}")
            self.check_connection()
            return None

    def update_stop_loss_percent(self, new_percent):
        """Stop Loss yüzdesini güncelle"""
        self.stop_percent = new_percent
        
        # Aktif pozisyon varsa stop loss'u güncelle
        position = self.get_position()
        if position and position['size'] != 0:
            self.update_stop_loss_orders()
        
        self.logger.info(f"Stop Loss yüzdesi güncellendi: {new_percent}%")

    def update_stop_loss_orders(self):
        """Mevcut Stop Loss emirlerini güncelle"""
        position = self.get_position()
        if not position or position['size'] == 0:
            return
        
        entry_price = position['entry_price']
        size = abs(position['size'])
        side = 'buy' if position['side'] == 'short' else 'sell'
        
        # Yeni stop loss fiyatını hesapla
        if side == 'sell':
            stop_price = entry_price * (1 - self.stop_percent/100)
        else:
            stop_price = entry_price * (1 + self.stop_percent/100)
        
        # Mevcut stop loss emirlerini iptal et
        for order_id, order_info in list(self.active_orders.items()):
            if order_info['type'] == 'stop_loss':
                self.cancel_order(order_id)
        
        # Yeni stop loss emri yerleştir
        self.place_stop_loss(side, stop_price, size)

    def update_entry_orders(self, new_price):
        """Giriş emirlerini güncelle"""
        try:
            for order_id, order_info in list(self.active_orders.items()):
                if order_info['type'] == 'entry':
                    # Mevcut emri iptal et
                    self.cancel_order(order_id)
                    
                    # Yeni fiyatla yeni emir yerleştir
                    original_order = order_info['order']
                    self.place_entry_order(
                        original_order['side'],
                        new_price,
                        original_order['amount']
                    )
        except Exception as e:
            self.logger.error(f"Emir güncelleme hatası: {e}")
            self.check_connection()

    def cancel_order(self, order_id):
        """Emir iptali"""
        try:
            self.exchange.cancel_order(order_id, self.symbol)
            if order_id in self.active_orders:
                del self.active_orders[order_id]
            return True
        except Exception as e:
            self.logger.error(f"Emir iptal hatası: {e}")
            self.check_connection()
            return False

    def get_position(self):
        """Mevcut pozisyon bilgisi"""
        try:
            positions = self.exchange.fetch_positions([self.symbol])
            for position in positions:
                if position['symbol'] == self.symbol:
                    return {
                        'size': position['contracts'],
                        'side': 'long' if position['side'] == 'buy' else 'short',
                        'entry_price': position['entryPrice'],
                        'liquidation_price': position['liquidationPrice'],
                        'unrealized_pnl': position['unrealizedPnl']
                    }
            return None
        except Exception as e:
            self.logger.error(f"Pozisyon bilgisi hatası: {e}")
            self.check_connection()
            return None

    def check_connection(self):
        """Bağlantı kontrolü"""
        try:
            self.exchange.fetch_ticker(self.symbol)
            if not self.connection_status:
                self.connection_status = True
                self.logger.info("Bağlantı yeniden sağlandı")
            return True
        except Exception as e:
            if self.connection_status:
                self.connection_status = False
                self.logger.error("Bağlantı kesildi!")
            return False

