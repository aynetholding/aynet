import pandas as pd
import numpy as np
import talib
import logging
from datetime import datetime, timedelta

class StrategyManager:
    def __init__(self):
        self.strategies = {}
        self.logger = logging.getLogger(__name__)
        
    def add_strategy(self, strategy):
        """Yeni strateji ekle"""
        try:
            self.strategies[strategy.name] = strategy
            self.logger.info(f"Strategy added: {strategy.name}")
        except Exception as e:
            self.logger.error(f"Strategy add error: {e}")
            raise
    
    def get_signals(self, strategy_name, market_data):
        """Belirtilen strateji için sinyal hesapla"""
        try:
            if strategy_name in self.strategies:
                return self.strategies[strategy_name].calculate_signals(market_data)
            return None
        except Exception as e:
            self.logger.error(f"Signal calculation error: {e}")
            return None

    def get_all_signals(self, market_data):
        """Tüm stratejiler için sinyal hesapla"""
        try:
            signals = {}
            for name, strategy in self.strategies.items():
                signals[name] = strategy.calculate_signals(market_data)
            return signals
        except Exception as e:
            self.logger.error(f"All signals calculation error: {e}")
            return None

class SuperTrendStrategy:
    def __init__(self, period=10, multiplier=3.0):
        self.name = "SuperTrend"
        self.period = period
        self.multiplier = multiplier
        self.signals = pd.DataFrame()
        self.logger = logging.getLogger(__name__)
        
        # Signal geçmişi
        self.signal_history = []
        self.last_signal = None
        self.signal_expiry = None
        
        # Performans metrikleri
        self.metrics = {
            'true_signals': 0,
            'false_signals': 0,
            'missed_signals': 0,
            'total_pnl': 0,
            'win_rate': 0
        }
        
    def calculate_signals(self, market_data):
        """
        SuperTrend sinyallerini hesapla
        
        Args:
            market_data: OHLCV verileri içeren dictionary veya DataFrame
            
        Returns:
            pd.DataFrame: Hesaplanmış sinyaller
        """
        try:
            # Market verilerini DataFrame'e çevir
            df = pd.DataFrame(market_data) if isinstance(market_data, list) else market_data
            
            # OHLCV verilerini hazırla
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df = df.resample('1min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()

            # ATR hesapla
            df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=self.period)
            
            # Basic Bands
            df['basic_upperband'] = ((df['high'] + df['low']) / 2) + (self.multiplier * df['atr'])
            df['basic_lowerband'] = ((df['high'] + df['low']) / 2) - (self.multiplier * df['atr'])
            
            # SuperTrend
            df['trend'] = 1
            df['upperband'] = df['basic_upperband']
            df['lowerband'] = df['basic_lowerband']
            
            for i in range(1, len(df)):
                if df['close'].iloc[i] > df['upperband'].iloc[i-1]:
                    df.loc[df.index[i], 'trend'] = 1
                elif df['close'].iloc[i] < df['lowerband'].iloc[i-1]:
                    df.loc[df.index[i], 'trend'] = -1
                else:
                    df.loc[df.index[i], 'trend'] = df['trend'].iloc[i-1]
                    
                    if df['trend'].iloc[i] == 1 and df['basic_lowerband'].iloc[i] < df['lowerband'].iloc[i-1]:
                        df.loc[df.index[i], 'lowerband'] = df['lowerband'].iloc[i-1]
                    if df['trend'].iloc[i] == -1 and df['basic_upperband'].iloc[i] > df['upperband'].iloc[i-1]:
                        df.loc[df.index[i], 'upperband'] = df['upperband'].iloc[i-1]
            
            # Temel sinyaller
            df['in_uptrend'] = df['trend'] == 1
            df['trend_changed'] = df['trend'] != df['trend'].shift(1)
            
            # Ek indikatörler
            df['rsi'] = talib.RSI(df['close'], timeperiod=14)
            df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(df['close'])
            
            # Volatilite
            df['daily_volatility'] = df['close'].pct_change().rolling(window=24).std() * 100
            
            # Sinyal gücü hesaplama
            df['price_distance'] = (df['close'] - df['lowerband']).abs() / df['atr']
            df['trend_strength'] = df['price_distance'].rolling(window=5).mean()
            df['volume_factor'] = df['volume'] / df['volume'].rolling(window=20).mean()
            
            # Farklı faktörleri birleştirerek sinyal gücünü hesapla
            df['signal_strength'] = (
                (df['trend_strength'] * 0.4) +  # Trend gücü
                (df['volume_factor'] * 0.3) +   # Hacim faktörü
                (df['rsi'].clip(0, 100) / 100 * 0.3)  # RSI normalize edilmiş
            ) * 100

            # Ek filtreler
            df['strong_trend'] = df['signal_strength'] > 70
            df['valid_volume'] = df['volume_factor'] > 1.2
            df['confirmed_signal'] = (
                (df['trend_changed']) & 
                (df['strong_trend']) & 
                (df['valid_volume'])
            )
            
            # Son sinyali kaydet
            last_signal = df.iloc[-1].copy()
            last_signal['timestamp'] = df.index[-1]
            self.signal_history.append(last_signal)
            
            # Sinyal geçmişini sınırla
            if len(self.signal_history) > 1000:
                self.signal_history.pop(0)
            
            # Son sinyali güncelle
            self.last_signal = last_signal
            self.signal_expiry = datetime.now() + timedelta(minutes=5)
            
            self.signals = df
            return df
            
        except Exception as e:
            self.logger.error(f"SuperTrend signal calculation error: {e}")
            return None

    def get_signal_summary(self):
        """Son sinyalin özetini al"""
        if len(self.signal_history) == 0:
            return None
            
        latest = self.signal_history[-1]
        return {
            'timestamp': latest['timestamp'],
            'trend': 'UP' if latest['in_uptrend'] else 'DOWN',
            'strength': latest['signal_strength'],
            'rsi': latest['rsi'],
            'volatility': latest['daily_volatility'],
            'volume_factor': latest['volume_factor']
        }

    def evaluate_signal(self, entry_price, exit_price, signal_type):
        """Sinyal performansını değerlendir"""
        try:
            pnl = exit_price - entry_price if signal_type == 'buy' else entry_price - exit_price
            success = pnl > 0
            
            if success:
                self.metrics['true_signals'] += 1
            else:
                self.metrics['false_signals'] += 1
                
            self.metrics['total_pnl'] += pnl
            total_signals = self.metrics['true_signals'] + self.metrics['false_signals']
            self.metrics['win_rate'] = (self.metrics['true_signals'] / total_signals * 100) if total_signals > 0 else 0
            
            return success, pnl
            
        except Exception as e:
            self.logger.error(f"Signal evaluation error: {e}")
            return False, 0

    def get_performance_metrics(self):
        """Strateji performans metriklerini getir"""
        return {
            'true_signals': self.metrics['true_signals'],
            'false_signals': self.metrics['false_signals'],
            'missed_signals': self.metrics['missed_signals'],
            'total_pnl': self.metrics['total_pnl'],
            'win_rate': self.metrics['win_rate']
        }

    def reset(self):
        """Strateji verilerini sıfırla"""
        self.signals = pd.DataFrame()
        self.signal_history = []
        self.last_signal = None
        self.signal_expiry = None
        self.metrics = {
            'true_signals': 0,
            'false_signals': 0,
            'missed_signals': 0,
            'total_pnl': 0,
            'win_rate': 0
        }
        self.logger.info("Strategy reset")
