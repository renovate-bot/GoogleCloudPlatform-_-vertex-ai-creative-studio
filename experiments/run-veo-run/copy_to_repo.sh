#!/bin/bash
SOURCE="/Users/ghchinoy/projects/run-veo-run"
DEST="/Users/ghchinoy/dev/vertex-ai-creative-studio-public/experiments/run-veo-run"

echo "Copying from $SOURCE to $DEST..."

mkdir -p "$DEST"

rsync -av \
  --exclude ".git" \
  --exclude ".beads" \
  --exclude ".genkit" \
  --exclude "node_modules" \
  --exclude "dist" \
  --exclude "server/server" \
  --exclude "*.log" \
  --exclude ".env" \
  --exclude ".DS_Store" \
  --exclude "tmp" \
  --exclude "drivectl-mcp.log" \
  "$SOURCE/" "$DEST/"

echo "✅ Copy complete."
echo "⚠️  REMINDER: Check server/go.mod if you need to update the module path."

