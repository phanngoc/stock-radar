"""
Stock Radar - Unified Application.
Multi-page Streamlit app combining Trading Analysis and News Chatbot.

Features:
- 📈 Trading Analysis: 5-Module signal system for Vietnam stocks
- 💬 News Chat: RAG-based Q&A with financial news
- 📰 News Info: Browse and preview news data

Usage:
    streamlit run app.py --server.port 8501
"""
import streamlit as st

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="Stock Radar",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import page modules
from pages import trading_page, chat_page, info_page


def main():
    """Main application with tab-based navigation."""
    
    # App header
    st.title("📊 Stock Radar")
    st.caption("Vietnam Stock Analysis & News Intelligence")
    
    # Create tabs for navigation
    tab1, tab2, tab3 = st.tabs([
        "📈 Trading Analysis",
        "💬 News Chat",
        "📰 News Info"
    ])
    
    # Render content based on selected tab
    with tab1:
        trading_page.render()
    
    with tab2:
        chat_page.render()
    
    with tab3:
        info_page.render()


if __name__ == "__main__":
    main()
