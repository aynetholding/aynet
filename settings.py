# config/settings.py

import os
from dotenv import load_dotenv

load_dotenv()

API_CONFIG = {
   'api_key': os.getenv('BITMEX_API_KEY'),
   'api_secret': os.getenv('BITMEX_API_SECRET'),
   'testnet': os.getenv('USE_TESTNET', 'True').lower() == 'true'
}

TELEGRAM_CONFIG = {
   'token': os.getenv('TELEGRAM_TOKEN'),
   'chat_id': os.getenv('TELEGRAM_CHAT_ID'),
   'use_telegram': os.getenv('USE_TELEGRAM', 'True').lower() == 'true'
}

TRADING_CONFIG = {
   'symbol': 'XBTUSDT',
   'position_size_percent': 25,
   'max_leverage': 10,
   'stop_loss_percent': 1.5,
   'trailing_stop': True,
   'atr_period': 7,
   'atr_multiplier': 7,
   'renko_brick_size': 125,
   'min_volume': 1000000
}

SYSTEM_CONFIG = {
   'log_level': os.getenv('LOG_LEVEL', 'INFO'),
   'data_dir': 'data',
   'log_dir': 'logs',
   'db_path': os.getenv('DB_PATH', 'data/trading.db')
}

DASHBOARD_CONFIG = {
   'host': '0.0.0.0', 
   'port': int(os.getenv('DASHBOARD_PORT', '8050')),
   'debug': False
}

API_SERVER_CONFIG = {
   'host': '0.0.0.0',
   'port': int(os.getenv('API_PORT', '8000')),
   'api_key': os.getenv('API_KEY', 'your-secret-key')
}
