import logging
import threading
import time
import psutil
import pandas as pd
from datetime import datetime, timedelta
import asyncio

class SystemMonitor:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Performance metrikleri
        self.system_metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'disk_usage': [],
            'network_io': []
        }
        
        # Trading metrikleri
        self.trading_metrics = {
            'execution_times': [],
            'signal_latency': [],
            'order_latency': [],
            'websocket_latency': []
        }
        
        # Uyarı limitleri
        self.alert_thresholds = {
            'cpu_usage': 80,  # %80 CPU kullanımı
            'memory_usage': 85,  # %85 RAM kullanımı
            'disk_usage': 90,  # %90 disk kullanımı
            'execution_time': 1.0,  # 1 saniye
            'signal_latency': 0.5,  # 500ms
            'order_latency': 0.3,  # 300ms
            'websocket_latency': 0.2  # 200ms
        }
        
        self.monitor_thread = None
        self.last_check = datetime.now()
        self.alert_sent = False

    def start_monitoring(self):
        """Monitoring thread'ini başlat"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        self.logger.info("System monitoring started")

    def stop_monitoring(self):
        """Monitoring'i durdur"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        self.logger.info("System monitoring stopped")

    def _monitoring_loop(self):
        """Ana monitoring döngüsü"""
        while self.running:
            try:
                # Sistem metriklerini topla
                self._collect_system_metrics()
                
                # Trading metriklerini topla
                self._collect_trading_metrics()
                
                # Metrikleri analiz et
                self._analyze_metrics()
                
                # Eski verileri temizle (24 saatten eski)
                self._cleanup_old_data()
                
                # Loglama ve uyarılar
                self._check_alerts()
                
                time.sleep(5)  # 5 saniye bekle
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                time.sleep(10)

    def _collect_system_metrics(self):
        """Sistem metriklerini topla"""
        try:
            timestamp = datetime.now()
            
            # CPU kullanımı
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_metrics['cpu_usage'].append({
                'timestamp': timestamp,
                'value': cpu_percent
            })
            
            # Memory kullanımı
            memory = psutil.virtual_memory()
            self.system_metrics['memory_usage'].append({
                'timestamp': timestamp,
                'value': memory.percent
            })
            
            # Disk kullanımı
            disk = psutil.disk_usage('/')
            self.system_metrics['disk_usage'].append({
                'timestamp': timestamp,
                'value': disk.percent
            })
            
            # Network I/O
            network = psutil.net_io_counters()
            self.system_metrics['network_io'].append({
                'timestamp': timestamp,
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv
            })
            
        except Exception as e:
            self.logger.error(f"System metrics collection error: {e}")

    def _collect_trading_metrics(self):
        """Trading metriklerini topla"""
        try:
            timestamp = datetime.now()
            
            # Sinyal hesaplama süresi
            start_time = time.time()
            self.bot.strategy_manager.get_signals('SuperTrend', [])
            signal_time = time.time() - start_time
            
            self.trading_metrics['signal_latency'].append({
                'timestamp': timestamp,
                'value': signal_time
            })
            
            # WebSocket gecikmesi
            if hasattr(self.bot.ws, 'last_message_time'):
                ws_latency = (datetime.now() - self.bot.ws.last_message_time).total_seconds()
                self.trading_metrics['websocket_latency'].append({
                    'timestamp': timestamp,
                    'value': ws_latency
                })
            
            # Order execution zamanları
            if hasattr(self.bot.trader, 'last_order_time'):
                order_latency = (datetime.now() - self.bot.trader.last_order_time).total_seconds()
                self.trading_metrics['order_latency'].append({
                    'timestamp': timestamp,
                    'value': order_latency
                })
            
        except Exception as e:
            self.logger.error(f"Trading metrics collection error: {e}")

    def _analyze_metrics(self):
        """Metrikleri analiz et"""
        try:
            # Son 5 dakikanın metriklerini al
            cutoff_time = datetime.now() - timedelta(minutes=5)
            
            # CPU kullanım analizi
            recent_cpu = [m['value'] for m in self.system_metrics['cpu_usage'] 
                         if m['timestamp'] > cutoff_time]
            if recent_cpu:
                avg_cpu = sum(recent_cpu) / len(recent_cpu)
                if avg_cpu > self.alert_thresholds['cpu_usage']:
                    self._send_alert(f"High CPU usage: {avg_cpu:.1f}%")
            
            # Memory kullanım analizi
            recent_memory = [m['value'] for m in self.system_metrics['memory_usage'] 
                           if m['timestamp'] > cutoff_time]
            if recent_memory:
                avg_memory = sum(recent_memory) / len(recent_memory)
                if avg_memory > self.alert_thresholds['memory_usage']:
                    self._send_alert(f"High memory usage: {avg_memory:.1f}%")
            
            # WebSocket gecikme analizi
            recent_ws = [m['value'] for m in self.trading_metrics['websocket_latency'] 
                        if m['timestamp'] > cutoff_time]
            if recent_ws:
                avg_ws = sum(recent_ws) / len(recent_ws)
                if avg_ws > self.alert_thresholds['websocket_latency']:
                    self._send_alert(f"High WebSocket latency: {avg_ws*1000:.0f}ms")
            
        except Exception as e:
            self.logger.error(f"Metrics analysis error: {e}")

    def _cleanup_old_data(self):
        """24 saatten eski verileri temizle"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            # Sistem metriklerini temizle
            for metric_type in self.system_metrics:
                self.system_metrics[metric_type] = [
                    m for m in self.system_metrics[metric_type] 
                    if m['timestamp'] > cutoff_time
                ]
            
            # Trading metriklerini temizle
            for metric_type in self.trading_metrics:
                self.trading_metrics[metric_type] = [
                    m for m in self.trading_metrics[metric_type] 
                    if m['timestamp'] > cutoff_time
                ]
                
        except Exception as e:
            self.logger.error(f"Data cleanup error: {e}")

    def _check_alerts(self):
        """Uyarıları kontrol et ve gönder"""
        try:
            # Her 5 dakikada bir kontrol et
            if (datetime.now() - self.last_check) < timedelta(minutes=5):
                return
                
            self.last_check = datetime.now()
            
            # Sistem kaynaklarını kontrol et
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            alerts = []
            
            if cpu_percent > self.alert_thresholds['cpu_usage']:
                alerts.append(f"CPU usage is high: {cpu_percent}%")
            
            if memory_percent > self.alert_thresholds['memory_usage']:
                alerts.append(f"Memory usage is high: {memory_percent}%")
            
            if disk_percent > self.alert_thresholds['disk_usage']:
                alerts.append(f"Disk usage is high: {disk_percent}%")
            
            # Trading metriklerini kontrol et
            if hasattr(self.bot.ws, 'last_message_time'):
                ws_delay = (datetime.now() - self.bot.ws.last_message_time).total_seconds()
                if ws_delay > self.alert_thresholds['websocket_latency']:
                    alerts.append(f"WebSocket delay is high: {ws_delay*1000:.0f}ms")
            
            # Uyarıları gönder
            if alerts and not self.alert_sent:
                alert_message = "\n".join(alerts)
                self._send_alert(alert_message)
                self.alert_sent = True
            elif not alerts:
                self.alert_sent = False
                
        except Exception as e:
            self.logger.error(f"Alert check error: {e}")

    async def _send_alert(self, message):
        """Uyarı gönder"""
        try:
            # Log'a kaydet
            self.logger.warning(f"ALERT: {message}")
            
            # Telegram bildirimi gönder
            if hasattr(self.bot, 'telegram'):
                await self.bot.telegram.send_message(
                    f"⚠️ System Alert:\n{message}"
                )
                
        except Exception as e:
            self.logger.error(f"Alert sending error: {e}")

    def get_performance_summary(self):
        """Performans özeti getir"""
        try:
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            
            # Son 1 saatin metriklerini filtrele
            cpu_usage = [m['value'] for m in self.system_metrics['cpu_usage'] 
                        if m['timestamp'] > hour_ago]
            memory_usage = [m['value'] for m in self.system_metrics['memory_usage'] 
                          if m['timestamp'] > hour_ago]
            ws_latency = [m['value'] for m in self.trading_metrics['websocket_latency'] 
                         if m['timestamp'] > hour_ago]
            
            return {
                'system': {
                    'cpu_usage_avg': sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
                    'memory_usage_avg': sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                    'disk_usage': psutil.disk_usage('/').percent
                },
                'network': {
                    'websocket_latency_avg': sum(ws_latency) / len(ws_latency) if ws_latency else 0,
                    'connection_status': self.bot.ws.connected if hasattr(self.bot.ws, 'connected') else False
                },
                'trading': {
                    'orders_per_hour': len(self.trading_metrics['order_latency']),
                    'signals_per_hour': len(self.trading_metrics['signal_latency'])
                }
            }
            
        except Exception as e:
            self.logger.error(f"Performance summary error: {e}")
            return None
