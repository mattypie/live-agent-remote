#!/usr/bin/env python3
"""
Audio Analyzer for LiveAgent
=============================
Analyzes audio files for BPM and musical key using librosa.

Designed to work with LiveAgent's auto-warp feature:
1. Detect BPM → set clip warp tempo
2. Detect key → set clip name with key info
3. Auto-generate warp markers based on beat positions

Usage:
    from audio_analyzer import AudioAnalyzer
    result = AudioAnalyzer.analyze("/path/to/file.wav")
    # {"bpm": 128.5, "key": "Fm", "beat_positions": [0.0, 0.468, ...]}
"""

import numpy as np

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False


class AudioAnalyzer:
    """Analyze audio files for tempo, key, and beat positions."""

    # Key mapping: chroma index → key name
    KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    # Krumhansl-Schmuckler key profiles (major and minor)
    MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

    @staticmethod
    def analyze(file_path, sample_rate=22050):
        """
        Full analysis of an audio file.

        Returns:
            dict with bpm, key, confidence, duration, beat_positions, beat_count
        """
        if not HAS_LIBROSA:
            return {"error": "librosa not installed. Run: pip install librosa"}

        # Load audio
        y, sr = librosa.load(file_path, sr=sample_rate)
        duration = float(len(y) / sr)

        # BPM detection
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo[0]) if len(tempo) > 0 else 0.0
        else:
            tempo = float(tempo)

        # Beat positions in seconds
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        # Key detection
        key_result = AudioAnalyzer._detect_key(y, sr)

        return {
            "file": file_path,
            "bpm": round(tempo, 2),
            "key": key_result["key"],
            "key_confidence": round(key_result["confidence"], 3),
            "key_mode": key_result["mode"],
            "duration_seconds": round(duration, 3),
            "beat_positions": [round(t, 4) for t in beat_times],
            "beat_count": len(beat_times),
            "sample_rate": sr,
        }

    @staticmethod
    def detect_bpm(file_path):
        """Quick BPM detection only."""
        if not HAS_LIBROSA:
            return {"error": "librosa not installed"}

        y, sr = librosa.load(file_path, sr=22050)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo[0]) if len(tempo) > 0 else 0.0
        else:
            tempo = float(tempo)
        return {"bpm": round(tempo, 2)}

    @staticmethod
    def detect_key(file_path):
        """Quick key detection only."""
        if not HAS_LIBROSA:
            return {"error": "librosa not installed"}

        y, sr = librosa.load(file_path, sr=22050)
        return AudioAnalyzer._detect_key(y, sr)

    @staticmethod
    def _detect_key(y, sr):
        """
        Detect musical key using Krumhansl-Schmuckler algorithm.

        Analyzes chromagram and correlates against major/minor profiles
        for all 24 keys (12 major + 12 minor).
        """
        # Get chromagram
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)

        # Average chroma across all frames
        chroma_avg = np.mean(chroma, axis=1)

        # Normalize
        chroma_norm = chroma_avg / (np.sum(chroma_avg) + 1e-10)

        # Correlate with all 24 key profiles
        best_corr = -1
        best_key = "C"
        best_mode = "major"

        major_profile = np.array(AudioAnalyzer.MAJOR_PROFILE)
        minor_profile = np.array(AudioAnalyzer.MINOR_PROFILE)

        # Normalize profiles
        major_norm = major_profile / np.sum(major_profile)
        minor_norm = minor_profile / np.sum(minor_profile)

        for i in range(12):
            # Rotate profile
            major_rot = np.roll(major_norm, i)
            minor_rot = np.roll(minor_norm, i)

            # Pearson correlation
            major_corr = np.corrcoef(chroma_norm, major_rot)[0, 1]
            minor_corr = np.corrcoef(chroma_norm, minor_rot)[0, 1]

            if major_corr > best_corr:
                best_corr = major_corr
                best_key = AudioAnalyzer.KEY_NAMES[i]
                best_mode = "major"

            if minor_corr > best_corr:
                best_corr = minor_corr
                best_key = AudioAnalyzer.KEY_NAMES[i]
                best_mode = "minor"

        key_name = best_key if best_mode == "major" else best_key + "m"

        return {
            "key": key_name,
            "root": best_key,
            "mode": best_mode,
            "confidence": float(best_corr),
        }

    @staticmethod
    def get_warp_data(file_path, target_bpm=None):
        """
        Analyze audio and return warp-relevant data.

        If target_bpm is provided, calculates the stretch ratio needed
        to match the target tempo.
        """
        result = AudioAnalyzer.analyze(file_path)
        if "error" in result:
            return result

        detected_bpm = result["bpm"]

        if target_bpm and detected_bpm > 0:
            stretch_ratio = detected_bpm / target_bpm
            result["target_bpm"] = target_bpm
            result["stretch_ratio"] = round(stretch_ratio, 4)
            result["warp_needed"] = abs(stretch_ratio - 1.0) > 0.005

        # Calculate beat grid in beats (assuming detected BPM)
        if result["beat_positions"] and detected_bpm > 0:
            beat_duration = 60.0 / detected_bpm
            # Convert beat positions (seconds) to beat numbers
            result["beat_grid"] = [
                round(t / beat_duration, 4) for t in result["beat_positions"]
            ]

        return result


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python audio_analyzer.py <audio_file> [--bpm-only] [--key-only]")
        sys.exit(1)

    file_path = sys.argv[1]

    if "--bpm-only" in sys.argv:
        result = AudioAnalyzer.detect_bpm(file_path)
    elif "--key-only" in sys.argv:
        result = AudioAnalyzer.detect_key(file_path)
    else:
        result = AudioAnalyzer.analyze(file_path)

    print(json.dumps(result, indent=2, ensure_ascii=False))
