# start_bot.py

import os
import argparse
import json
from pathlib import Path
import logging
from datetime import datetime

def setup_initial_config():
    """İlk konfigürasyon ayarları"""
    config = {
        "trading": {
            "symbol": "XBTUSDT",
            "position_size_percent": 25,
            "max_leverage": 10,
            "stop_loss_percent": 1.5,
            "enable_trailing_stop": True
        },
        "strategy": {
            "atr_period": 7,
            "atr_multiplier": 7,
            "renko_brick_size": 125
        },
        "monitoring": {
            "enable_dashboard": True,
            "enable_api": True,
            "log_level": "INFO"
        }
    }
    return config

def create_directory_structure():
    """Klasör yapısını oluştur"""
    directories = [
        'data',
        'logs',
        'config',
        'modules',
        'tests',
        'backups'
    ]
    
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)

def setup_logging():
    """Loglama ayarları"""
    log_file = f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def main():
    parser = argparse.ArgumentParser(description='Bitmex Trading Bot Setup')
    parser.add_argument('--testnet', action='store_true', help='Testnet modunda başlat')
    parser.add_argument('--config', type=str, help='Konfigürasyon dosyası yolu')
    args = parser.parse_args()

    print("Bot kurulumu başlıyor...")

    # Klasör yapısını oluştur
    create_directory_structure()
    print("✓ Klasör yapısı oluşturuldu")

    # Loglama ayarlarını yap
    setup_logging()
    print("✓ Loglama ayarları yapıldı")

    # Konfigürasyon ayarları
    if args.config and os.path.exists(args.config):
        with open(args.config) as f:
            config = json.load(f)
    else:
        config = setup_initial_config()
    
    # Testnet ayarı
    if args.testnet:
        config['trading']['testnet'] = True
    
    # Konfigürasyonu kaydet
    with open('config/config.json', 'w') as f:
        json.dump(config, f, indent=4)
    print("✓ Konfigürasyon dosyası oluşturuldu")

    print("\nKurulum tamamlandı!")
    print("""
Başlamak için:
1. .env.example dosyasını .env olarak kopyalayın
2. API anahtarlarınızı .env dosyasına ekleyin
3. 'make start' komutu ile botu başlatın
4. http://localhost:8050 adresinden dashboard'a erişin
""")

if __name__ == "__main__":
    main()
