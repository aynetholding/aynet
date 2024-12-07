import websocket
import json
import threading
import logging
import time
from datetime import datetime
import hmac
import hashlib
import urllib.parse
from collections import deque

class BitmexWebsocket:
    def __init__(self, api_key, api_secret, testnet=True, symbol="XBTUSD"):
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        
        # Websocket URL'i
        if testnet:
            self.endpoint = "wss://testnet.bitmex.com/realtime"
        else:
            self.endpoint = "wss://www.bitmex.com/realtime"
            
        # Bağlantı durumu
        self.ws = None
        self.connected = False
        self.should_reconnect = True
        self.reconnect_count = 0
        
        # Veri yapıları
        self.trades = deque(maxlen=1000)  # Son 1000 trade
        self.orderbook = {
            'bids': {},
            'asks': {},
            'timestamp': None
        }
        self.ticker = {}
        self.positions = []
        
        # Thread yönetimi
        self.ping_thread = None
        self.last_ping = datetime.now()
        self.mutex = threading.Lock()

    def generate_signature(self, expires):
        """HMAC signature oluştur"""
        verb = 'GET'
        url = '/realtime'
        
        signature = hmac.new(
            bytes(self.api_secret, 'utf8'),
            bytes(verb + url + str(expires), 'utf8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return signature

    def connect(self):
        """WebSocket bağlantısı başlat"""
        try:
            websocket.enableTrace(True)
            
            # Auth parametreleri
            expires = int(time.time()) + 5
            signature = self.generate_signature(expires)
            
            auth_params = {
                'api-key': self.api_key,
                'api-expires': str(expires),
                'api-signature': signature
            }
            
            # Query string oluştur
            auth_string = '&'.join([f'{k}={v}' for k, v in auth_params.items()])
            url = f"{self.endpoint}?{auth_string}"
            
            # WebSocket bağlantısı
            self.ws = websocket.WebSocketApp(
                url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # Bağlantıyı başlat
            wst = threading.Thread(target=lambda: self.ws.run_forever())
            wst.daemon = True
            wst.start()
            
            # Ping thread'ini başlat
            self.ping_thread = threading.Thread(target=self._ping_loop)
            self.ping_thread.daemon = True
            self.ping_thread.start()
            
            self.logger.info("WebSocket bağlantısı başlatıldı")
            
        except Exception as e:
            self.logger.error(f"WebSocket bağlantı hatası: {e}")
            self.reconnect()

    def _ping_loop(self):
        """Ping/Pong kontrolü"""
        while self.connected:
            try:
                if (datetime.now() - self.last_ping).seconds > 10:
                    self.ws.send('ping')
                    self.last_ping = datetime.now()
                time.sleep(5)
            except Exception as e:
                self.logger.error(f"Ping error: {e}")

    def _on_message(self, ws, message):
        """WebSocket mesaj işleme"""
        try:
            data = json.loads(message)
            
            if 'table' not in data:
                return
                
            table = data['table']
            action = data.get('action', '')
            
            if table == 'trade':
                self._handle_trade(data['data'])
            elif table == 'orderBook10':
                self._handle_orderbook(data['data'])
            elif table == 'instrument':
                self._handle_ticker(data['data'])
            elif table == 'position':
                self._handle_position(data['data'])
                
        except Exception as e:
            self.logger.error(f"Mesaj işleme hatası: {e}")

    def _handle_trade(self, trades):
        """Trade verilerini işle"""
        with self.mutex:
            for trade in trades:
                self.trades.append({
                    'timestamp': datetime.strptime(trade['timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                    'side': trade['side'],
                    'size': trade['size'],
                    'price': trade['price'],
                    'tickDirection': trade.get('tickDirection'),
                    'trdMatchID': trade['trdMatchID']
                })

    def _handle_orderbook(self, orderbook):
        """OrderBook verilerini işle"""
        with self.mutex:
            if not orderbook:
                return
                
            data = orderbook[0]  # En son orderbook
            
            self.orderbook = {
                'bids': {price: size for price, size in data['bids']},
                'asks': {price: size for price, size in data['asks']},
                'timestamp': datetime.now()
            }

    def _handle_ticker(self, ticker):
        """Ticker verilerini işle"""
        if not ticker:
            return
            
        data = ticker[0]
        self.ticker = {
            'last_price': data['lastPrice'],
            'high_price': data['highPrice'],
            'low_price': data['lowPrice'],
            'mark_price': data['markPrice'],
            'volume_24h': data['volume24h'],
            'timestamp': datetime.now()
        }

    def _handle_position(self, positions):
        """Pozisyon verilerini işle"""
        if not positions:
            return
            
        self.positions = [{
            'symbol': pos['symbol'],
            'size': pos['currentQty'],
            'entry_price': pos['avgEntryPrice'],
            'mark_price': pos['markPrice'],
            'liq_price': pos['liquidationPrice'],
            'leverage': pos['leverage']
        } for pos in positions]

    def _on_error(self, ws, error):
        """Hata yönetimi"""
        self.logger.error(f"WebSocket hatası: {error}")
        if self.should_reconnect:
            self.reconnect()

    def _on_close(self, ws, close_status_code, close_msg):
        """Bağlantı kapanma yönetimi"""
        self.logger.info("WebSocket bağlantısı kapandı")
        self.connected = False
        if self.should_reconnect:
            self.reconnect()

    def _on_open(self, ws):
        """Bağlantı açıldığında"""
        self.logger.info("WebSocket bağlantısı açıldı")
        self.connected = True
        self.reconnect_count = 0
        
        # Subscribe to channels
        subscriptions = [
            f"trade:{self.symbol}",
            f"orderBook10:{self.symbol}",
            f"instrument:{self.symbol}",
            "position"
        ]
        
        self.ws.send(json.dumps({
            "op": "subscribe",
            "args": subscriptions
        }))

    def get_market_data(self):
        """Market verilerini getir"""
        with self.mutex:
            last_trades = list(self.trades)[-100:]  # Son 100 trade
            
            data = {
                'trades': last_trades,
                'orderbook': self.orderbook,
                'ticker': self.ticker,
                'positions': self.positions
            }
            
            return data

    def reconnect(self):
        """Yeniden bağlanma mantığı"""
        try:
            self.reconnect_count += 1
            if self.reconnect_count > 5:
                self.logger.error("Maksimum yeniden bağlanma denemesi aşıldı")
                return
                
            self.logger.info(f"Yeniden bağlanılıyor... Deneme: {self.reconnect_count}")
            time.sleep(5 * self.reconnect_count)  # Exponential backoff
            self.connect()
            
        except Exception as e:
            self.logger.error(f"Yeniden bağlanma hatası: {e}")

    def close(self):
        """Bağlantıyı kapat"""
        self.should_reconnect = False
        if self.ws:
            self.ws.close()
        self.connected = False
        self.logger.info("WebSocket bağlantısı kapatıldı")
