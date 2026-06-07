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
import os
import json
import hashlib

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False

# Cache directory for analysis results
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".analysis_cache")


class AnalysisCache:
    """Persistent JSON cache for audio analysis results."""

    @staticmethod
    def _file_hash(file_path):
        """Generate a cache key from file path + mtime + size."""
        try:
            stat = os.stat(file_path)
            raw = "%s|%s|%s" % (file_path, stat.st_mtime, stat.st_size)
            return hashlib.md5(raw.encode()).hexdigest()
        except OSError:
            return hashlib.md5(file_path.encode()).hexdigest()

    @staticmethod
    def get(file_path, analysis_type="pitch"):
        """Get cached result if available and valid."""
        key = AnalysisCache._file_hash(file_path)
        cache_file = os.path.join(CACHE_DIR, "%s_%s.json" % (key, analysis_type))
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                # Verify the file hasn't changed
                if data.get("_src") == os.path.basename(file_path):
                    return data.get("result")
            except (json.JSONDecodeError, IOError):
                pass
        return None

    @staticmethod
    def set(file_path, analysis_type, result):
        """Save analysis result to cache."""
        os.makedirs(CACHE_DIR, exist_ok=True)
        key = AnalysisCache._file_hash(file_path)
        cache_file = os.path.join(CACHE_DIR, "%s_%s.json" % (key, analysis_type))
        try:
            with open(cache_file, "w") as f:
                json.dump({"_src": os.path.basename(file_path), "result": result}, f)
        except IOError:
            pass

    @staticmethod
    def batch_get(file_paths, analysis_type="pitch"):
        """Get multiple cached results. Returns {path: result} for hits."""
        hits = {}
        for fp in file_paths:
            cached = AnalysisCache.get(fp, analysis_type)
            if cached is not None:
                hits[fp] = cached
        return hits

    @staticmethod
    def stats():
        """Return cache statistics."""
        if not os.path.exists(CACHE_DIR):
            return {"files": 0, "size_mb": 0}
        files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".json")]
        total_size = sum(os.path.getsize(os.path.join(CACHE_DIR, f)) for f in files)
        return {"files": len(files), "size_mb": round(total_size / 1048576, 2)}

    @staticmethod
    def clear():
        """Clear all cached results."""
        if os.path.exists(CACHE_DIR):
            for f in os.listdir(CACHE_DIR):
                if f.endswith(".json"):
                    os.remove(os.path.join(CACHE_DIR, f))


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

        # Check cache
        cached = AnalysisCache.get(file_path, "full")
        if cached is not None:
            return cached

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

        # Save to cache
        AnalysisCache.set(file_path, "full", result)
        return result

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

    # ── One-Shot Pitch Detection ────────────────────────────

    @staticmethod
    def detect_pitch(file_path):
        """Detect the fundamental pitch of a one-shot sample (kick, snare, etc).

        Returns the dominant frequency and its closest musical note.
        """
        if not HAS_LIBROSA:
            return {"error": "librosa not installed"}

        # Check cache
        cached = AnalysisCache.get(file_path, "pitch")
        if cached is not None:
            return cached

        y, sr = librosa.load(file_path, sr=22050)

        # Use pyin for monophonic pitch detection
        f0, voiced_flags, voiced_probs = librosa.pyin(
            y, fmin=20, fmax=2000, sr=sr
        )

        # Filter out NaN values
        valid_f0 = f0[~np.isnan(f0)]

        if len(valid_f0) == 0:
            # No clear pitch — likely atonal/noise (some snares, hats)
            # Fallback: use spectral centroid
            centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            avg_centroid = float(np.mean(centroid))
            note_info = AudioAnalyzer._freq_to_note(avg_centroid)
            result = {
                "pitch": note_info["note"],
                "frequency": round(avg_centroid, 2),
                "note_number": note_info["note_number"],
                "octave": note_info["octave"],
                "confidence": 0.0,
                "is_atonal": True,
                "type": "noise/atonal",
            }
            AnalysisCache.set(file_path, "pitch", result)
            return result

        # Weighted average pitch (weight by probability)
        valid_probs = voiced_probs[~np.isnan(f0)]
        if len(valid_probs) == len(valid_f0):
            weights = valid_probs
        else:
            weights = np.ones(len(valid_f0))
        weights = weights / (np.sum(weights) + 1e-10)

        avg_freq = float(np.average(valid_f0, weights=weights))
        median_freq = float(np.median(valid_f0))

        # Use the most common pitch (mode-like)
        # Bin into note ranges and find the most frequent
        note_counts = {}
        for freq in valid_f0:
            n = AudioAnalyzer._freq_to_note(freq)
            key = n["note"]
            note_counts[key] = note_counts.get(key, 0) + 1

        dominant_note = max(note_counts, key=note_counts.get)
        confidence = note_counts[dominant_note] / len(valid_f0)

        note_info = AudioAnalyzer._freq_to_note(median_freq)

        result = {
            "pitch": dominant_note,
            "frequency": round(median_freq, 2),
            "note_number": note_info["note_number"],
            "octave": note_info["octave"],
            "confidence": round(confidence, 3),
            "is_atonal": False,
            "type": "tonal",
        }
        AnalysisCache.set(file_path, "pitch", result)
        return result

    @staticmethod
    def _freq_to_note(freq):
        """Convert frequency to closest musical note."""
        if freq <= 0:
            return {"note": "C1", "note_number": 24, "octave": 1, "cents_off": 0}

        # MIDI note number from frequency
        note_number = 12 * np.log2(freq / 440.0) + 69
        note_number_rounded = int(round(note_number))
        cents_off = int((note_number - note_number_rounded) * 100)

        octave = (note_number_rounded // 12) - 1
        note_idx = note_number_rounded % 12
        note_name = AudioAnalyzer.KEY_NAMES[note_idx]

        return {
            "note": "%s%d" % (note_name, octave),
            "note_number": note_number_rounded,
            "octave": octave,
            "cents_off": cents_off,
        }

    # ── Camelot Wheel ───────────────────────────────────────

    CAMELOT_MAP = {
        # Minor keys
        "Am": "8A", "A#m": "8A", "Bbm": "8A",
        "Bm": "7A",
        "Cm": "5A",
        "C#m": "12A", "Dbm": "12A",
        "Dm": "7A",
        "D#m": "2A", "Ebm": "2A",
        "Em": "9A",
        "Fm": "4A",
        "F#m": "11A", "Gbm": "11A",
        "Gm": "6A",
        "G#m": "1A", "Abm": "1A",
        # Major keys
        "A": "11B",
        "A#": "6B", "Bb": "6B",
        "B": "1B",
        "C": "8B",
        "C#": "3B", "Db": "3B",
        "D": "10B",
        "D#": "5B", "Eb": "5B",
        "E": "12B",
        "F": "7B",
        "F#": "2B", "Gb": "2B",
        "G": "9B",
        "G#": "4B", "Ab": "4B",
    }

    CAMELOT_COMPATIBLE = {
        # Same key, +1, -1 on same letter (A↔A, B↔B)
        "1A": ["1A", "2A", "12A", "1B"],
        "2A": ["2A", "3A", "1A", "2B"],
        "3A": ["3A", "4A", "2A", "3B"],
        "4A": ["4A", "5A", "3A", "4B"],
        "5A": ["5A", "6A", "4A", "5B"],
        "6A": ["6A", "7A", "5A", "6B"],
        "7A": ["7A", "8A", "6A", "7B"],
        "8A": ["8A", "9A", "7A", "8B"],
        "9A": ["9A", "10A", "8A", "9B"],
        "10A": ["10A", "11A", "9A", "10B"],
        "11A": ["11A", "12A", "10A", "11B"],
        "12A": ["12A", "1A", "11A", "12B"],
        "1B": ["1B", "2B", "12B", "1A"],
        "2B": ["2B", "3B", "1B", "2A"],
        "3B": ["3B", "4B", "2B", "3A"],
        "4B": ["4B", "5B", "3B", "4A"],
        "5B": ["5B", "6B", "4B", "5A"],
        "6B": ["6B", "7B", "5B", "6A"],
        "7B": ["7B", "8B", "6B", "7A"],
        "8B": ["8B", "9B", "7B", "8A"],
        "9B": ["9B", "10B", "8B", "9A"],
        "10B": ["10B", "11B", "9B", "10A"],
        "11B": ["11B", "12B", "10B", "11A"],
        "12B": ["12B", "1B", "11B", "12A"],
    }

    @staticmethod
    def get_camelot(key):
        """Get Camelot Wheel notation for a key."""
        return AudioAnalyzer.CAMELOT_MAP.get(key, "??")

    @staticmethod
    def is_harmonically_compatible(key1, key2):
        """Check if two keys are compatible on the Camelot Wheel."""
        c1 = AudioAnalyzer.get_camelot(key1)
        c2 = AudioAnalyzer.get_camelot(key2)
        if c1 == "??" or c2 == "??":
            return False
        return c2 in AudioAnalyzer.CAMELOT_COMPATIBLE.get(c1, [])

    # ── Batch Analysis ──────────────────────────────────────

    @staticmethod
    def analyze_folder(folder_path, mode="full"):
        """Analyze all audio files in a folder.

        Args:
            folder_path: Path to folder
            mode: 'full' (BPM+key+pitch), 'pitch' (pitch only), 'key' (key only), 'bpm' (BPM only)

        Returns:
            List of analysis results, sorted by pitch/note number
        """
        import os

        extensions = {".wav", ".aif", ".aiff", ".mp3", ".flac", ".ogg", ".m4a"}
        results = []

        for item in sorted(os.listdir(folder_path)):
            ext = os.path.splitext(item)[1].lower()
            if ext not in extensions:
                continue

            file_path = os.path.join(folder_path, item)
            try:
                if mode == "pitch":
                    r = AudioAnalyzer.detect_pitch(file_path)
                    r["file"] = item
                elif mode == "key":
                    r = AudioAnalyzer.detect_key(file_path)
                    r["file"] = item
                elif mode == "bpm":
                    r = AudioAnalyzer.detect_bpm(file_path)
                    r["file"] = item
                else:
                    r = AudioAnalyzer.analyze(file_path)
                    # Also add pitch for one-shots
                    pitch = AudioAnalyzer.detect_pitch(file_path)
                    r["pitch"] = pitch.get("pitch", "?")
                    r["note_number"] = pitch.get("note_number", 0)
                    r["is_atonal"] = pitch.get("is_atonal", False)
                    r["camelot"] = AudioAnalyzer.get_camelot(r.get("key", ""))
                    r["file"] = item

                results.append(r)
            except Exception as e:
                results.append({"file": item, "error": str(e)})

        # Sort by note_number (pitch ascending)
        if mode in ("full", "pitch"):
            results.sort(key=lambda x: x.get("note_number", 999))

        return results

    @staticmethod
    def find_compatible_samples(folder_path, target_key, mode="full"):
        """Find samples in a folder that are harmonically compatible with a target key.

        Uses Camelot Wheel matching.
        """
        results = AudioAnalyzer.analyze_folder(folder_path, mode=mode)
        compatible = []
        incompatible = []

        for r in results:
            if "error" in r:
                continue
            sample_key = r.get("key", "")
            if not sample_key:
                # Use pitch as key for one-shots
                pitch = r.get("pitch", "")
                if pitch and len(pitch) > 1:
                    # e.g. "F2" -> "F" -> check compatibility
                    root = pitch[:-1]
                    sample_key = root + "m"  # assume minor for drums
                    r["assumed_key"] = sample_key

            if sample_key:
                is_compat = AudioAnalyzer.is_harmonically_compatible(target_key, sample_key)
                r["compatible_with"] = target_key
                r["is_compatible"] = is_compat
                r["camelot"] = AudioAnalyzer.get_camelot(sample_key)
                if is_compat:
                    compatible.append(r)
                else:
                    incompatible.append(r)
            else:
                r["is_compatible"] = None
                incompatible.append(r)

        return {
            "target_key": target_key,
            "target_camelot": AudioAnalyzer.get_camelot(target_key),
            "compatible_count": len(compatible),
            "total_analyzed": len(results),
            "compatible": compatible,
            "others": incompatible,
        }

    @staticmethod
    def create_smart_folder(target_key, categories=None, base_path=None):
        """Create a smart folder with symlinks to harmonically compatible samples.

        Generates symlinks under NI Samples/_smart/<Key Name>/ so that
        Ableton's browser can directly show compatible samples.

        Args:
            target_key: Target key (e.g. 'Fm', 'C')
            categories: List of sample categories to scan (default: all)
            base_path: Base NI Samples path (default: ~/書類/Ableton Live/NI Samples)

        Returns:
            dict with folder path and file count
        """
        import os
        import glob

        if base_path is None:
            base_path = "/Users/mtsh/書類/Ableton Live/NI Samples"

        if categories is None:
            # Scan all category folders
            categories = [
                d for d in os.listdir(base_path)
                if os.path.isdir(os.path.join(base_path, d)) and d != "_smart"
            ]

        # Create smart folder
        safe_key = target_key.replace("#", "s").replace("/", "-")
        smart_dir = os.path.join(base_path, "_smart", safe_key)

        # Clean existing smart folder
        if os.path.exists(smart_dir):
            for f in os.listdir(smart_dir):
                fp = os.path.join(smart_dir, f)
                if os.path.islink(fp):
                    os.remove(fp)

        os.makedirs(smart_dir, exist_ok=True)

        total_linked = 0
        errors = []

        for cat in categories:
            cat_path = os.path.join(base_path, cat)
            if not os.path.isdir(cat_path):
                continue

            # Find all audio files (follow symlinks to real files)
            extensions = {".wav", ".aif", ".aiff", ".mp3", ".flac", ".ogg", ".m4a"}
            audio_files = []

            for root, dirs, files in os.walk(cat_path):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in extensions:
                        audio_files.append(os.path.join(root, f))

            if not audio_files:
                continue

            # Analyze each file for pitch
            for file_path in audio_files:
                try:
                    pitch_result = AudioAnalyzer.detect_pitch(file_path)
                    if "error" in pitch_result:
                        continue

                    sample_pitch = pitch_result.get("pitch", "")
                    is_atonal = pitch_result.get("is_atonal", True)

                    if is_atonal:
                        # Atonal samples are always compatible (hi-hats, noise snares)
                        # Include them in a subfolder
                        sub_dir = os.path.join(smart_dir, cat, "_atonal")
                        os.makedirs(sub_dir, exist_ok=True)
                    else:
                        # Check compatibility
                        if sample_pitch and len(sample_pitch) > 1:
                            root_note = sample_pitch[:-1]  # "F2" -> "F"
                            sample_key = root_note + "m"
                            is_compat = AudioAnalyzer.is_harmonically_compatible(target_key, sample_key)

                            if not is_compat:
                                # Also check major
                                sample_key_major = root_note
                                is_compat = AudioAnalyzer.is_harmonically_compatible(target_key, sample_key_major)

                            if not is_compat:
                                continue

                        sub_dir = os.path.join(smart_dir, cat)
                        os.makedirs(sub_dir, exist_ok=True)

                    # Create symlink
                    basename = os.path.basename(file_path)
                    link_path = os.path.join(sub_dir, basename)

                    # Handle duplicate names
                    if os.path.exists(link_path):
                        name, ext = os.path.splitext(basename)
                        link_path = os.path.join(sub_dir, "%s_2%s" % (name, ext))

                    os.symlink(file_path, link_path)
                    total_linked += 1

                except Exception as e:
                    errors.append({"file": file_path, "error": str(e)})

        return {
            "target_key": target_key,
            "camelot": AudioAnalyzer.get_camelot(target_key),
            "smart_folder": smart_dir,
            "total_files": total_linked,
            "categories_scanned": len(categories),
            "errors_count": len(errors),
        }


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python audio_analyzer.py <file> [--bpm-only] [--key-only] [--pitch-only]")
        print("  python audio_analyzer.py <folder> --folder [--mode full|pitch|key|bpm]")
        print("  python audio_analyzer.py <folder> --compatible <key>")
        sys.exit(1)

    target = sys.argv[1]

    if "--folder" in sys.argv:
        mode = "full"
        for i, arg in enumerate(sys.argv):
            if arg == "--mode" and i + 1 < len(sys.argv):
                mode = sys.argv[i + 1]
        result = AudioAnalyzer.analyze_folder(target, mode=mode)
    elif "--compatible" in sys.argv:
        key_idx = sys.argv.index("--compatible") + 1
        target_key = sys.argv[key_idx] if key_idx < len(sys.argv) else "Am"
        result = AudioAnalyzer.find_compatible_samples(target, target_key)
    elif "--smart-folder" in sys.argv:
        key_idx = sys.argv.index("--smart-folder") + 1
        target_key = sys.argv[key_idx] if key_idx < len(sys.argv) else "Fm"
        result = AudioAnalyzer.create_smart_folder(target_key)
    elif "--cache-stats" in sys.argv:
        result = AnalysisCache.stats()
    elif "--cache-clear" in sys.argv:
        AnalysisCache.clear()
        result = {"cleared": True}
    elif "--pitch-only" in sys.argv:
        result = AudioAnalyzer.detect_pitch(target)
    elif "--bpm-only" in sys.argv:
        result = AudioAnalyzer.detect_bpm(target)
    elif "--key-only" in sys.argv:
        result = AudioAnalyzer.detect_key(target)
    else:
        result = AudioAnalyzer.analyze(target)

    print(json.dumps(result, indent=2, ensure_ascii=False))
