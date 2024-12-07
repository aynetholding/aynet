
# bitmex_integration.py
import ccxt
import pandas as pd
from datetime import datetime
import time

class BitmexTrader:
    def __init__(self, api_key, api_secret, testnet=False):
        self.exchange = ccxt.bitmex({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'test': testnet  # Testnet için True
        })
        
        # Parametre ayarları
        self.position_config = {
            'take_profit_usd': 10000,  # USD cinsinden kar al
            'stop_loss_usd': 10000,    # USD cinsinden zarar kes
            'leverage': 1,             # Kaldıraç
            'position_size': 100       # Kontrat sayısı
        }
        
        self.active_orders = {}
        self.current_position = None

    def calculate_position_size(self, price):
        """USD cinsinden pozisyon büyüklüğü hesaplama"""
        contract_value = 1  # 1 USD for XBTUSD
        return self.position_config['position_size'] * contract_value

    def place_orders(self, signal_type, entry_price):
        """Sinyal tipine göre order yerleştirme"""
        try:
            # Mevcut pozisyonları ve orderleri temizle
            self.cancel_all_orders()
            
            position_size = self.calculate_position_size(entry_price)
            
            if signal_type == 'buy':
                # Long pozisyon
                main_order = self.exchange.create_order(
                    symbol='BTC/USD',
                    type='market',
                    side='buy',
                    amount=position_size
                )
                
                # Take Profit order
                tp_price = entry_price + (self.position_config['take_profit_usd'] / position_size)
                tp_order = self.exchange.create_order(
                    symbol='BTC/USD',
                    type='limit',
                    side='sell',
                    amount=position_size,
                    price=tp_price,
                    params={'stopPx': tp_price}
                )
                
                # Stop Loss order
                sl_price = entry_price - (self.position_config['stop_loss_usd'] / position_size)
                sl_order = self.exchange.create_order(
                    symbol='BTC/USD',
                    type='stop',
                    side='sell',
                    amount=position_size,
                    price=sl_price,
                    params={'stopPx': sl_price}
                )
                
            elif signal_type == 'sell':
                # Short pozisyon
                main_order = self.exchange.create_order(
                    symbol='BTC/USD',
                    type='market',
                    side='sell',
                    amount=position_size
                )
                
                # Take Profit order
                tp_price = entry_price - (self.position_config['take_profit_usd'] / position_size)
                tp_order = self.exchange.create_order(
                    symbol='BTC/USD',
                    type='limit',
                    side='buy',
                    amount=position_size,
                    price=tp_price,
                    params={'stopPx': tp_price}
                )
                
                # Stop Loss order
                sl_price = entry_price + (self.position_config['stop_loss_usd'] / position_size)
                sl_order = self.exchange.create_order(
                    symbol='BTC/USD',
                    type='stop',
                    side='buy',
                    amount=position_size,
                    price=sl_price,
                    params={'stopPx': sl_price}
                )
            
            # Order bilgilerini sakla
            self.active_orders = {
                'main': main_order,
                'tp': tp_order,
                'sl': sl_order,
                'entry_price': entry_price,
                'position_size': position_size,
                'type': signal_type
            }
            
            return True, "Orders placed successfully"
            
        except Exception as e:
            return False, f"Error placing orders: {str(e)}"

    def update_position_params(self, tp_usd=None, sl_usd=None, leverage=None, size=None):
        """Pozisyon parametrelerini güncelle"""
        if tp_usd is not None:
            self.position_config['take_profit_usd'] = tp_usd
        if sl_usd is not None:
            self.position_config['stop_loss_usd'] = sl_usd
        if leverage is not None:
            self.position_config['leverage'] = leverage
            self.update_leverage(leverage)
        if size is not None:
            self.position_config['position_size'] = size

    def update_leverage(self, leverage):
        """Kaldıraç güncelleme"""
        try:
            self.exchange.private_post_position_leverage({
                'symbol': 'XBTUSD',
                'leverage': leverage
            })
            return True, "Leverage updated successfully"
        except Exception as e:
            return False, f"Error updating leverage: {str(e)}"

    def cancel_all_orders(self):
        """Tüm aktif orderleri iptal et"""
        try:
            self.exchange.cancel_all_orders('BTC/USD')
            self.active_orders = {}
            return True, "All orders cancelled"
        except Exception as e:
            return False, f"Error cancelling orders: {str(e)}"

    def get_current_position(self):
        """Mevcut pozisyon bilgisini al"""
        try:
            positions = self.exchange.fetch_positions()
            for position in positions:
                if position['symbol'] == 'BTC/USD':
                    self.current_position = position
                    return position
            return None
        except Exception as e:
            return None

    def calculate_pnl(self):
        """Kar/Zarar hesaplama"""
        position = self.get_current_position()
        if position and position['contracts']:
            return {
                'unrealized_pnl': position['unrealizedPnl'],
                'realized_pnl': position['realizedPnl'],
                'entry_price': position['entryPrice'],
                'current_price': position['markPrice'],
                'size': position['contracts']
            }
        return None

    def modify_take_profit(self, new_tp_usd):
        """Take Profit değerini güncelle"""
        if not self.active_orders or 'tp' not in self.active_orders:
            return False, "No active TP order"
            
        try:
            # Mevcut TP orderı iptal et
            self.exchange.cancel_order(self.active_orders['tp']['id'])
            
            # Yeni TP orderı yerleştir
            position = self.get_current_position()
            if position:
                side = 'sell' if position['side'] == 'buy' else 'buy'
                new_tp_price = position['entryPrice'] + (new_tp_usd / position['contracts'])
                if side == 'sell':
                    new_tp_price = position['entryPrice'] - (new_tp_usd / position['contracts'])
                
                new_tp_order = self.exchange.create_order(
                    symbol='BTC/USD',
                    type='limit',
                    side=side,
                    amount=abs(position['contracts']),
                    price=new_tp_price,
                    params={'stopPx': new_tp_price}
                )
                
                self.active_orders['tp'] = new_tp_order
                return True, "TP updated successfully"
                
        except Exception as e:
            return False, f"Error updating TP: {str(e)}"

    def modify_stop_loss(self, new_sl_usd):
        """Stop Loss değerini güncelle"""
        if not self.active_orders or 'sl' not in self.active_orders:
            return False, "No active SL order"
            
        try:
            # Mevcut SL orderı iptal et
            self.exchange.cancel_order(self.active_orders['sl']['id'])
            
            # Yeni SL orderı yerleştir
            position = self.get_current_position()
            if position:
                side = 'sell' if position['side'] == 'buy' else 'buy'
                new_sl_price = position['entryPrice'] - (new_sl_usd / position['contracts'])
                if side == 'buy':
                    new_sl_price = position['entryPrice'] + (new_sl_usd / position['contracts'])
                
                new_sl_order = self.exchange.create_order(
                    symbol='BTC/USD',
                    type='stop',
                    side=side,
                    amount=abs(position['contracts']),
                    price=new_sl_price,
                    params={'stopPx': new_sl_price}
                )
                
                self.active_orders['sl'] = new_sl_order
                return True, "SL updated successfully"
                
        except Exception as e:
            return False, f"Error updating SL: {str(e)}"
