"""Pattern Signals - Aggregate Phase 4"""
import numpy as np
from .regime_detector import AdvancedRegimeDetector
from .factor_model import FactorModel
from .anomaly_detector import AnomalyDetector


class PatternSignals:
    """
    Aggregate signals từ pattern hunting:
    - Regime detection
    - Factor alpha
    - Anomaly detection
    """
    
    def __init__(self):
        self.regime = AdvancedRegimeDetector(n_regimes=4)
        self.factor = FactorModel(n_factors=5)
        self.anomaly = AnomalyDetector(z_threshold=2.0)
        
    def generate(self, prices_df, returns_df, target_asset):
        """
        Generate composite pattern signal
        """
        if target_asset not in prices_df.columns:
            return {'error': f'{target_asset} not found'}
            
        # Regime signal (use target prices)
        regime_signal = self.regime.get_signal(prices_df[target_asset].values)
        
        # Factor alpha signal
        factor_signal = self.factor.get_alpha_signal(returns_df, target_asset)
        
        # Anomaly signal
        anomaly_signal = self.anomaly.get_anomaly_signal(prices_df, returns_df, target_asset)
        
        # Weighted composite
        weights = {'regime': 0.45, 'factor': 0.30, 'anomaly': 0.25}
        
        composite = (
            weights['regime'] * regime_signal['signal'] +
            weights['factor'] * factor_signal['signal'] +
            weights['anomaly'] * anomaly_signal['signal']
        )
        
        confidence = (
            weights['regime'] * regime_signal['confidence'] +
            weights['factor'] * factor_signal['confidence'] +
            weights['anomaly'] * anomaly_signal['confidence']
        )
        
        # Regime override
        if regime_signal['regime'] == 'BEAR_HIGH_VOL':
            composite = min(composite, 0)  # No long in crash
        elif regime_signal['regime'] == 'BULL_LOW_VOL':
            composite = max(composite, 0)  # No short in strong bull
            
        return {
            'signal': float(composite),
            'confidence': float(confidence),
            'regime': regime_signal['regime'],
            'regime_action': regime_signal['action'],
            'components': {
                'regime': regime_signal,
                'factor': factor_signal,
                'anomaly': anomaly_signal
            }
        }
    
    def scan_opportunities(self, prices_df, returns_df):
        """
        Scan all assets for opportunities
        """
        opportunities = []
        
        for asset in prices_df.columns:
            try:
                result = self.generate(prices_df, returns_df, asset)
                if 'error' not in result:
                    opportunities.append({
                        'asset': asset,
                        'signal': result['signal'],
                        'confidence': result['confidence'],
                        'regime': result['regime']
                    })
            except:
                continue
                
        # Sort by signal strength
        opportunities.sort(key=lambda x: abs(x['signal'] * x['confidence']), reverse=True)
        
        return {
            'buy_candidates': [o for o in opportunities if o['signal'] > 0.3][:5],
            'sell_candidates': [o for o in opportunities if o['signal'] < -0.3][:5],
            'all': opportunities
        }
