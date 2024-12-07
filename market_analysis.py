# modules/market_analysis.py

from datetime import datetime
import pandas as pd
import numpy as np
import talib
import logging

class MarketAnalyzer:
   def __init__(self, exchange, order_book_manager, config):
       self.exchange = exchange
       self.ob_manager = order_book_manager 
       self.config = config
       self.logger = logging.getLogger(__name__)
       
       self.price_data = pd.DataFrame()
       self.renko_data = pd.DataFrame()
       self.current_signals = {
           'supertrend': None,
           'direction': None,
           'strength': 0
       }

   def update_data(self):
       """Fiyat verilerini güncelle"""
       try:
           ohlcv = self.exchange.fetch_ohlcv(
               symbol='XBTUSDT',
               timeframe='1m', 
               limit=100
           )
           
           df = pd.DataFrame(
               ohlcv,
               columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
           )
           df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
           df.set_index('timestamp', inplace=True)
           
           self.price_data = df
           self.calculate_indicators()
           return True
           
       except Exception as e:
           self.logger.error(f"Data update error: {e}")
           return False

   def create_renko(self):
       """Renko mumları oluştur"""
       if self.price_data.empty:
           return
           
       brick_size = self.config['renko_brick_size']
       renko_prices = []
       current_brick = self.price_data['close'].iloc[0]
       
       for idx, row in self.price_data.iterrows():
           price = row['close']
           
           # Yukarı hareket
           while price >= current_brick + brick_size:
               current_brick += brick_size
               renko_prices.append({
                   'timestamp': idx,
                   'open': current_brick - brick_size,
                   'high': current_brick,
                   'low': current_brick - brick_size,
                   'close': current_brick,
                   'direction': 1
               })
               
           # Aşağı hareket
           while price <= current_brick - brick_size:
               current_brick -= brick_size
               renko_prices.append({
                   'timestamp': idx,
                   'open': current_brick + brick_size,
                   'high': current_brick + brick_size,
                   'low': current_brick,
                   'close': current_brick,
                   'direction': -1  
               })
               
       self.renko_data = pd.DataFrame(renko_prices)

   def calculate_indicators(self):
       """İndikatörleri hesapla"""
       df = self.price_data
       
       # ATR hesapla
       df['atr'] = talib.ATR(
           df['high'].values,
           df['low'].values,
           df['close'].values,
           timeperiod=self.config['atr_period']
       )
       
       # SuperTrend bantlarını hesapla
       df['upperband'] = ((df['high'] + df['low']) / 2) + (
           self.config['atr_multiplier'] * df['atr']
       )
       df['lowerband'] = ((df['high'] + df['low']) / 2) - (
           self.config['atr_multiplier'] * df['atr']
       )
       
       # Trend yönünü hesapla
       df['in_uptrend'] = True
       
       for i in range(1, len(df)):
           curr_close = df['close'].iloc[i]
           curr_upper = df['upperband'].iloc[i]
           curr_lower = df['lowerband'].iloc[i]
           prev_close = df['close'].iloc[i-1]
           prev_upper = df['upperband'].iloc[i-1]
           prev_lower = df['lowerband'].iloc[i-1]
           prev_trend = df['in_uptrend'].iloc[i-1]
           
           if prev_trend:
               if curr_close < curr_lower:
                   df.loc[df.index[i], 'in_uptrend'] = False
               else:
                   df.loc[df.index[i], 'in_uptrend'] = True
           else:
               if curr_close > curr_upper:
                   df.loc[df.index[i], 'in_uptrend'] = True
               else:
                   df.loc[df.index[i], 'in_uptrend'] = False
                   
       # Sinyal gücü hesapla
       df['signal_strength'] = self.calculate_signal_strength(df)
       
       # Son durumu kaydet
       last_row = df.iloc[-1]
       self.current_signals = {
           'supertrend': last_row['in_uptrend'],
           'direction': 'long' if last_row['in_uptrend'] else 'short',
           'strength': last_row['signal_strength']
       }

   def calculate_signal_strength(self, df):
       """Sinyal gücü hesapla"""
       strength = pd.Series(index=df.index, data=0)
       
       # Trend süresi (0-40 puan)
       trend_duration = df['in_uptrend'].groupby(
           (df['in_uptrend'] != df['in_uptrend'].shift()).cumsum()
       ).cumcount()
       strength += np.minimum(trend_duration * 2, 40)
       
       # Hacim desteği (0-30 puan)
       volume_ma = df['volume'].rolling(20).mean()
       strength += np.where(
           df['volume'] > volume_ma,
           30,
           (df['volume'] / volume_ma) * 30
       )
       
       # Fiyat momentum (0-30 puan)
       roc = talib.ROC(df['close'], timeperiod=10)
       strength += np.where(
           (df['in_uptrend'] & (roc > 0)) | (~df['in_uptrend'] & (roc < 0)),
           30,
           0
       )
       
       return strength

   def should_entry(self):
       """Giriş sinyali kontrol"""
       return (
           self.current_signals['strength'] >= 80 and
           abs(self.ob_manager.get_imbalance()) >= 0.2
       )

   def should_exit(self):
       """Çıkış sinyali kontrol"""
       return (
           self.current_signals['strength'] <= 20 or
           abs(self.ob_manager.get_imbalance()) <= -0.2
       )

   def get_market_state(self):
       """Piyasa durumu bilgisi"""
       return {
           'timestamp': datetime.now(),
           'signals': self.current_signals,
           'orderbook': self.ob_manager.get_current_state(),
           'price_data': {
               'last_price': self.price_data['close'].iloc[-1],
               'price_change': self.price_data['close'].pct_change().iloc[-1],
               'volume': self.price_data['volume'].iloc[-1]
           }
       }
