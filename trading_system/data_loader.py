"""Data Loader - vnstock integration"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional
import warnings
warnings.filterwarnings('ignore')


class VNStockLoader:
    """Load Vietnam stock data using vnstock"""
    
    def __init__(self, source='VCI'):
        self.source = source
        self._vnstock = None
        
    @property
    def vnstock(self):
        if self._vnstock is None:
            from vnstock import Vnstock
            self._vnstock = Vnstock()
        return self._vnstock
    
    def load_single(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """Load single stock data"""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        stock = self.vnstock.stock(symbol=symbol, source=self.source)
        df = stock.quote.history(start=start_date, end=end_date, interval='1D')
        
        if df is not None and len(df) > 0:
            df = df.rename(columns={'time': 'date'})
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            
        return df
    
    def load_multiple(self, symbols: List[str], days: int = 365) -> pd.DataFrame:
        """Load multiple stocks, return close prices DataFrame"""
        prices = {}
        
        for symbol in symbols:
            try:
                df = self.load_single(symbol, days)
                if df is not None and len(df) > 0:
                    prices[symbol] = df['close']
                    print(f"✓ Loaded {symbol}: {len(df)} rows")
            except Exception as e:
                print(f"✗ Failed {symbol}: {e}")
                
        if not prices:
            return pd.DataFrame()
            
        # Combine and align dates
        result = pd.DataFrame(prices)
        result = result.dropna()
        
        return result
    
    def get_returns(self, prices_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate returns from prices"""
        return prices_df.pct_change().dropna()


# Popular VN stocks for testing
VN30_SYMBOLS = [
    'VNM', 'FPT', 'VIC', 'VHM', 'HPG',
    'MSN', 'VCB', 'BID', 'CTG', 'TCB',
    'MBB', 'VPB', 'ACB', 'GAS', 'SAB',
    'PLX', 'VRE', 'NVL', 'MWG', 'POW'
]

BLUECHIP_SYMBOLS = ['VNM', 'FPT', 'VIC', 'VHM', 'HPG', 'MWG', 'PNJ', 'REE']


def load_vn_data(symbols: List[str] = None, days: int = 365) -> pd.DataFrame:
    """Quick function to load VN stock data"""
    symbols = symbols or BLUECHIP_SYMBOLS[:5]
    loader = VNStockLoader()
    return loader.load_multiple(symbols, days)
