#!/bin/bash
# LiveAgent Remote Setup
# =====================
# Run this after cloning the repository.

set -e
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== LiveAgent Remote Setup ==="
echo ""

# 1. Create virtual environment
if [ ! -d "$REPO_DIR/.venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv "$REPO_DIR/.venv"
else
    echo "[1/4] Virtual environment already exists."
fi

# 2. Install dependencies
echo "[2/4] Installing dependencies..."
"$REPO_DIR/.venv/bin/pip" install --quiet "mcp[cli]" librosa

# 3. Create config
if [ ! -f "$REPO_DIR/config.local.py" ]; then
    echo "[3/4] Creating config.local.py..."
    cp "$REPO_DIR/config.example.py" "$REPO_DIR/config.local.py"
    echo ""
    echo "  >> Edit config.local.py and set SAMPLES_PATH to your sample library:"
    echo "     nano $REPO_DIR/config.local.py"
    echo ""
else
    echo "[3/4] config.local.py already exists."
fi

# 4. Install LiveAgent Control Surface
ABLETON_CS_DIR=""
for dir in "/Applications/Ableton Live 11 Standard.app" \
           "/Applications/Ableton Live 11 Suite.app" \
           "/Applications/Ableton Live 12 Standard.app" \
           "/Applications/Ableton Live 12 Suite.app" \
           "/Applications/Ableton Live 11 Intro.app"; do
    if [ -d "$dir" ]; then
        ABLETON_CS_DIR="$dir/Contents/App-Resources/MIDI Remote Scripts"
        break
    fi
done

if [ -n "$ABLETON_CS_DIR" ]; then
    echo "[4/4] Installing LiveAgent Control Surface..."
    mkdir -p "$ABLETON_CS_DIR/LiveAgent"
    cp "$REPO_DIR/LiveAgent/LiveAgent.py" "$ABLETON_CS_DIR/LiveAgent/"
    cp "$REPO_DIR/LiveAgent/__init__.py" "$ABLETON_CS_DIR/LiveAgent/" 2>/dev/null || true
    echo "  Installed to: $ABLETON_CS_DIR/LiveAgent/"
    echo ""
    echo "  >> Enable in Ableton: Settings > Link/Tempo > Control Surface > LiveAgent"
else
    echo "[4/4] Ableton not found. Copy LiveAgent/ manually to:"
    echo "     <Ableton.app>/Contents/App-Resources/MIDI Remote Scripts/"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit config.local.py — set SAMPLES_PATH"
echo "  2. Restart Ableton Live — enable LiveAgent control surface"
echo "  3. Build cache: .venv/bin/python3 batch_analyze.py"
echo "  4. Start MCP:   .venv/bin/python3 mcp_server.py"
