
# modules/advanced_order_manager.py

from datetime import datetime
import logging
import numpy as np

class AdvancedOrderManager:
    def __init__(self, exchange, config):
        self.exchange = exchange
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.active_orders = {
            'entry_long': None,
            'entry_short': None,
            'stop_loss': None
        }
        
        self.position = None
        self.slippage_data = []
        self.entry_delay = None
        self.last_signal = None

    def calculate_entry_level(self, signal_price, direction):
        """OrderBook derinliğine göre giriş seviyesi hesapla"""
        orderbook = self.exchange.fetch_order_book('XBTUSDT')
        if not orderbook:
            return signal_price
            
        if direction == 'long':
            # En iyi 5 ask seviyesini kontrol et
            asks = orderbook['asks'][:5]
            weighted_price = np.average([price for price, _ in asks], 
                                      weights=[vol for _, vol in asks])
            return min(weighted_price, signal_price)
        else:
            # En iyi 5 bid seviyesini kontrol et
            bids = orderbook['bids'][:5]
            weighted_price = np.average([price for price, _ in bids],
                                      weights=[vol for _, vol in bids])
            return max(weighted_price, signal_price)

    def place_orders(self, signal_type, signal_price):
        """Emir yerleştirme"""
        try:
            # Mevcut emirleri temizle
            self.cancel_all_orders()
            
            # Pozisyon büyüklüğü hesapla
            balance = self.exchange.fetch_balance()
            free_balance = balance['free']['USDT']
            position_size = (free_balance * self.config['position_size_percent']) / 100
            
            # En iyi giriş seviyesini hesapla
            entry_price = self.calculate_entry_level(signal_price, signal_type)
            
            # Stop Loss hesapla
            if signal_type == 'long':
                stop_price = entry_price * (1 - self.config['stop_loss_percent'] / 100)
            else:
                stop_price = entry_price * (1 + self.config['stop_loss_percent'] / 100)

            # Ana emir
            main_order = self.exchange.create_order(
                symbol='XBTUSDT',
                type='stop_market',
                side='buy' if signal_type == 'long' else 'sell',
                amount=position_size,
                params={
                    'stopPx': entry_price,
                    'execInst': 'Last',
                    'closeOnTrigger': False
                }
            )
            
            # Stop Loss emri
            sl_order = self.exchange.create_order(
                symbol='XBTUSDT',
                type='stop',
                side='sell' if signal_type == 'long' else 'buy',
                amount=position_size,
                params={
                    'stopPx': stop_price,
                    'execInst': 'Last',
                    'closeOnTrigger': True
                }
            )
            
            # Emirleri kaydet
            self.active_orders[f'entry_{signal_type}'] = {
                'order': main_order,
                'intended_price': entry_price
            }
            
            self.active_orders['stop_loss'] = {
                'order': sl_order,
                'intended_price': stop_price
            }
            
            self.logger.info(f"Orders placed - Type: {signal_type}, Entry: {entry_price}, Stop: {stop_price}")
            return True
            
        except Exception as e:
            self.logger.error(f"Order placement error: {e}")
            return False

    def modify_stop_loss(self, new_stop_price):
        """Stop Loss güncelle"""
        try:
            if not self.active_orders['stop_loss']:
                return False

            position = self.get_position()
            if not position:
                return False

            # Yeni stop loss emri
            new_sl_order = self.exchange.create_order(
                symbol='XBTUSDT',
                type='stop',
                side='sell' if position['side'] == 'buy' else 'buy',
                amount=abs(position['size']),
                params={
                    'stopPx': new_stop_price,
                    'execInst': 'Last',
                    'closeOnTrigger': True
                }
            )
            
            # Eski emri iptal et
            self.cancel_order(self.active_orders['stop_loss']['order']['id'])
            
            # Yeni emri kaydet
            self.active_orders['stop_loss'] = {
                'order': new_sl_order,
                'intended_price': new_stop_price
            }
            
            return True
            
        except Exception as e:
            self.logger.error(f"Stop loss modification error: {e}")
            return False

    def calculate_slippage(self, order_id, execution_price):
        """Kayma hesapla"""
        try:
            for key, order_info in self.active_orders.items():
                if order_info and order_info['order']['id'] == order_id:
                    intended_price = order_info['intended_price']
                    slippage = abs(execution_price - intended_price)
                    slippage_percent = (slippage / intended_price) * 100
                    
                    self.slippage_data.append({
                        'timestamp': datetime.now(),
                        'order_type': key,
                        'intended_price': intended_price,
                        'execution_price': execution_price,
                        'slippage': slippage,
                        'slippage_percent': slippage_percent
                    })
                    
                    return slippage_percent
                    
            return 0
            
        except Exception as e:
            self.logger.error(f"Slippage calculation error: {e}")
            return 0

    def get_position(self):
        """Pozisyon bilgisi al"""
        try:
            positions = self.exchange.fetch_positions(['XBTUSDT'])
            for position in positions:
                if position['symbol'] == 'XBTUSDT':
                    return {
                        'size': position['contracts'],
                        'side': position['side'],
                        'entry_price': position['entryPrice'],
                        'liquidation_price': position['liquidationPrice'],
                        'unrealized_pnl': position['unrealizedPnl']
                    }
            return None
            
        except Exception as e:
            self.logger.error(f"Position fetch error: {e}")
            return None

    def cancel_all_orders(self):
        """Tüm emirleri iptal et"""
        try:
            self.exchange.cancel_all_orders('XBTUSDT')
            self.active_orders = {
                'entry_long': None,
                'entry_short': None,
                'stop_loss': None
            }
            return True
        except Exception as e:
            self.logger.error(f"Order cancellation error: {e}")
            return False

    def cancel_order(self, order_id):
        """Tek emir iptal et"""
        try:
            self.exchange.cancel_order(order_id, 'XBTUSDT')
            for key in self.active_orders:
                if self.active_orders[key] and self.active_orders[key]['order']['id'] == order_id:
                    self.active_orders[key] = None
            return True
        except Exception as e:
            self.logger.error(f"Order cancellation error: {e}")
            return False

