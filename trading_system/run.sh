#!/bin/bash
# Run the unified Stock Radar application
# Combines Trading Analysis and News Chatbot

cd "$(dirname "$0")"

echo "📊 Starting Stock Radar..."
echo "📂 Working directory: $(pwd)"
echo ""

# Activate virtual environment
if [ -d "../myenv" ]; then
    source ../myenv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Warning: Virtual environment not found at ../myenv"
    echo "   Using system Python"
fi

# Check if .env exists for chatbot features
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  Note: .env file not found!"
    echo "   News Chat features require OPENAI_API_KEY in .env"
    echo "   Trading features will work without it."
    echo ""
fi

echo ""
echo "🚀 Starting Streamlit app on port 8501..."
echo "   URL: http://localhost:8501"
echo ""

# Run unified app
streamlit run app.py --server.port 8501
