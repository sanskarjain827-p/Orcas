#!/bin/bash
set -e

echo "🐋 Orcas - Global Installation Script"
echo "--------------------------------------"

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed."
    exit 1
fi

# 2. Check for dependencies
echo "📦 Installing Python dependencies..."
pip3 install .

# 3. Handle Static Assets
if [ ! -d "brain/static" ]; then
    echo "⚠️  Static UI files not found in brain/static."
    if command -v npm &> /dev/null; then
        echo "🔨 Building UI from source (requires Node.js)..."
        cd cli && npm install && npm run build && cd ..
        mkdir -p brain/static
        cp -r cli/build/* brain/static/
    fi
fi

echo "--------------------------------------"
echo "✅ Orcas installed successfully!"
echo "🚀 Try running: orcas"
