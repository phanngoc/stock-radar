"""NLinear Model for time-series forecasting"""
import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler


class NLinear(nn.Module):
    """Normalization-Linear model for time-series prediction"""
    def __init__(self, seq_len, pred_len):
        super().__init__()
        self.linear = nn.Linear(seq_len, pred_len)
    
    def forward(self, x):
        seq_last = x[:, -1:, :].detach()
        x = x - seq_last
        x = self.linear(x.permute(0, 2, 1)).permute(0, 2, 1)
        return x + seq_last


class NLinearModel:
    """
    NLinear wrapper for trading signal generation.
    Uses normalization-linear approach for trend prediction.
    """
    
    def __init__(self, seq_len=60, epochs=50, lr=0.001):
        self.seq_len = seq_len
        self.epochs = epochs
        self.lr = lr
        self.scaler = MinMaxScaler()
        
    def _create_dataset(self, data, pred_len):
        """Create training sequences"""
        X, y = [], []
        for i in range(len(data) - self.seq_len - pred_len + 1):
            X.append(data[i:i + self.seq_len])
            y.append(data[i + self.seq_len:i + self.seq_len + pred_len])
        return torch.FloatTensor(np.array(X)), torch.FloatTensor(np.array(y))
    
    def _train(self, model, X, y):
        """Train model"""
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=self.lr)
        
        for _ in range(self.epochs):
            model.train()
            optimizer.zero_grad()
            output = model(X)
            loss = criterion(output, y)
            loss.backward()
            optimizer.step()
        return model
    
    def get_signal(self, prices, pred_days=5):
        """
        Generate trading signal from NLinear prediction.
        
        Returns:
            dict: {
                'signal': float [-1, 1],
                'direction': int (1/-1/0),
                'confidence': float [0, 1],
                'forecast': np.array,
                'pct_change': float
            }
        """
        try:
            prices = np.array(prices).flatten().reshape(-1, 1)
            
            if len(prices) < self.seq_len + pred_days:
                return self._default_signal()
            
            # Scale data
            scaled = self.scaler.fit_transform(prices)
            
            # Create dataset and train
            X, y = self._create_dataset(scaled, pred_days)
            if len(X) < 10:
                return self._default_signal()
            
            model = NLinear(self.seq_len, pred_days)
            model = self._train(model, X, y)
            
            # Predict
            model.eval()
            with torch.no_grad():
                last_seq = torch.FloatTensor(scaled[-self.seq_len:]).unsqueeze(0)
                pred_scaled = model(last_seq).squeeze().numpy()
            
            forecast = self.scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
            
            # Calculate signal
            current = prices[-1, 0]
            future = forecast[-1]
            pct_change = (future - current) / current
            
            # Direction
            if pct_change > 0.01:
                direction = 1
            elif pct_change < -0.01:
                direction = -1
            else:
                direction = 0
            
            # Confidence based on trend consistency
            trend_changes = np.diff(forecast)
            consistency = np.mean(np.sign(trend_changes) == np.sign(pct_change)) if len(trend_changes) > 0 else 0.5
            confidence = min(0.5 + consistency * 0.5, 1.0)
            
            # Signal = direction * confidence * magnitude
            signal = np.clip(pct_change * 10, -1, 1) * confidence
            
            return {
                'signal': float(signal),
                'direction': direction,
                'confidence': float(confidence),
                'forecast': forecast,
                'pct_change': float(pct_change)
            }
            
        except Exception:
            return self._default_signal()
    
    def _default_signal(self):
        """Return neutral signal on error"""
        return {
            'signal': 0.0,
            'direction': 0,
            'confidence': 0.0,
            'forecast': np.array([]),
            'pct_change': 0.0
        }
