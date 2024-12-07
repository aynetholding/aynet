import os
import sys
import logging
import threading
import time
import asyncio
from datetime import datetime

from config.trading_config import TradingConfig
from config.telegram_config import TELEGRAM_CONFIG
from config.logging_config import setup_logging
from modules.bitmex_trader import BitmexTrader
from modules.telegram_bot import TelegramBot
from modules.visualization import DashboardVisualizer
from modules.websocket_manager import BitmexWebsocket
from modules.monitoring import SystemMonitor
from modules.strategy_manager import StrategyManager, SuperTrendStrategy
from modules.risk_manager import RiskManager

# BitMEX API Konfigürasyonu
BITMEX_CONFIG = {
    'api_key': 'ZhN2is3fxZBurWWAXj5MGNF4',
    'api_secret': 'VA2KIZAv-miprHXRQO2lY5I7GiJQ-g-gCxEeNr6A5YGCmLo3',
    'symbol': 'XBTUSD',
    'testnet': False
}

class TradingBot:
    def __init__(self):
        # Logging setup
        self.loggers = setup_logging(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            getattr(logging, 'INFO')
        )
        self.logger = self.loggers['trading']
        
        self.config = TradingConfig
        self.setup_exchange()
        self.setup_websocket()
        self.initialize_modules()
        
        self.running = False

    def setup_exchange(self):
        """Exchange bağlantısını kur"""
        try:
            self.trader = BitmexTrader(
                api_key=BITMEX_CONFIG['api_key'],
                api_secret=BITMEX_CONFIG['api_secret'],
                testnet=BITMEX_CONFIG['testnet']
            )
            self.logger.info(f"Exchange connected - Live Trading: {not BITMEX_CONFIG['testnet']}")
        except Exception as e:
            self.logger.error(f"Exchange connection error: {e}")
            sys.exit(1)

    def setup_websocket(self):
        """WebSocket bağlantısını kur"""
        try:
            self.ws = BitmexWebsocket(
                api_key=BITMEX_CONFIG['api_key'],
                api_secret=BITMEX_CONFIG['api_secret'],
                testnet=BITMEX_CONFIG['testnet']
            )
            self.ws.connect()
            self.logger.info("WebSocket connected")
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
            sys.exit(1)

    def initialize_modules(self):
        """Modülleri başlat"""
        try:
            # Temel konfigürasyon kontrolü
            self.config.validate_settings()

            # Risk manager başlat
            self.risk_manager = RiskManager(
                self.trader,
                self.config
            )

            # Strateji yöneticisi başlat
            self.strategy_manager = StrategyManager()
            
            # SuperTrend stratejisini ekle
            self.supertrend = SuperTrendStrategy(
                period=self.config.SUPERTREND_LENGTH,
                multiplier=self.config.SUPERTREND_MULTIPLIER
            )
            self.strategy_manager.add_strategy(self.supertrend)
            
            # Monitor başlat
            self.monitor = SystemMonitor(self)
            
            # Telegram bot başlat (opsiyonel)
            if TELEGRAM_CONFIG['use_telegram']:
                try:
                    self.telegram = TelegramBot()
                    # Yeni event loop oluştur ve ayarla
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Bot'u başlat
                    loop.run_until_complete(
                        self.telegram.initialize(
                            token=TELEGRAM_CONFIG['token'],
                            chat_id=TELEGRAM_CONFIG['chat_id'],
                            market_analyzer=self.supertrend,
                            trader=self.trader,
                            risk_manager=self.risk_manager
                        )
                    )
                    self.logger.info("Telegram bot initialized successfully")
                except Exception as e:
                    self.logger.error(f"Telegram initialization error: {e}")
                    self.telegram = None

            # Dashboard başlat
            self.visualizer = DashboardVisualizer(
                self.supertrend,
                self.trader,
                self.risk_manager
            )
            
            self.logger.info("All modules initialized")
            
        except Exception as e:
            self.logger.error(f"Module initialization error: {e}")
            raise

    def trading_loop(self):
        """Ana trading döngüsü"""
        while self.running:
            try:
                if not self.risk_manager.can_trade():
                    time.sleep(self.config.UPDATE_INTERVAL)
                    continue

                market_data = self.ws.get_market_data()
                if not market_data:
                    self.logger.warning("No market data received")
                    time.sleep(self.config.UPDATE_INTERVAL)
                    continue
                
                for strategy_name in self.strategy_manager.strategies:
                    signals = self.strategy_manager.get_signals(strategy_name, market_data)
                    if signals is None or signals.empty:
                        continue
                        
                    position = self.trader.get_position()
                    self.logger.info(f"Current position: {position}")
                    self.logger.info(f"Current signals: {signals.iloc[-1].to_dict()}")
                    
                    # Pozisyon varsa
                    if position:
                        # Trend değişimi kontrolü
                        last_signal = signals.iloc[-1]
                        if ((position['side'] == 'buy' and not last_signal['in_uptrend']) or
                            (position['side'] == 'sell' and last_signal['in_uptrend'])):
                                
                            # Pozisyonu kapat
                            self.logger.info("Closing position due to trend change")
                            close_result = self.trader.close_position()
                            if close_result:
                                self.risk_manager.update_trade_stats(position['unrealized_pnl'])
                                
                                if hasattr(self, 'telegram'):
                                    asyncio.create_task(self.telegram.send_message(
                                        f"🔄 Pozisyon Kapatıldı\n"
                                        f"📍 {position['side'].upper()}\n"
                                        f"💰 {position['size']} kontrat\n"
                                        f"💵 PnL: ${position['unrealized_pnl']:.2f}"
                                    ))
                    
                    # Pozisyon yoksa
                    else:
                        last_signal = signals.iloc[-1]
                        
                        # Sinyal kontrolü
                        if last_signal['signal_strength'] > self.config.MIN_SIGNAL_STRENGTH:
                            side = 'buy' if last_signal['in_uptrend'] else 'sell'
                            entry_price = float(last_signal['close'])
                            
                            # Risk hesaplamaları
                            position_size = self.risk_manager.calculate_position_size(side, entry_price)
                            self.logger.info(f"Calculated position size: {position_size}")
                            
                            if position_size <= 0:
                                self.logger.info("Position size too small, skipping trade")
                                continue
                                
                            stop_price = self.risk_manager.calculate_stop_loss(side, entry_price)
                            if stop_price is None:
                                self.logger.info("Could not calculate stop loss, skipping trade")
                                continue
                            
                            # Ana pozisyon emri
                            self.logger.info(f"Placing {side} order: Size={position_size}, Entry={entry_price}")
                            order = self.trader.place_order(
                                side=side,
                                amount=position_size,
                                order_type='market'
                            )
                            
                            if order:
                                self.logger.info(f"Order placed successfully: {order}")
                                # Stop loss emri
                                stop_side = 'sell' if side == 'buy' else 'buy'
                                stop_order = self.trader.place_stop_market(
                                    side=stop_side,
                                    amount=position_size,
                                    stop_price=stop_price,
                                    close_on_trigger=True
                                )
                                
                                if stop_order:
                                    self.logger.info(f"Stop order placed: {stop_order}")
                                
                                # Telegram bildirimi
                                if hasattr(self, 'telegram'):
                                    asyncio.create_task(self.telegram.send_message(
                                        f"✅ Yeni Pozisyon\n"
                                        f"📍 {side.upper()}\n"
                                        f"💰 {position_size} kontrat\n"
                                        f"🎯 Giriş: ${entry_price:.2f}\n"
                                        f"⛔ Stop: ${stop_price:.2f}"
                                    ))
                            else:
                                self.logger.error("Order placement failed")
                
                time.sleep(self.config.UPDATE_INTERVAL)
                
            except Exception as e:
                self.logger.error(f"Trading loop error: {e}")
                time.sleep(self.config.ERROR_HANDLING['RETRY_DELAY'])

    def start(self):
        """Trading bot'u başlat"""
        self.running = True
        self.monitor.start_monitoring()
        # Trading loop'u ayrı bir thread'de başlat
        trading_thread = threading.Thread(target=self.trading_loop, daemon=True)
        trading_thread.start()
        # Dashboard'ı ana thread'de başlat
        self.visualizer.start_dashboard()

    def stop(self):
        """Trading bot'u durdur"""
        self.running = False
        self.ws.close()
        if hasattr(self, 'telegram'):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.telegram.stop())
        self.logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        # Gerçek hesap uyarısı
        if not BITMEX_CONFIG['testnet']:
            print("\n⚠️  GERÇEK HESAPTA TRADING BAŞLATILIYOR!")
            print("3 saniye içinde iptal etmek için Ctrl+C tuşuna basın...\n")
            time.sleep(3)
        
        bot = TradingBot()
        bot.start()
    except KeyboardInterrupt:
        print("\nBot durduruldu!")
        bot.stop()
