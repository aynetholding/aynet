
# config/trading_config.py

class TradingConfig:
    # Temel ayarlar
    SYMBOL = "XBTUSDT"
    TESTNET = True
    USE_LEVERAGE = True
    MAX_LEVERAGE = 10

    # Risk yönetimi
    INITIAL_BALANCE = None  # None olursa mevcut bakiye kullanılır
    POSITION_SIZE_PERCENT = 25  # Sermayenin yüzdesi
    MAX_DAILY_LOSS_PERCENT = 5  # Günlük maksimum kayıp
    MAX_DRAWDOWN_PERCENT = 15   # Maksimum drawdown
    STOP_LOSS_PERCENT = 1.5     # Stop loss yüzdesi
    MAX_SLIPPAGE_PERCENT = 0.1  # Maksimum kayma
    MAX_TRADES_PER_DAY = 10     # Günlük maksimum işlem sayısı

    # SuperTrend ayarları
    SUPERTREND_LENGTH = 11
    SUPERTREND_MULTIPLIER = 1.7
    MIN_SIGNAL_STRENGTH = 80    # Minimum sinyal gücü
    
    # Erken giriş ayarları
    EARLY_ENTRY = {
        'HIGH_VOLATILITY': 0.05,
        'MEDIUM_VOLATILITY': 0.03,
        'LOW_VOLATILITY': 0.01
    }

    # OrderBook ayarları
    ORDERBOOK_DEPTH = 10
    MIN_LIQUIDITY = 1000000  # Minimum likidite (USD)
    IMBALANCE_THRESHOLD = 0.2  # Dengesizlik eşiği

    # Zaman ayarları
    UPDATE_INTERVAL = 1.0  # Güncelleme sıklığı (saniye)
    TRADING_HOURS = {
        'START': '00:00',
        'END': '23:59'
    }

    # Log ayarları
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Dashboard ayarları
    DASHBOARD = {
        'PORT': 8050,
        'HOST': 'localhost',
        'DEBUG': True,
        'THEME': 'dark',
        'REFRESH_INTERVAL': 1000  # milisaniye
    }

    # Bildirim ayarları
    NOTIFICATIONS = {
        'TRADE_ALERTS': True,
        'ERROR_ALERTS': True,
        'DAILY_SUMMARY': True,
        'PERFORMANCE_ALERTS': True,
        'CONNECTION_ALERTS': True
    }

    # Veritabanı ayarları
    DATABASE = {
        'ENABLED': True,
        'TYPE': 'sqlite',  # sqlite veya postgresql
        'PATH': 'data/trading.db'
    }

    # Performans metrikleri
    METRICS = {
        'TRACK_SLIPPAGE': True,
        'TRACK_EXECUTION_TIME': True,
        'TRACK_MARKET_IMPACT': True,
        'SAVE_TRADE_HISTORY': True
    }

    # Hata yönetimi
    ERROR_HANDLING = {
        'MAX_RETRIES': 3,
        'RETRY_DELAY': 5,  # saniye
        'AUTO_RECONNECT': True
    }

    # Özel filtreler
    FILTERS = {
        'MIN_VOLUME': 1000000,  # Minimum 24s hacim
        'MIN_PRICE': 0,         # Minimum fiyat
        'MAX_PRICE': 999999,    # Maksimum fiyat
        'IGNORE_WICKS': True    # Fitilleri yoksay
    }

    @classmethod
    def get_all_settings(cls):
        """Tüm ayarları sözlük olarak döndür"""
        return {
            'symbol': cls.SYMBOL,
            'testnet': cls.TESTNET,
            'leverage': {
                'use': cls.USE_LEVERAGE,
                'max': cls.MAX_LEVERAGE
            },
            'risk': {
                'position_size': cls.POSITION_SIZE_PERCENT,
                'daily_loss': cls.MAX_DAILY_LOSS_PERCENT,
                'drawdown': cls.MAX_DRAWDOWN_PERCENT,
                'stop_loss': cls.STOP_LOSS_PERCENT,
                'slippage': cls.MAX_SLIPPAGE_PERCENT,
                'max_trades': cls.MAX_TRADES_PER_DAY
            },
            'supertrend': {
                'length': cls.SUPERTREND_LENGTH,
                'multiplier': cls.SUPERTREND_MULTIPLIER,
                'min_strength': cls.MIN_SIGNAL_STRENGTH
            },
            'entry': cls.EARLY_ENTRY,
            'orderbook': {
                'depth': cls.ORDERBOOK_DEPTH,
                'min_liquidity': cls.MIN_LIQUIDITY,
                'imbalance': cls.IMBALANCE_THRESHOLD
            },
            'timing': {
                'interval': cls.UPDATE_INTERVAL,
                'hours': cls.TRADING_HOURS
            },
            'dashboard': cls.DASHBOARD,
            'notifications': cls.NOTIFICATIONS,
            'database': cls.DATABASE,
            'metrics': cls.METRICS,
            'errors': cls.ERROR_HANDLING,
            'filters': cls.FILTERS
        }

    @classmethod
    def validate_settings(cls):
        """Ayarların geçerliliğini kontrol et"""
        assert 0 < cls.POSITION_SIZE_PERCENT <= 100, "Pozisyon büyüklüğü 0-100 arası olmalı"
        assert 0 < cls.MAX_DAILY_LOSS_PERCENT <= 100, "Günlük kayıp limiti 0-100 arası olmalı"
        assert 0 < cls.STOP_LOSS_PERCENT <= 100, "Stop loss 0-100 arası olmalı"
        assert cls.MAX_LEVERAGE > 0, "Kaldıraç 0'dan büyük olmalı"
        assert cls.UPDATE_INTERVAL > 0, "Güncelleme sıklığı 0'dan büyük olmalı"
        # ... diğer kontroller

