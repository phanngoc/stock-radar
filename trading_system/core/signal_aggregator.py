"""Signal Aggregator - Combine signals from all phases"""
import numpy as np
from typing import Dict, Optional


class SignalAggregator:
    """
    Aggregate signals từ tất cả 5 phases
    - Weighted combination
    - Confirmation logic
    - Final trading decision
    """
    
    def __init__(self, phase_weights: Optional[Dict] = None):
        self.phase_weights = phase_weights or {
            'foundation': 0.25,
            'network': 0.20,
            'multivariate': 0.20,
            'pattern': 0.25,
            'crypto': 0.10
        }
        
    def aggregate(self, signals: Dict) -> Dict:
        """
        Aggregate signals từ multiple phases
        
        Args:
            signals: dict {phase_name: {'signal': float, 'confidence': float}}
            
        Returns:
            dict: {
                'composite_signal': float,
                'confidence': float,
                'action': str,
                'position_size': float
            }
        """
        total_weight = 0
        weighted_signal = 0
        weighted_confidence = 0
        
        for phase, weight in self.phase_weights.items():
            if phase in signals and 'signal' in signals[phase]:
                sig = signals[phase]['signal']
                conf = signals[phase].get('confidence', 0.5)
                
                weighted_signal += weight * sig
                weighted_confidence += weight * conf
                total_weight += weight
                
        if total_weight == 0:
            return {'error': 'No valid signals'}
            
        composite = weighted_signal / total_weight
        confidence = weighted_confidence / total_weight
        
        # Confirmation bonus
        agreement_count = sum(
            1 for p in signals.values() 
            if 'signal' in p and np.sign(p['signal']) == np.sign(composite)
        )
        
        if agreement_count >= 3:
            confidence = min(confidence * 1.2, 1.0)
            
        # Action
        if composite > 0.3 and confidence > 0.5:
            action = 'BUY'
        elif composite < -0.3 and confidence > 0.5:
            action = 'SELL'
        else:
            action = 'HOLD'
            
        return {
            'composite_signal': float(composite),
            'confidence': float(confidence),
            'action': action,
            'agreement_count': agreement_count,
            'phases_used': list(signals.keys())
        }
