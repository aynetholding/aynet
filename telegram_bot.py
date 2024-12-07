import logging
import asyncio
from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackContext
)
import pandas as pd
from datetime import datetime

class TelegramBot:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.bot = None
        self.application = None
        self.chat_id = None
        self.market_analyzer = None
        self.trader = None
        self.risk_manager = None

    async def initialize(self, token: str, chat_id: str, market_analyzer, trader, risk_manager):
        """Bot'u başlat ve komutları ayarla"""
        try:
            self.bot = Bot(token)
            self.chat_id = chat_id
            self.market_analyzer = market_analyzer
            self.trader = trader
            self.risk_manager = risk_manager

            # Application'ı oluştur
            self.application = Application.builder().token(token).build()

            # Komut handler'larını ekle
            self.application.add_handler(CommandHandler("start", self._start_command))
            self.application.add_handler(CommandHandler("help", self._help_command))
            self.application.add_handler(CommandHandler("status", self._status_command))
            self.application.add_handler(CommandHandler("position", self._position_command))
            self.application.add_handler(CommandHandler("close", self._close_command))
            self.application.add_handler(CommandHandler("signals", self._signals_command))
            self.application.add_handler(CommandHandler("balance", self._balance_command))
            self.application.add_handler(CommandHandler("performance", self._performance_command))

            # Diğer mesajlar için handler
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

            # Error handler
            self.application.add_error_handler(self._error_handler)

            # Bot'u başlat
            await self.application.initialize()
            await self.application.start()
            await self.application.update_bot_data()

            # Başlangıç mesajı gönder
            await self.send_message("🤖 Trading Bot başlatıldı")
            self.logger.info("Telegram bot initialized")

        except Exception as e:
            self.logger.error(f"Telegram bot initialization error: {e}")
            raise

    async def stop(self):
        """Bot'u durdur"""
        try:
            if self.application:
                await self.application.stop()
            self.logger.info("Telegram bot stopped")
        except Exception as e:
            self.logger.error(f"Telegram bot stop error: {e}")

    async def send_message(self, message: str):
        """Mesaj gönder"""
        try:
            if self.bot and self.chat_id:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode='HTML'
                )
        except Exception as e:
            self.logger.error(f"Message send error: {e}")

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start komutu işleyicisi"""
        welcome_message = (
            "🤖 Trading Bot'a hoş geldiniz!\n\n"
            "Mevcut komutlar:\n"
            "/help - Yardım menüsü\n"
            "/status - Bot durumu\n"
            "/position - Pozisyon bilgisi\n"
            "/close - Pozisyonu kapat\n"
            "/signals - Sinyal bilgileri\n"
            "/balance - Bakiye bilgisi\n"
            "/performance - Performans metrikleri"
        )
        await update.message.reply_text(welcome_message)

    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help komutu işleyicisi"""
        help_message = (
            "📚 Komut Listesi:\n\n"
            "/status - Bot durumu ve genel bilgiler\n"
            "/position - Aktif pozisyon detayları\n"
            "/close - Açık pozisyonu kapat\n"
            "/signals - Güncel trading sinyalleri\n"
            "/balance - Hesap bakiyesi ve PnL\n"
            "/performance - Performans metrikleri ve istatistikler"
        )
        await update.message.reply_text(help_message)

    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Status komutu işleyicisi"""
        try:
            position = self.trader.get_position()
            signals = self.market_analyzer.get_signal_summary()
            metrics = self.risk_manager.get_risk_metrics()

            status_message = (
                "📊 Bot Durumu\n\n"
                f"🤖 Bot Aktif: ✅\n"
                f"📈 Pozisyon: {'Var' if position else 'Yok'}\n"
                f"📉 Trend: {signals['trend'] if signals else 'N/A'}\n"
                f"💰 Günlük PnL: ${metrics['daily_stats']['pnl']:.2f}\n"
                f"📈 Win Rate: {metrics['daily_stats']['win_rate']:.1f}%"
            )
            await update.message.reply_text(status_message)

        except Exception as e:
            self.logger.error(f"Status command error: {e}")
            await update.message.reply_text("❌ Status bilgisi alınamadı")

    async def _position_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Position komutu işleyicisi"""
        try:
            position = self.trader.get_position()
            if not position:
                await update.message.reply_text("ℹ️ Aktif pozisyon yok")
                return

            position_message = (
                "📊 Pozisyon Detayları\n\n"
                f"📍 Yön: {position['side'].upper()}\n"
                f"💰 Büyüklük: {position['size']} kontrat\n"
                f"🎯 Giriş: ${position['entry_price']:.2f}\n"
                f"💵 PnL: ${position['unrealized_pnl']:.2f}\n"
                f"⚡ Kaldıraç: {position['leverage']}x\n"
                f"⚠️ Likidasyon: ${position['liquidation_price']:.2f}"
            )
            await update.message.reply_text(position_message)

        except Exception as e:
            self.logger.error(f"Position command error: {e}")
            await update.message.reply_text("❌ Pozisyon bilgisi alınamadı")

    async def _close_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Close komutu işleyicisi"""
        try:
            position = self.trader.get_position()
            if not position:
                await update.message.reply_text("ℹ️ Kapatılacak pozisyon yok")
                return

            result = self.trader.close_position()
            if result:
                close_message = (
                    "✅ Pozisyon kapatıldı\n\n"
                    f"📍 Yön: {position['side'].upper()}\n"
                    f"💰 Büyüklük: {position['size']} kontrat\n"
                    f"💵 PnL: ${position['unrealized_pnl']:.2f}"
                )
                await update.message.reply_text(close_message)
            else:
                await update.message.reply_text("❌ Pozisyon kapatılamadı")

        except Exception as e:
            self.logger.error(f"Close command error: {e}")
            await update.message.reply_text("❌ İşlem hatası")

    async def _signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Signals komutu işleyicisi"""
        try:
            signals = self.market_analyzer.get_signal_summary()
            if not signals:
                await update.message.reply_text("ℹ️ Aktif sinyal yok")
                return

            signals_message = (
                "🎯 Trading Sinyalleri\n\n"
                f"📈 Trend: {signals['trend']}\n"
                f"💪 Sinyal Gücü: {signals['strength']:.1f}%\n"
                f"📊 RSI: {signals['rsi']:.1f}\n"
                f"📉 Volatilite: {signals['volatility']:.2f}%\n"
                f"📊 Hacim Faktörü: {signals['volume_factor']:.2f}"
            )
            await update.message.reply_text(signals_message)

        except Exception as e:
            self.logger.error(f"Signals command error: {e}")
            await update.message.reply_text("❌ Sinyal bilgisi alınamadı")

    async def _balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Balance komutu işleyicisi"""
        try:
            balance = self.trader.update_balance()
            metrics = self.risk_manager.get_risk_metrics()

            balance_message = (
                "💰 Bakiye Bilgisi\n\n"
                f"💵 Total: {balance['total']:.8f} BTC\n"
                f"🆓 Kullanılabilir: {balance['free']:.8f} BTC\n"
                f"🔒 Kullanımda: {balance['used']:.8f} BTC\n"
                f"📈 Günlük PnL: ${metrics['daily_stats']['pnl']:.2f}\n"
                f"📉 Max Drawdown: {metrics['daily_stats']['max_drawdown']:.2f}%"
            )
            await update.message.reply_text(balance_message)

        except Exception as e:
            self.logger.error(f"Balance command error: {e}")
            await update.message.reply_text("❌ Bakiye bilgisi alınamadı")

    async def _performance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Performance komutu işleyicisi"""
        try:
            metrics = self.risk_manager.get_risk_metrics()
            daily_stats = metrics['daily_stats']

            performance_message = (
                "📊 Performans Metrikleri\n\n"
                f"🎯 İşlem Sayısı: {daily_stats['trades']}\n"
                f"✅ Kazanç: {daily_stats['wins']}\n"
                f"❌ Kayıp: {daily_stats['losses']}\n"
                f"📈 Win Rate: {daily_stats['win_rate']:.1f}%\n"
                f"💰 Toplam PnL: ${daily_stats['pnl']:.2f}\n"
                f"📉 Max Drawdown: {daily_stats['max_drawdown']:.2f}%"
            )
            await update.message.reply_text(performance_message)

        except Exception as e:
            self.logger.error(f"Performance command error: {e}")
            await update.message.reply_text("❌ Performans bilgisi alınamadı")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Diğer mesajları işle"""
        await update.message.reply_text(
            "ℹ️ Komut listesi için /help yazabilirsiniz"
        )

    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Hata işleyici"""
        self.logger.error(f"Telegram error: {context.error}")
        if update and isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Bir hata oluştu. Lütfen daha sonra tekrar deneyin."
            )
