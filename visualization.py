
# modules/visualization.py

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import pandas as pd
import logging
from datetime import datetime

class DashboardVisualizer:
    def __init__(self, market_analyzer, order_manager, risk_manager):
        self.market_analyzer = market_analyzer
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.logger = logging.getLogger(__name__)
        
        # Veri depolama
        self.price_history = []
        self.trade_history = []
        
        # Grafik ayarları
        self.chart_config = {
            'theme': 'dark',
            'colors': {
                'background': '#1e1e1e',
                'text': '#ffffff',
                'buy': '#26a69a',
                'sell': '#ef5350',
                'line': '#2196f3',
                'grid': '#333333'
            }
        }

    def create_main_chart(self):
        """Ana grafik oluştur"""
        try:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.7, 0.3],
                subplot_titles=('XBTUSDT', 'SuperTrend Sinyalleri')
            )
            
            # Mum grafiği
            fig.add_trace(
                go.Candlestick(
                    x=self.market_analyzer.price_data.index,
                    open=self.market_analyzer.price_data['open'],
                    high=self.market_analyzer.price_data['high'],
                    low=self.market_analyzer.price_data['low'],
                    close=self.market_analyzer.price_data['close'],
                    name='XBTUSDT'
                ),
                row=1, col=1
            )
            
            # SuperTrend çizgisi
            supertrend_data = self.market_analyzer.calculate_supertrend()
            if supertrend_data is not None:
                fig.add_trace(
                    go.Scatter(
                        x=supertrend_data.index,
                        y=supertrend_data['upperband'],
                        mode='lines',
                        line=dict(color=self.chart_config['colors']['sell']),
                        name='SuperTrend Üst'
                    ),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=supertrend_data.index,
                        y=supertrend_data['lowerband'],
                        mode='lines',
                        line=dict(color=self.chart_config['colors']['buy']),
                        name='SuperTrend Alt'
                    ),
                    row=1, col=1
                )
            
            # İşlem noktaları
            for trade in self.trade_history:
                fig.add_trace(
                    go.Scatter(
                        x=[trade['timestamp']],
                        y=[trade['price']],
                        mode='markers',
                        marker=dict(
                            symbol='triangle-up' if trade['side'] == 'buy' else 'triangle-down',
                            size=12,
                            color=self.chart_config['colors']['buy'] if trade['side'] == 'buy' 
                                  else self.chart_config['colors']['sell']
                        ),
                        name=f"{trade['side'].title()} Entry"
                    ),
                    row=1, col=1
                )
            
            # Sinyal göstergesi
            fig.add_trace(
                go.Scatter(
                    x=supertrend_data.index,
                    y=supertrend_data['in_uptrend'],
                    mode='lines',
                    line=dict(color=self.chart_config['colors']['line']),
                    name='SuperTrend Signal'
                ),
                row=2, col=1
            )
            
            # Grafik düzeni
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor=self.chart_config['colors']['background'],
                plot_bgcolor=self.chart_config['colors']['background'],
                xaxis_rangeslider_visible=False,
                height=800
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Chart creation error: {e}")
            return None

    def create_order_book_visual(self):
        """Order book görselleştirmesi"""
        try:
            ob_state = self.order_manager.ob_manager.get_current_state()
            if not ob_state:
                return None
                
            fig = go.Figure()
            
            # Alış emirleri
            fig.add_trace(
                go.Bar(
                    x=ob_state['bids_prices'],
                    y=ob_state['bids_volumes'],
                    name='Bids',
                    marker_color=self.chart_config['colors']['buy']
                )
            )
            
            # Satış emirleri
            fig.add_trace(
                go.Bar(
                    x=ob_state['asks_prices'],
                    y=ob_state['asks_volumes'],
                    name='Asks',
                    marker_color=self.chart_config['colors']['sell']
                )
            )
            
            fig.update_layout(
                title='Order Book',
                template='plotly_dark',
                height=400
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Order book visualization error: {e}")
            return None

    def create_dashboard_layout(self):
        """Dashboard layout oluştur"""
        return dbc.Container([
            # Üst Bar
            dbc.Row([
                dbc.Col(html.H1("XBTUSDT Trading Bot", className="text-center mb-4"))
            ]),
            
            # Ana Panel
            dbc.Row([
                # Sol Panel - Grafikler
                dbc.Col([
                    dcc.Graph(id='main-chart'),
                    dcc.Graph(id='order-book-chart')
                ], width=9),
                
                # Sağ Panel - Kontroller ve Bilgiler
                dbc.Col([
                    # Pozisyon Bilgisi
                    dbc.Card([
                        dbc.CardHeader("Pozisyon Bilgisi"),
                        dbc.CardBody(id='position-info')
                    ], className="mb-3"),
                    
                    # SuperTrend Sinyalleri
                    dbc.Card([
                        dbc.CardHeader("SuperTrend Sinyalleri"),
                        dbc.CardBody(id='signal-info')
                    ], className="mb-3"),
                    
                    # Risk Metrikleri
                    dbc.Card([
                        dbc.CardHeader("Risk Metrikleri"),
                        dbc.CardBody(id='risk-info')
                    ])
                ], width=3)
            ]),
            
            dcc.Interval(
                id='update-interval',
                interval=1000,  # her saniye
                n_intervals=0
            )
        ], fluid=True)

    def update_position_info(self):
        """Pozisyon bilgilerini güncelle"""
        position = self.order_manager.get_position()
        if not position:
            return html.Div("Aktif pozisyon yok")
            
        return html.Div([
            html.P(f"Yön: {position['side'].upper()}"),
            html.P(f"Büyüklük: {position['size']} kontrakt"),
            html.P(f"Giriş: ${position['entry_price']:.2f}"),
            html.P(f"Unrealized PnL: ${position['unrealized_pnl']:.2f}")
        ])

    def update_signal_info(self):
        """Sinyal bilgilerini güncelle"""
        signals = self.market_analyzer.current_signals
        entry_conditions = self.market_analyzer.get_entry_conditions()
        
        return html.Div([
            html.P(f"Yön: {signals['direction'].upper()}"),
            html.P(f"Sinyal Gücü: {entry_conditions['strength']}%"),
            html.Div([
                html.P("Giriş Nedenleri:"),
                html.Ul([
                    html.Li(reason) for reason in entry_conditions['reasons']
                ])
            ])
        ])

    def update_risk_info(self):
        """Risk metriklerini güncelle"""
        metrics = self.risk_manager.get_risk_metrics()
        
        return html.Div([
            html.P(f"Günlük PnL: ${metrics['daily_stats']['pnl']:.2f}"),
            html.P(f"Max Drawdown: {metrics['account_metrics']['max_drawdown']:.2f}%"),
            html.P(f"Win Rate: {metrics['position_metrics']['win_rate']:.2f}%"),
            html.P(f"Avg Slippage: ${metrics['position_metrics']['avg_slippage']:.2f}")
        ])

    def add_trade_marker(self, trade):
        """İşlem noktası ekle"""
        self.trade_history.append({
            'timestamp': trade['timestamp'],
            'price': trade['entry_price'],
            'side': trade['side']
        })
