#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
  echo "⚠️  No .env file found. Copy .env.example and add your keys:"
  echo "    cp .env.example .env"
  exit 1
fi

if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "📦 Installing dependencies..."
  pip install -r requirements.txt -q
fi

echo "🚀 TKS Signal Engine starting at http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
