#!/bin/bash
# Helper script to update frontend dependencies and lock file

set -e

echo "📦 Updating Frontend Dependencies"
echo "=================================="

cd frontend

echo ""
echo "Running npm install to update package-lock.json..."
npm install

echo ""
echo "✅ Dependencies updated!"
echo ""
echo "⚠️  Don't forget to commit both package.json and package-lock.json:"
echo "   git add frontend/package.json frontend/package-lock.json"
echo "   git commit -m 'Update frontend dependencies'"
