#!/usr/bin/env python3
"""Batch analyze all NI Samples — builds persistent cache for instant queries."""

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio_analyzer import AudioAnalyzer, AnalysisCache

BASE = "/Users/mtsh/書類/Ableton Live/NI Samples"
EXTENSIONS = {'.wav', '.aif', '.aiff', '.mp3', '.flac', '.ogg', '.m4a'}

def collect_files(category=None):
    """Collect all audio files, optionally filtered by category."""
    files = []
    if category:
        cats = [category]
    else:
        cats = sorted([d for d in os.listdir(BASE) 
                       if os.path.isdir(os.path.join(BASE, d)) and d != "_smart"])
    
    for cat in cats:
        cat_path = os.path.join(BASE, cat)
        if not os.path.isdir(cat_path):
            continue
        for root, dirs, fnames in os.walk(cat_path):
            for f in fnames:
                ext = os.path.splitext(f)[1].lower()
                if ext in EXTENSIONS:
                    files.append(os.path.join(root, f))
    return files

def analyze_batch(files, analysis_type="pitch"):
    """Analyze files with cache, skipping already-cached ones."""
    # Check what's already cached
    total = len(files)
    to_analyze = []
    for fp in files:
        cached = AnalysisCache.get(fp, analysis_type)
        if cached is None:
            to_analyze.append(fp)
    
    print(f"Total: {total}, Cached: {total - len(to_analyze)}, To analyze: {len(to_analyze)}")
    
    done = total - len(to_analyze)
    errors = 0
    t_start = time.time()
    
    for i, fp in enumerate(to_analyze):
        try:
            result = AudioAnalyzer.detect_pitch(fp)
            if "error" in result:
                errors += 1
            done += 1
        except Exception as e:
            errors += 1
            done += 1
        
        # Progress every 100 files
        if (i + 1) % 100 == 0 or i == len(to_analyze) - 1:
            elapsed = time.time() - t_start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (len(to_analyze) - i - 1) / rate if rate > 0 else 0
            pct = done / total * 100
            print(f"[{pct:.1f}%] {done}/{total} done | {rate:.1f} files/s | ETA: {remaining/60:.1f}min | errors: {errors}")
    
    elapsed = time.time() - t_start
    print(f"\nDone! {done}/{total} in {elapsed:.1f}s ({errors} errors)")
    
    cache_stats = AnalysisCache.stats()
    print(f"Cache: {cache_stats['files']} files, {cache_stats['size_mb']} MB")

if __name__ == "__main__":
    category = sys.argv[1] if len(sys.argv) > 1 else None
    files = collect_files(category)
    print(f"Analyzing {len(files)} files" + (f" [{category}]" if category else " [ALL]"))
    analyze_batch(files)
