
# telegram_reporting.py
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import pandas as pd
import plotly.express as px
from io import BytesIO
import matplotlib.pyplot as plt

class TelegramReportingBot:
    def __init__(self, token):
        self.token = token
        self.updater = None
        self.reports_config = {
            'position_updates': True,      # Pozisyon güncellemeleri
            'trade_alerts': True,          # Al/sat sinyalleri
            'daily_summary': False,        # Günlük özet
            'risk_alerts': False,          # Risk uyarıları
            'performance_stats': False,    # Performans istatistikleri
            'market_analysis': False,      # Piyasa analizi
            'supertrend_signals': False,   # SuperTrend sinyalleri
            'technical_levels': False      # Teknik seviyeler
        }

    def setup_commands(self):
        dp = self.updater.dispatcher
        
        # Temel Komutlar
        dp.add_handler(CommandHandler("start", self.start_command))
        dp.add_handler(CommandHandler("help", self.help_command))
        
        # Pozisyon ve İşlem Komutları
        dp.add_handler(CommandHandler("position", self.get_position))
        dp.add_handler(CommandHandler("trades", self.get_recent_trades))
        dp.add_handler(CommandHandler("pnl", self.get_pnl))
        
        # Analiz Komutları
        dp.add_handler(CommandHandler("analysis", self.get_market_analysis))
        dp.add_handler(CommandHandler("levels", self.get_technical_levels))
        dp.add_handler(CommandHandler("risk", self.get_risk_analysis))
        
        # Rapor Komutları
        dp.add_handler(CommandHandler("daily", self.get_daily_summary))
        dp.add_handler(CommandHandler("stats", self.get_performance_stats))
        dp.add_handler(CommandHandler("signals", self.get_supertrend_signals))

    async def get_position(self, update, context):
        """Mevcut pozisyon detayları"""
        if not self.reports_config['position_updates']:
            await update.message.reply_text("❌ Pozisyon raporlaması devre dışı.")
            return

        position_info = f"""
🔵 Pozisyon Detayları:
└── Yön: {'Long' if position['side'] == 'buy' else 'Short'}
└── Boyut: {position['size']} USD
└── Giriş: ${position['entry_price']}
└── Market: ${position['current_price']}
└── P/L: {position['unrealized_pnl']}%
└── Risk: {position['risk_level']}
"""
        await update.message.reply_text(position_info)

    async def get_daily_summary(self, update, context):
        """Günlük özet raporu"""
        if not self.reports_config['daily_summary']:
            await update.message.reply_text("❌ Günlük özet devre dışı.")
            return

        summary = f"""
📊 Günlük Özet:
├── İşlem Sayısı: {daily_stats['trade_count']}
├── Kazanç/Kayıp: {daily_stats['pnl']}%
├── En İyi Trade: {daily_stats['best_trade']}%
├── En Kötü Trade: {daily_stats['worst_trade']}%
├── Win Rate: {daily_stats['win_rate']}%
└── Ortalama RR: {daily_stats['avg_rr']}
"""
        await update.message.reply_text(summary)

    async def get_performance_stats(self, update, context):
        """Detaylı performans istatistikleri"""
        if not self.reports_config['performance_stats']:
            await update.message.reply_text("❌ Performans istatistikleri devre dışı.")
            return

        stats = f"""
📈 Performans İstatistikleri:
├── Toplam PnL: {stats['total_pnl']}%
├── Sharpe Ratio: {stats['sharpe']}
├── Sortino Ratio: {stats['sortino']}
├── Max Drawdown: {stats['max_dd']}%
├── Win Rate: {stats['win_rate']}%
├── Profit Faktör: {stats['profit_factor']}
└── Ortalama Trade: {stats['avg_trade']}%

🔄 Trade İstatistikleri:
├── Toplam Trade: {stats['total_trades']}
├── Kazançlı: {stats['winning_trades']}
├── Kayıplı: {stats['losing_trades']}
├── Ortalama Kazanç: {stats['avg_win']}%
└── Ortalama Kayıp: {stats['avg_loss']}%
"""
        await update.message.reply_text(stats)

    async def get_risk_analysis(self, update, context):
        """Risk analizi raporu"""
        if not self.reports_config['risk_alerts']:
            await update.message.reply_text("❌ Risk analizi devre dışı.")
            return

        risk_info = f"""
⚠️ Risk Analizi:
├── Mevcut Risk: {risk['current_risk']}%
├── Port. Risk: {risk['portfolio_risk']}%
├── Kaldıraç: {risk['leverage']}x
├── Marj Kul.: {risk['margin_usage']}%
└── Liq. Mesafe: {risk['liquidation_distance']}%
"""
        await update.message.reply_text(risk_info)

    async def get_market_analysis(self, update, context):
        """Piyasa analizi raporu"""
        if not self.reports_config['market_analysis']:
            await update.message.reply_text("❌ Piyasa analizi devre dışı.")
            return

        analysis = f"""
🔍 Piyasa Analizi:
├── Trend: {analysis['trend']}
├── RSI: {analysis['rsi']}
├── Volatilite: {analysis['volatility']}%
├── 24s Değişim: {analysis['change_24h']}%
├── Hacim: {analysis['volume']} BTC
└── Funding Rate: {analysis['funding_rate']}%
"""
        await update.message.reply_text(analysis)

    async def get_supertrend_signals(self, update, context):
        """SuperTrend sinyalleri"""
        if not self.reports_config['supertrend_signals']:
            await update.message.reply_text("❌ SuperTrend sinyalleri devre dışı.")
            return

        signals = f"""
🎯 SuperTrend Sinyalleri:
├── Sinyal: {signals['current_signal']}
├── Trend Yönü: {signals['trend_direction']}
├── Trend Gücü: {signals['trend_strength']}
├── Son Sinyal: {signals['last_signal_time']}
└── Sinyal Fiyatı: ${signals['signal_price']}
"""
        await update.message.reply_text(signals)

    def toggle_report(self, report_name: str, state: bool):
        """Rapor özelliklerini aç/kapat"""
        if report_name in self.reports_config:
            self.reports_config[report_name] = state
            return True
        return False

    def get_active_reports(self):
        """Aktif raporları listele"""
        return {k: v for k, v in self.reports_config.items() if v}

class TelegramControlPanel:
    def create_panel(self):
        return dbc.Card([
            dbc.CardHeader("Telegram Rapor Kontrolleri"),
            dbc.CardBody([
                dbc.Switch(
                    id='telegram-position-switch',
                    label='Pozisyon Güncellemeleri',
                    value=True
                ),
                dbc.Switch(
                    id='telegram-trades-switch',
                    label='İşlem Alertleri',
                    value=True
                ),
                dbc.Switch(
                    id='telegram-daily-switch',
                    label='Günlük Özet',
                    value=False
                ),
                dbc.Switch(
                    id='telegram-risk-switch',
                    label='Risk Uyarıları',
                    value=False
                ),
                dbc.Switch(
                    id='telegram-performance-switch',
                    label='Performans İstatistikleri',
                    value=False
                ),
                dbc.Switch(
                    id='telegram-market-switch',
                    label='Piyasa Analizi',
                    value=False
                ),
                dbc.Switch(
                    id='telegram-signals-switch',
                    label='SuperTrend Sinyalleri',
                    value=False
                ),
                dbc.Switch(
                    id='telegram-levels-switch',
                    label='Teknik Seviyeler',
                    value=False
                )
            ])
        ])
