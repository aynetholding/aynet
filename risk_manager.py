import logging
from datetime import datetime, time
import pandas as pd

class RiskManager:
    def __init__(self, trader, config):
        """
        Risk yönetimi için ana sınıf
        
        Args:
            trader: BitmexTrader instance
            config: TradingConfig instance
        """
        self.trader = trader
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # İstatistikler
        self.daily_trades = 0
        self.daily_loss = 0
        self.initial_balance = self._get_initial_balance()
        self.max_drawdown = 0
        self.daily_stats = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'pnl': 0.0
        }
        
        self._reset_daily_stats()

    def _get_initial_balance(self):
        """Başlangıç bakiyesini al"""
        try:
            if hasattr(self.config, 'INITIAL_BALANCE') and self.config.INITIAL_BALANCE:
                return self.config.INITIAL_BALANCE
            else:
                balance = self.trader.exchange.fetch_balance()
                return float(balance.get('BTC', {}).get('total', 0))
        except Exception as e:
            self.logger.error(f"Initial balance fetch error: {e}")
            return 0

    def _reset_daily_stats(self):
        """Günlük istatistikleri sıfırla"""
        self.daily_trades = 0
        self.daily_loss = 0
        self.daily_stats = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'pnl': 0.0
        }

    def can_trade(self):
        """Trading kurallarını kontrol et"""
        try:
            # Trading saatlerini kontrol et
            if not self._check_trading_hours():
                self.logger.info("Trading saatleri dışında")
                return False

            # Günlük işlem limitini kontrol et
            if self.daily_trades >= self.config.MAX_TRADES_PER_DAY:
                self.logger.info("Günlük işlem limiti aşıldı")
                return False

            # Günlük kayıp limitini kontrol et
            if abs(self.daily_loss) > self._get_max_daily_loss():
                self.logger.info("Günlük kayıp limiti aşıldı")
                return False

            # Drawdown kontrolü
            if self._check_drawdown():
                self.logger.info("Maximum drawdown aşıldı")
                return False

            # Balance kontrolü
            if not self._check_minimum_balance():
                self.logger.info("Yetersiz bakiye")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Can trade check error: {e}")
            return False

    def _check_minimum_balance(self):
        """Minimum işlem bakiyesini kontrol et"""
        try:
            balance = self.trader.exchange.fetch_balance()
            free_balance = float(balance['BTC']['free'])
            return free_balance > 0.0001  # Minimum 0.0001 BTC gerekli
        except Exception as e:
            self.logger.error(f"Balance check error: {e}")
            return False

    def calculate_position_size(self, side, entry_price):
        """Pozisyon büyüklüğünü hesapla"""
        try:
            balance = self.trader.exchange.fetch_balance()
            free_balance = float(balance['BTC']['free'])

            # Risk bazlı pozisyon büyüklüğü
            risk_amount = free_balance * (self.config.POSITION_SIZE_PERCENT / 100)
            
            # Stop loss mesafesini hesapla
            stop_price = self.calculate_stop_loss(side, entry_price)
            if stop_price is None:
                return 0
                
            risk_per_coin = abs(entry_price - stop_price)
            
            # Sıfıra bölme kontrolü
            if risk_per_coin == 0:
                self.logger.error("Risk per coin cannot be zero")
                return 0
                
            position_size = risk_amount / risk_per_coin
            
            # Kaldıraç kullan
            if self.config.USE_LEVERAGE:
                current_leverage = min(
                    self.config.MAX_LEVERAGE, 
                    self.trader.exchange.fetch_leverage()
                )
                position_size *= current_leverage

            # Minimum ve maksimum kontrolleri
            min_size = 0.001  # 0.001 BTC minimum
            max_size = free_balance * current_leverage * 0.95  # Bakiyenin %95'i

            position_size = max(min_size, min(position_size, max_size))
            return round(position_size, 8)

        except Exception as e:
            self.logger.error(f"Position size calculation error: {e}")
            return 0

    def calculate_stop_loss(self, side, entry_price):
        """Stop loss seviyesini hesapla"""
        try:
            stop_percent = self.config.STOP_LOSS_PERCENT / 100
            
            if side == 'buy':
                stop_price = entry_price * (1 - stop_percent)
            else:
                stop_price = entry_price * (1 + stop_percent)

            # Minimum hareket kontrolü (0.5$ for XBTUSD)
            min_tick = 0.5
            stop_price = round(stop_price / min_tick) * min_tick

            return round(stop_price, 1)

        except Exception as e:
            self.logger.error(f"Stop loss calculation error: {e}")
            return None

    def _check_trading_hours(self):
        """Trading saatlerini kontrol et"""
        try:
            now = datetime.now().time()
            start = datetime.strptime(self.config.TRADING_HOURS['START'], '%H:%M').time()
            end = datetime.strptime(self.config.TRADING_HOURS['END'], '%H:%M').time()
            
            if start <= end:
                return start <= now <= end
            else:  # Gece yarısını kapsayan saat aralığı
                return now >= start or now <= end

        except Exception as e:
            self.logger.error(f"Trading hours check error: {e}")
            return False

    def _get_max_daily_loss(self):
        """Maksimum günlük kayıp limitini hesapla"""
        try:
            current_balance = float(self.trader.exchange.fetch_balance()['BTC']['total'])
            return current_balance * (self.config.MAX_DAILY_LOSS_PERCENT / 100)
        except Exception as e:
            self.logger.error(f"Max daily loss calculation error: {e}")
            return float('inf')  # Hata durumunda limitsiz

    def _check_drawdown(self):
        """Drawdown kontrolü"""
        try:
            if self.initial_balance == 0:
                return False
                
            current_balance = float(self.trader.exchange.fetch_balance()['BTC']['total'])
            drawdown = (self.initial_balance - current_balance) / self.initial_balance * 100
            
            self.max_drawdown = max(self.max_drawdown, drawdown)
            
            return drawdown > self.config.MAX_DRAWDOWN_PERCENT

        except Exception as e:
            self.logger.error(f"Drawdown check error: {e}")
            return True  # Hata durumunda güvenli tarafta kal

    def update_trade_stats(self, pnl):
        """İşlem istatistiklerini güncelle"""
        try:
            self.daily_trades += 1
            self.daily_stats['trades'] += 1
            self.daily_stats['pnl'] += pnl
            
            if pnl >= 0:
                self.daily_stats['wins'] += 1
            else:
                self.daily_stats['losses'] += 1
                self.daily_loss += abs(pnl)

        except Exception as e:
            self.logger.error(f"Stats update error: {e}")

    def get_risk_metrics(self):
        """Risk metriklerini getir"""
        try:
            position = self.trader.get_position()
            balance = self.trader.exchange.fetch_balance()
            
            metrics = {
                'position': {
                    'active': position is not None,
                    'size': position['size'] if position else 0,
                    'side': position['side'] if position else None,
                    'pnl': position['unrealized_pnl'] if position else 0,
                    'leverage': position['leverage'] if position else 0
                },
                'account': {
                    'balance': balance['BTC']['total'],
                    'free': balance['BTC']['free'],
                    'used': balance['BTC']['used'],
                    'max_drawdown': self.max_drawdown
                },
                'daily_stats': {
                    'trades': self.daily_stats['trades'],
                    'wins': self.daily_stats['wins'],
                    'losses': self.daily_stats['losses'],
                    'win_rate': (self.daily_stats['wins'] / self.daily_stats['trades'] * 100) 
                              if self.daily_stats['trades'] > 0 else 0,
                    'pnl': self.daily_stats['pnl']
                }
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Risk metrics calculation error: {e}")
            return None

    def reset(self):
        """Risk yöneticisini sıfırla"""
        self._reset_daily_stats()
        self.initial_balance = self._get_initial_balance()
        self.max_drawdown = 0
