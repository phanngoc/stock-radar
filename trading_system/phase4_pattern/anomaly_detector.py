"""Anomaly Detection - Cross-asset and Statistical Anomalies"""
import numpy as np
import pandas as pd
from scipy import stats


class AnomalyDetector:
    """
    Detect trading anomalies:
    - Statistical arbitrage opportunities
    - Pair deviations
    - Cross-asset anomalies
    """
    
    def __init__(self, z_threshold=2.0):
        self.z_threshold = z_threshold
        
    def detect_pair_anomaly(self, series1, series2, window=60):
        """
        Detect pair trading anomaly (spread deviation)
        """
        s1 = np.array(series1)
        s2 = np.array(series2)
        
        # Calculate spread (ratio)
        spread = s1 / s2
        
        # Rolling mean and std
        if len(spread) < window:
            window = len(spread) // 2
            
        rolling_mean = pd.Series(spread).rolling(window).mean().values
        rolling_std = pd.Series(spread).rolling(window).std().values
        
        # Z-score
        z_score = (spread[-1] - rolling_mean[-1]) / rolling_std[-1]
        
        if abs(z_score) > self.z_threshold:
            if z_score > 0:
                action = 'SHORT_S1_LONG_S2'  # Spread too high
            else:
                action = 'LONG_S1_SHORT_S2'  # Spread too low
            is_anomaly = True
        else:
            action = 'NO_ACTION'
            is_anomaly = False
            
        return {
            'is_anomaly': is_anomaly,
            'z_score': float(z_score),
            'action': action,
            'spread': float(spread[-1]),
            'mean': float(rolling_mean[-1]),
            'std': float(rolling_std[-1])
        }
    
    def scan_pair_anomalies(self, prices_df):
        """
        Scan all pairs for anomalies
        """
        assets = prices_df.columns
        anomalies = []
        
        for i, a1 in enumerate(assets):
            for j, a2 in enumerate(assets):
                if i < j:
                    result = self.detect_pair_anomaly(
                        prices_df[a1].values,
                        prices_df[a2].values
                    )
                    if result['is_anomaly']:
                        anomalies.append({
                            'pair': (a1, a2),
                            **result
                        })
                        
        # Sort by z-score magnitude
        anomalies.sort(key=lambda x: abs(x['z_score']), reverse=True)
        return anomalies
    
    def detect_momentum_anomaly(self, returns_df, lookback=20):
        """
        Detect momentum anomalies (extreme recent performance)
        """
        recent_returns = returns_df.iloc[-lookback:].sum()
        
        # Z-score across assets
        mean_ret = recent_returns.mean()
        std_ret = recent_returns.std()
        z_scores = (recent_returns - mean_ret) / std_ret
        
        anomalies = []
        for asset in returns_df.columns:
            z = z_scores[asset]
            if abs(z) > self.z_threshold:
                anomalies.append({
                    'asset': asset,
                    'z_score': float(z),
                    'return': float(recent_returns[asset]),
                    'type': 'MOMENTUM_WINNER' if z > 0 else 'MOMENTUM_LOSER'
                })
                
        return anomalies
    
    def detect_volatility_anomaly(self, returns_df, window=20):
        """
        Detect volatility anomalies (unusual vol)
        """
        recent_vol = returns_df.iloc[-window:].std()
        historical_vol = returns_df.iloc[:-window].std()
        
        vol_ratio = recent_vol / historical_vol
        
        anomalies = []
        for asset in returns_df.columns:
            ratio = vol_ratio[asset]
            if ratio > 1.5:
                anomalies.append({
                    'asset': asset,
                    'vol_ratio': float(ratio),
                    'type': 'VOL_SPIKE',
                    'action': 'REDUCE_POSITION'
                })
            elif ratio < 0.5:
                anomalies.append({
                    'asset': asset,
                    'vol_ratio': float(ratio),
                    'type': 'VOL_COMPRESSION',
                    'action': 'PREPARE_FOR_BREAKOUT'
                })
                
        return anomalies
    
    def get_anomaly_signal(self, prices_df, returns_df, target_asset):
        """
        Generate signal from anomaly detection
        """
        signals = []
        
        # Pair anomalies involving target
        pair_anomalies = self.scan_pair_anomalies(prices_df)
        for anom in pair_anomalies:
            if target_asset in anom['pair']:
                if anom['action'] == 'LONG_S1_SHORT_S2':
                    sig = 0.5 if anom['pair'][0] == target_asset else -0.5
                else:
                    sig = -0.5 if anom['pair'][0] == target_asset else 0.5
                signals.append(sig * min(abs(anom['z_score']) / 3, 1))
                
        # Momentum anomaly
        mom_anomalies = self.detect_momentum_anomaly(returns_df)
        for anom in mom_anomalies:
            if anom['asset'] == target_asset:
                # Mean reversion: fade extreme momentum
                sig = -0.3 if anom['type'] == 'MOMENTUM_WINNER' else 0.3
                signals.append(sig)
                
        # Volatility anomaly
        vol_anomalies = self.detect_volatility_anomaly(returns_df)
        for anom in vol_anomalies:
            if anom['asset'] == target_asset:
                if anom['type'] == 'VOL_SPIKE':
                    signals.append(-0.2)  # Reduce in high vol
                    
        if not signals:
            return {'signal': 0, 'confidence': 0.5, 'anomalies': []}
            
        composite = np.mean(signals)
        confidence = min(len(signals) * 0.2 + 0.3, 1.0)
        
        return {
            'signal': float(composite),
            'confidence': float(confidence),
            'n_anomalies': len(signals),
            'pair_anomalies': [a for a in pair_anomalies if target_asset in a['pair']],
            'momentum_anomalies': [a for a in mom_anomalies if a['asset'] == target_asset],
            'vol_anomalies': [a for a in vol_anomalies if a['asset'] == target_asset]
        }
