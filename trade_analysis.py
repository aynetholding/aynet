# modules/trade_analysis.py

import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging

class TradeAnalyzer:
   def __init__(self, database_manager):
       self.db = database_manager
       self.logger = logging.getLogger(__name__)
       
   def analyze_trades(self, start_date=None, end_date=None):
       """İşlem analizi"""
       try:
           trades_df = self.db.get_trade_history(start_date, end_date)
           
           if trades_df.empty:
               return None
               
           analysis = {
               'general': self._calculate_general_stats(trades_df),
               'time': self._analyze_time_distribution(trades_df),
               'profit': self._analyze_profit_distribution(trades_df),
               'risk': self._analyze_risk_metrics(trades_df),
               'slippage': self._analyze_slippage(trades_df)
           }
           
           return analysis
           
       except Exception as e:
           self.logger.error(f"Trade analysis error: {e}")
           return None

   def _calculate_general_stats(self, df):
       """Genel istatistikler"""
       winning_trades = df[df['pnl'] > 0]
       losing_trades = df[df['pnl'] <= 0]
       
       return {
           'total_trades': len(df),
           'winning_trades': len(winning_trades),
           'losing_trades': len(losing_trades),
           'win_rate': len(winning_trades) / len(df) if len(df) > 0 else 0,
           'total_pnl': df['pnl'].sum(),
           'average_pnl': df['pnl'].mean(),
           'largest_win': df['pnl'].max(),
           'largest_loss': df['pnl'].min(),
           'avg_win': winning_trades['pnl'].mean() if not winning_trades.empty else 0,
           'avg_loss': losing_trades['pnl'].mean() if not losing_trades.empty else 0,
           'profit_factor': abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) 
                          if not losing_trades.empty and losing_trades['pnl'].sum() != 0 else 0
       }

   def _analyze_time_distribution(self, df):
       """Zaman bazlı analiz"""
       df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
       
       hourly_stats = df.groupby('hour').agg({
           'pnl': ['count', 'sum', 'mean'],
           'id': 'count'
       }).reset_index()
       
       return {
           'best_hour': hourly_stats.loc[hourly_stats[('pnl', 'sum')].idxmax(), 'hour'],
           'worst_hour': hourly_stats.loc[hourly_stats[('pnl', 'sum')].idxmin(), 'hour'],
           'busiest_hour': hourly_stats.loc[hourly_stats[('id', 'count')].idxmax(), 'hour'],
           'hourly_distribution': hourly_stats
       }

   def _analyze_profit_distribution(self, df):
       """Kar dağılımı"""
       return {
           'pnl_distribution': {
               'mean': df['pnl'].mean(),
               'std': df['pnl'].std(),
               'skew': df['pnl'].skew(),
               'kurtosis': df['pnl'].kurtosis(),
               'percentiles': df['pnl'].describe(
                   percentiles=[.05, .25, .5, .75, .95]
               ).to_dict()
           }
       }

   def _analyze_risk_metrics(self, df):
       """Risk metrikleri"""
       df['cumulative_pnl'] = df['pnl'].cumsum()
       df['peak'] = df['cumulative_pnl'].expanding().max()
       df['drawdown'] = df['peak'] - df['cumulative_pnl']
       
       return {
           'max_drawdown': df['drawdown'].max(),
           'max_drawdown_duration': self._calculate_max_drawdown_duration(df),
           'sharpe_ratio': self._calculate_sharpe_ratio(df['pnl']),
           'sortino_ratio': self._calculate_sortino_ratio(df['pnl'])
       }

   def _analyze_slippage(self, df):
       """Kayma analizi"""
       return {
           'average_slippage': df['slippage'].mean(),
           'max_slippage': df['slippage'].max(),
           'slippage_cost': df['slippage'].sum(),
           'slippage_distribution': df['slippage'].describe().to_dict()
       }

   def _calculate_max_drawdown_duration(self, df):
       """Maximum drawdown süresi"""
       peak = df['cumulative_pnl'].expanding().max()
       drawdown = peak - df['cumulative_pnl']
       is_drawdown = drawdown > 0
       
       # Drawdown periyotlarını bul
       drawdown_start = is_drawdown.ne(is_drawdown.shift()).cumsum()
       duration = df.groupby(drawdown_start)['timestamp'].agg(['first', 'last'])
       
       if not duration.empty:
           duration['length'] = (
               pd.to_datetime(duration['last']) - 
               pd.to_datetime(duration['first'])
           ).dt.total_seconds() / 3600  # Saat cinsinden
           
           return duration['length'].max()
       return 0

   def _calculate_sharpe_ratio(self, returns, risk_free_rate=0.02):
       """Sharpe oranı"""
       if len(returns) < 2:
           return 0
           
       excess_returns = returns - risk_free_rate/252
       return np.sqrt(252) * excess_returns.mean() / excess_returns.std()

   def _calculate_sortino_ratio(self, returns, risk_free_rate=0.02):
       """Sortino oranı"""
       if len(returns) < 2:
           return 0
           
       excess_returns = returns - risk_free_rate/252
       downside_returns = excess_returns[excess_returns < 0]
       
       if len(downside_returns) == 0:
           return 0
           
       return np.sqrt(252) * excess_returns.mean() / downside_returns.std()

   def plot_analysis(self, analysis):
       """Analiz görselleştirme"""
       fig = make_subplots(
           rows=3, cols=2,
           subplot_titles=(
               'Kümülatif PnL',
               'Saatlik Dağılım',
               'PnL Dağılımı',
               'Drawdown',
               'Slippage Dağılımı',
               'Trade Büyüklüğü'
           )
       )
       
       # Grafikleri oluştur
       self._add_cumulative_pnl_plot(fig, analysis, 1, 1)
       self._add_hourly_distribution_plot(fig, analysis, 1, 2)
       self._add_pnl_distribution_plot(fig, analysis, 2, 1)
       self._add_drawdown_plot(fig, analysis, 2, 2)
       self._add_slippage_plot(fig, analysis, 3, 1)
       self._add_trade_size_plot(fig, analysis, 3, 2)
       
       fig.update_layout(height=1000, showlegend=True)
       return fig
