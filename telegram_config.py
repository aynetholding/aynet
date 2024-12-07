# Telegram bot konfigürasyonu
TELEGRAM_CONFIG = {
    'use_telegram': True,  # Telegram bildirimleri aktif/pasif
    'token': '6883516719:AAF1Oht4cAMz3AHBwBh7AEDMGb10_7qZPfY',  # Bot token'ı
    'chat_id': '-4048520903',  # Chat ID
    
    # Bildirim ayarları
    'notifications': {
        'trades': True,      # Trade bildirimleri
        'signals': True,     # Sinyal bildirimleri
        'errors': True,      # Hata bildirimleri
        'performance': True, # Performans bildirimleri
        'system': True      # Sistem bildirimleri
    },
    
    # Bildirim limitleri
    'limits': {
        'min_pnl_notify': 10,  # Minimum PnL bildirimi (USD)
        'max_notifications_per_hour': 20,  # Saatlik maksimum bildirim
        'notification_cooldown': 300  # Bildirimler arası minimum süre (saniye)
    }
}
