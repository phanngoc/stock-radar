#!/bin/bash

# Script to setup and run Stock Prediction App

set -e

echo "🚀 Stock Prediction App - Setup & Run"
echo "======================================"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Check if dependencies are installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -e .
else
    echo "✅ Dependencies already installed"
fi

# Run the app
echo "🎯 Starting Streamlit app..."
echo "📍 Access at: http://localhost:8501"
echo ""
streamlit run app.py
