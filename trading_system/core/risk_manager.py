"""Risk Manager - Position sizing, Stop loss, Portfolio risk"""
import numpy as np
from typing import Dict, Optional


class RiskManager:
    """
    Risk Management cho trading system
    - Kelly Criterion position sizing
    - Stop loss / Take profit
    - Portfolio-level risk controls
    """
    
    def __init__(self, max_position=0.25, max_drawdown=0.15):
        self.max_position = max_position  # Max 25% per position
        self.max_drawdown = max_drawdown  # Stop trading at 15% DD
        self.portfolio_value = 100000  # Default
        self.peak_value = 100000
        
    def kelly_criterion(self, win_prob: float, win_loss_ratio: float = 2.0) -> float:
        """
        Kelly Criterion: f* = (p*b - q) / b
        
        Args:
            win_prob: probability of winning (0-1)
            win_loss_ratio: avg_win / avg_loss
            
        Returns:
            float: optimal fraction of capital to bet
        """
        if win_prob <= 0 or win_prob >= 1:
            return 0
            
        q = 1 - win_prob
        b = win_loss_ratio
        
        kelly = (win_prob * b - q) / b
        
        # Half-Kelly for safety
        kelly = kelly * 0.5
        
        # Cap at max position
        return max(0, min(kelly, self.max_position))
    
    def calculate_position_size(self, signal: float, confidence: float, 
                                 current_price: float) -> Dict:
        """
        Calculate position size based on signal and confidence
        
        Returns:
            dict: {
                'position_pct': float,
                'shares': int,
                'dollar_amount': float
            }
        """
        import math
        
        # Handle NaN/invalid inputs
        if math.isnan(signal) or math.isnan(confidence) or math.isnan(current_price):
            return {
                'position_pct': 0,
                'shares': 0,
                'dollar_amount': 0,
                'direction': 'NONE'
            }
        
        # Convert confidence to win probability
        win_prob = 0.5 + (confidence * 0.2)  # 50-70% range
        
        # Adjust by signal strength
        base_size = self.kelly_criterion(win_prob)
        position_pct = base_size * abs(signal)
        
        dollar_amount = self.portfolio_value * position_pct
        shares = int(dollar_amount / current_price) if current_price > 0 else 0
        
        return {
            'position_pct': position_pct,
            'shares': shares,
            'dollar_amount': dollar_amount,
            'direction': 'LONG' if signal > 0 else 'SHORT' if signal < 0 else 'NONE'
        }
    
    def calculate_stop_loss(self, entry_price: float, volatility: float,
                            atr_multiplier: float = 2.0) -> Dict:
        """
        Calculate stop loss based on volatility (ATR-based)
        """
        stop_distance = volatility * atr_multiplier
        
        return {
            'stop_loss': entry_price * (1 - stop_distance),
            'stop_pct': stop_distance,
            'take_profit': entry_price * (1 + stop_distance * 2),  # 2:1 R/R
            'risk_reward': 2.0
        }
    
    def check_portfolio_risk(self, positions: Dict) -> Dict:
        """
        Check portfolio-level risk constraints
        """
        total_exposure = sum(p.get('position_pct', 0) for p in positions.values())
        
        # Drawdown check
        current_dd = (self.peak_value - self.portfolio_value) / self.peak_value
        
        warnings = []
        if total_exposure > 0.8:
            warnings.append('HIGH_EXPOSURE')
        if current_dd > self.max_drawdown * 0.7:
            warnings.append('APPROACHING_MAX_DD')
        if current_dd > self.max_drawdown:
            warnings.append('MAX_DD_BREACHED')
            
        return {
            'total_exposure': total_exposure,
            'current_drawdown': current_dd,
            'warnings': warnings,
            'can_trade': 'MAX_DD_BREACHED' not in warnings
        }
    
    def update_portfolio(self, new_value: float):
        """Update portfolio value and peak"""
        self.portfolio_value = new_value
        self.peak_value = max(self.peak_value, new_value)
