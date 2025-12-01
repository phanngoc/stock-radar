"""Hidden Markov Model for Market Regime Detection"""
import numpy as np
from hmmlearn import hmm
import warnings
warnings.filterwarnings('ignore')


class HMMRegimeDetector:
    """
    HMM để detect market regimes:
    - State 0: Bear (downtrend, high vol)
    - State 1: Sideways (no trend, low vol)  
    - State 2: Bull (uptrend, moderate vol)
    
    Trading implication:
    - Bull: Long positions, higher allocation
    - Bear: Cash/Short, reduce exposure
    - Sideways: Mean reversion strategies
    """
    
    REGIMES = {0: 'BEAR', 1: 'SIDEWAYS', 2: 'BULL'}
    
    def __init__(self, n_states=3, n_iter=100):
        self.n_states = n_states
        self.model = hmm.GaussianHMM(
            n_components=n_states,
            covariance_type="full",
            n_iter=n_iter,
            random_state=42
        )
        self.fitted = False
        
    def _prepare_features(self, prices, window=20):
        """
        Tạo features cho HMM:
        - Returns
        - Volatility (rolling std)
        """
        prices = np.array(prices).flatten()
        returns = np.diff(prices) / prices[:-1]
        
        # Rolling volatility
        vol = np.array([
            np.std(returns[max(0, i-window):i+1]) 
            for i in range(len(returns))
        ])
        
        # Stack features
        features = np.column_stack([returns, vol])
        return features
    
    def fit(self, prices):
        """Fit HMM on historical prices"""
        features = self._prepare_features(prices)
        self.model.fit(features)
        self.fitted = True
        
        # Sort states by mean return (Bear < Sideways < Bull)
        means = self.model.means_[:, 0]  # Return means
        self.state_order = np.argsort(means)
        
        return self
    
    def predict_regime(self, prices):
        """
        Predict current regime
        Returns:
            dict: {
                'regime': int (0=Bear, 1=Sideways, 2=Bull),
                'regime_name': str,
                'probabilities': array of state probabilities,
                'history': array of historical regimes
            }
        """
        if not self.fitted:
            self.fit(prices)
            
        features = self._prepare_features(prices)
        
        # Predict states
        states = self.model.predict(features)
        probs = self.model.predict_proba(features)
        
        # Map to ordered states
        mapped_states = np.array([
            np.where(self.state_order == s)[0][0] for s in states
        ])
        
        current_state = mapped_states[-1]
        current_probs = probs[-1][self.state_order]
        
        return {
            'regime': int(current_state),
            'regime_name': self.REGIMES[current_state],
            'probabilities': current_probs,
            'history': mapped_states
        }
    
    def get_signal(self, prices):
        """
        Generate trading signal từ regime
        - Bull: +1 (full long)
        - Sideways: 0 (neutral/mean reversion)
        - Bear: -1 (cash/short)
        
        Signal strength = probability of current regime
        """
        result = self.predict_regime(prices)
        
        regime = result['regime']
        prob = result['probabilities'][regime]
        
        # Map regime to signal
        if regime == 2:  # Bull
            base_signal = 1.0
        elif regime == 0:  # Bear
            base_signal = -1.0
        else:  # Sideways
            base_signal = 0.0
            
        signal = base_signal * prob
        
        # Regime transition detection
        history = result['history']
        if len(history) >= 5:
            recent = history[-5:]
            if recent[-1] != recent[-2]:  # Regime just changed
                transition = 'REGIME_CHANGE'
            else:
                transition = 'STABLE'
        else:
            transition = 'INSUFFICIENT_DATA'
            
        return {
            'signal': signal,
            'regime': regime,
            'regime_name': result['regime_name'],
            'confidence': prob,
            'transition': transition,
            'probabilities': {
                'bear': result['probabilities'][0],
                'sideways': result['probabilities'][1],
                'bull': result['probabilities'][2]
            }
        }
    
    def get_regime_stats(self, prices):
        """Thống kê về các regime"""
        result = self.predict_regime(prices)
        history = result['history']
        
        stats = {}
        for i, name in self.REGIMES.items():
            mask = history == i
            stats[name] = {
                'count': int(np.sum(mask)),
                'pct': float(np.mean(mask)),
                'avg_duration': self._avg_duration(history, i)
            }
        return stats
    
    def _avg_duration(self, history, state):
        """Tính average duration của một state"""
        durations = []
        count = 0
        for s in history:
            if s == state:
                count += 1
            elif count > 0:
                durations.append(count)
                count = 0
        if count > 0:
            durations.append(count)
        return np.mean(durations) if durations else 0
