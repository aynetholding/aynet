# modules/performance_analyzer.py
import pandas as pd
import numpy as np

class PerformanceAnalyzer:
    def __init__(self):
        self.is_active = False
        
    def analyze_performance(self, trades_history):
        if not self.is_active:
            return None
            
        stats = {
            'total_trades': len(trades_history),
            'win_rate': self.calculate_win_rate(trades_history),
            'avg_profit': self.calculate_avg_profit(trades_history),
            'max_drawdown': self.calculate_max_drawdown(trades_history),
            'sharpe_ratio': self.calculate_sharpe_ratio(trades_history),
            'improvement_suggestions': self.generate_suggestions(trades_history)
        }
        
        return stats
        
    def generate_suggestions(self, trades_history):
        suggestions = []
        
        # Win rate analizi
        if self.calculate_win_rate(trades_history) < 0.5:
            suggestions.append("Giriş stratejinizi gözden geçirin")
            
        # Drawdown analizi
        if self.calculate_max_drawdown(trades_history) > 0.2:
            suggestions.append("Risk yönetimi parametrelerini sıkılaştırın")
            
        # Pozisyon boyutu analizi
        if self.analyze_position_sizes(trades_history):
            suggestions.append("Pozisyon boyutlarını optimize edin")
            
        return suggestions
