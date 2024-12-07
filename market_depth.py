
# modules/market_depth.py
import plotly.graph_objects as go
import pandas as pd

class MarketDepthVisualizer:
    def __init__(self):
        self.is_active = False
    
    def create_depth_chart(self, orderbook_data):
        if not self.is_active:
            return None
            
        fig = go.Figure()
        
        # Alış emirleri (yeşil)
        fig.add_trace(go.Scatter(
            x=orderbook_data['bids_price'],
            y=orderbook_data['bids_volume'],
            fill='tozeroy',
            fillcolor='rgba(38, 166, 154, 0.3)',
            line=dict(color='rgb(38, 166, 154)'),
            name='Alış Emirleri'
        ))
        
        # Satış emirleri (kırmızı)
        fig.add_trace(go.Scatter(
            x=orderbook_data['asks_price'],
            y=orderbook_data['asks_volume'],
            fill='tozeroy',
            fillcolor='rgba(239, 83, 80, 0.3)',
            line=dict(color='rgb(239, 83, 80)'),
            name='Satış Emirleri'
        ))
        
        fig.update_layout(
            title='Piyasa Derinliği',
            xaxis_title='Fiyat',
            yaxis_title='Hacim',
            height=300
        )
        
        return fig
