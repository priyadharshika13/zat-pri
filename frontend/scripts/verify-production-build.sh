#!/bin/bash
# Production build verification script
# Verifies that the production build completes successfully and has no errors

set -e

echo "🔨 Building production bundle..."
npm run build

echo "✅ Build completed successfully"

echo "📦 Checking build output..."
if [ ! -d "dist" ]; then
  echo "❌ Error: dist directory not found"
  exit 1
fi

echo "✅ Build output directory exists"

echo "🔍 Verifying critical files..."
if [ ! -f "dist/index.html" ]; then
  echo "❌ Error: index.html not found in dist"
  exit 1
fi

echo "✅ index.html found"

echo "📊 Build size check..."
BUILD_SIZE=$(du -sh dist | cut -f1)
echo "Build size: $BUILD_SIZE"

echo "✅ Production build verification complete!"

