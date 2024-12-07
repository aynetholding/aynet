
# trading_controls.py
import ccxt
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output, State

class TradingControls:
    def __init__(self, api_key, api_secret, testnet=False):
        self.exchange = ccxt.bitmex({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'test': testnet
        })
        
        # Varsayılan trading parametreleri
        self.trading_params = {
            'take_profit_usd': 10000,
            'stop_loss_usd': 10000,
            'leverage': 1,
            'contract_size': 100,
            'capital_percentage': 25,  # Sermayenin yüzdesi
            'balance': 0,
            'position': None
        }
        
        # Bakiye bilgisini güncelle
        self.update_balance()

    def create_control_panel(self):
        """Trading kontrol paneli oluştur"""
        return dbc.Card([
            dbc.CardHeader([
                html.H5("Trading Kontrolleri", className="mb-0"),
                html.Div([
                    html.H6("Bakiye:", className="d-inline me-2"),
                    html.H6(id='usdt-balance', className="d-inline text-success")
                ], className="mt-2")
            ]),
            dbc.CardBody([
                # Take Profit Kontrolü
                html.Div([
                    html.Label("Take Profit (USD)"),
                    dbc.Input(
                        id='tp-input',
                        type='number',
                        value=self.trading_params['take_profit_usd'],
                        min=0,
                        step=100
                    ),
                ], className="mb-3"),
                
                # Stop Loss Kontrolü
                html.Div([
                    html.Label("Stop Loss (USD)"),
                    dbc.Input(
                        id='sl-input',
                        type='number',
                        value=self.trading_params['stop_loss_usd'],
                        min=0,
                        step=100
                    ),
                ], className="mb-3"),
                
                # Kaldıraç Kontrolü
                html.Div([
                    html.Label("Kaldıraç"),
                    dcc.Slider(
                        id='leverage-slider',
                        min=1,
                        max=100,
                        step=1,
                        value=self.trading_params['leverage'],
                        marks={i: str(i) for i in [1, 25, 50, 75, 100]},
                    ),
                    html.Div(id='leverage-value')
                ], className="mb-3"),
                
                # Kontrat Sayısı
                html.Div([
                    html.Label("Kontrat Sayısı"),
                    dbc.Input(
                        id='contract-input',
                        type='number',
                        value=self.trading_params['contract_size'],
                        min=1,
                        step=1
                    ),
                ], className="mb-3"),
                
                # Sermaye Yüzdesi
                html.Div([
                    html.Label("Sermaye Yüzdesi (%)"),
                    dcc.Slider(
                        id='capital-slider',
                        min=1,
                        max=100,
                        step=1,
                        value=self.trading_params['capital_percentage'],
                        marks={i: f'%{i}' for i in [1, 25, 50, 75, 100]},
                    ),
                    html.Div(id='capital-value')
                ], className="mb-3"),
                
                # Uygula Butonu
                dbc.Button(
                    "Parametreleri Uygula",
                    id='apply-params-button',
                    color='primary',
                    className="w-100"
                ),
            ])
        ])

    def create_position_info(self):
        """Pozisyon bilgi paneli"""
        return dbc.Card([
            dbc.CardHeader("Pozisyon Bilgileri"),
            dbc.CardBody([
                # İşlem Öncesi
                html.Div([
                    html.H6("İşlem Öncesi:", className="mb-2"),
                    html.Div(id='pre-trade-info', className="ms-3")
                ], className="mb-3"),
                
                # İşlem Sonrası
                html.Div([
                    html.H6("İşlem Sonrası:", className="mb-2"),
                    html.Div(id='post-trade-info', className="ms-3")
                ])
            ])
        ])

    def update_balance(self):
        """Bakiye bilgisini güncelle"""
        try:
            balance = self.exchange.fetch_balance()
            self.trading_params['balance'] = balance['USDT']['free']
            return self.trading_params['balance']
        except Exception as e:
            print(f"Bakiye güncelleme hatası: {e}")
            return 0

    def calculate_position_size(self, price):
        """Pozisyon büyüklüğünü hesapla"""
        available_capital = self.trading_params['balance'] * (self.trading_params['capital_percentage'] / 100)
        max_contracts = (available_capital * self.trading_params['leverage']) / price
        return min(max_contracts, self.trading_params['contract_size'])

    def format_position_info(self, position_type="LONG", price=0):
        """Pozisyon bilgilerini formatla"""
        contracts = self.calculate_position_size(price)
        capital_used = (contracts * price) / self.trading_params['leverage']
        
        return {
            'pre_trade': {
                'Yön': position_type,
                'Kontrat': f"{contracts:.2f}",
                'Kaldıraç': f"{self.trading_params['leverage']}x",
                'Kullanılan Sermaye': f"${capital_used:.2f}",
                'Sermaye Yüzdesi': f"%{self.trading_params['capital_percentage']}",
                'Giriş Fiyatı': f"${price:.2f}"
            },
            'post_trade': {
                'Take Profit': f"${price + (self.trading_params['take_profit_usd'] / contracts):.2f}",
                'Stop Loss': f"${price - (self.trading_params['stop_loss_usd'] / contracts):.2f}",
                'Risk': f"${self.trading_params['stop_loss_usd']:.2f}",
                'Hedef': f"${self.trading_params['take_profit_usd']:.2f}",
                'R/R Oranı': f"{self.trading_params['take_profit_usd'] / self.trading_params['stop_loss_usd']:.2f}"
            }
        }

def setup_callbacks(app, trading_controls):
    @app.callback(
        [Output('usdt-balance', 'children'),
         Output('leverage-value', 'children'),
         Output('capital-value', 'children')],
        [Input('interval-component', 'n_intervals'),
         Input('leverage-slider', 'value'),
         Input('capital-slider', 'value')]
    )
    def update_display_values(n, leverage, capital):
        balance = trading_controls.update_balance()
        return [
            f"${balance:.2f}",
            f"Kaldıraç: {leverage}x",
            f"Sermaye: %{capital}"
        ]

    @app.callback(
        [Output('pre-trade-info', 'children'),
         Output('post-trade-info', 'children')],
        [Input('apply-params-button', 'n_clicks')],
        [State('tp-input', 'value'),
         State('sl-input', 'value'),
         State('leverage-slider', 'value'),
         State('contract-input', 'value'),
         State('capital-slider', 'value')]
    )
    def update_position_info(n_clicks, tp, sl, leverage, contracts, capital):
        if not n_clicks:
            return None, None
            
        # Trading parametrelerini güncelle
        trading_controls.trading_params.update({
            'take_profit_usd': tp,
            'stop_loss_usd': sl,
            'leverage': leverage,
            'contract_size': contracts,
            'capital_percentage': capital
        })
        
        # Örnek fiyat (gerçek uygulamada güncel fiyat kullanılacak)
        current_price = trading_controls.exchange.fetch_ticker('BTC/USD')['last']
        
        info = trading_controls.format_position_info("LONG", current_price)
        
        pre_trade = [html.Div(f"{k}: {v}") for k, v in info['pre_trade'].items()]
        post_trade = [html.Div(f"{k}: {v}") for k, v in info['post_trade'].items()]
        
        return pre_trade, post_trade
