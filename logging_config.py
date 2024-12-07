# config/logging_config.py

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logging(log_dir='logs', log_level=logging.INFO):
    """Loglama sistemini ayarla"""
    
    # Log dizinini oluştur
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Log dosya adı
    log_file = f"{log_dir}/trading_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Formatter tanımla
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Root logger'ı yapılandır
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Özel logger'lar
    loggers = {
        'trading': logging.getLogger('trading'),
        'orders': logging.getLogger('orders'),
        'websocket': logging.getLogger('websocket'),
        'strategy': logging.getLogger('strategy'),
        'risk': logging.getLogger('risk')
    }

    for logger in loggers.values():
        logger.setLevel(log_level)

    return loggers
