#!/usr/bin/env python3
"""
Prepare all tenor pan sounds as WAV files.

For each note in the tenor pan layout, ensures a WAV file exists in sounds/
by trying, in order:
  1. Already exists in sounds/
  2. Download from urbanPan GitHub repo (layer 2, forte)
  3. Pitch-shift from an octave-below sample (2x playback rate)
  4. Synthesize using calibrated parameters

Layout source (in order):
  1. pan_layout.json (if exists)
  2. Parse noteShapes from player.html
  3. Built-in default tenor pan layout

Usage:
    python prepare_sounds.py            # Populate sounds/
    python prepare_sounds.py --force    # Re-generate all files
    python prepare_sounds.py --verbose  # Show detail for each note
"""

import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.error
import numpy as np
from scipy.io import wavfile
from scipy import signal

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")
LAYOUT_FILE = os.path.join(BASE_DIR, "pan_layout.json")
PLAYER_HTML = os.path.join(BASE_DIR, "player.html")

GITHUB_RAW_BASE = (
    "https://raw.githubusercontent.com/urbansmash/urbanPan/master/urbanPan/Samples"
)

SAMPLE_RATE = 44100

# Note name mappings
# Display name -> filename-safe name (sharps use lowercase 's')
NAME_TO_FILESAFE = {
    "C": "C", "C#": "Cs", "Db": "Cs",
    "D": "D", "D#": "Ds", "Eb": "Ds",
    "E": "E",
    "F": "F", "F#": "Fs", "Gb": "Fs",
    "G": "G", "G#": "Gs", "Ab": "Gs",
    "A": "A", "A#": "As", "Bb": "As",
    "B": "B",
}

# Display name -> urbanPan filename format (sharps use uppercase 'S')
NAME_TO_URBANPAN = {
    "C": "C", "C#": "CS", "Db": "CS",
    "D": "D", "D#": "DS", "Eb": "DS",
    "E": "E",
    "F": "F", "F#": "FS", "Gb": "FS",
    "G": "G", "G#": "GS", "Ab": "GS",
    "A": "A", "A#": "AS", "Bb": "AS",
    "B": "B",
}

NOTE_TO_SEMITONE = {
    "C": 0, "C#": 1, "Db": 1,
    "D": 2, "D#": 3, "Eb": 3,
    "E": 4,
    "F": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8,
    "A": 9, "A#": 10, "Bb": 10,
    "B": 11,
}

# Default tenor pan layout (29 notes, 3 rings)
DEFAULT_LAYOUT = [
    # Outer Ring (Octave 4) - 4ths
    {"name": "F#", "octave": 4, "ring": "outer", "idx": "O0"},
    {"name": "B",  "octave": 4, "ring": "outer", "idx": "O1"},
    {"name": "E",  "octave": 4, "ring": "outer", "idx": "O2"},
    {"name": "A",  "octave": 4, "ring": "outer", "idx": "O3"},
    {"name": "D",  "octave": 4, "ring": "outer", "idx": "O4"},
    {"name": "G",  "octave": 4, "ring": "outer", "idx": "O5"},
    {"name": "C",  "octave": 4, "ring": "outer", "idx": "O6"},
    {"name": "F",  "octave": 4, "ring": "outer", "idx": "O7"},
    {"name": "Bb", "octave": 4, "ring": "outer", "idx": "O8"},
    {"name": "Eb", "octave": 4, "ring": "outer", "idx": "O9"},
    {"name": "Ab", "octave": 4, "ring": "outer", "idx": "O10"},
    {"name": "C#", "octave": 4, "ring": "outer", "idx": "O11"},
    # Central Ring (Octave 5) - 5ths
    {"name": "F#", "octave": 5, "ring": "central", "idx": "C0"},
    {"name": "B",  "octave": 5, "ring": "central", "idx": "C1"},
    {"name": "E",  "octave": 5, "ring": "central", "idx": "C2"},
    {"name": "A",  "octave": 5, "ring": "central", "idx": "C3"},
    {"name": "D",  "octave": 5, "ring": "central", "idx": "C4"},
    {"name": "G",  "octave": 5, "ring": "central", "idx": "C5"},
    {"name": "C",  "octave": 5, "ring": "central", "idx": "C6"},
    {"name": "F",  "octave": 5, "ring": "central", "idx": "C7"},
    {"name": "Bb", "octave": 5, "ring": "central", "idx": "C8"},
    {"name": "Eb", "octave": 5, "ring": "central", "idx": "C9"},
    {"name": "Ab", "octave": 5, "ring": "central", "idx": "C10"},
    {"name": "C#", "octave": 5, "ring": "central", "idx": "C11"},
    # Inner Ring (Octave 6) - 6ths
    {"name": "C#", "octave": 6, "ring": "inner", "idx": "I0"},
    {"name": "E",  "octave": 6, "ring": "inner", "idx": "I1"},
    {"name": "D",  "octave": 6, "ring": "inner", "idx": "I2"},
    {"name": "C",  "octave": 6, "ring": "inner", "idx": "I3"},
    {"name": "Eb", "octave": 6, "ring": "inner", "idx": "I4"},
]


def note_to_midi(name, octave):
    """Convert note name and octave to MIDI number."""
    semi = NOTE_TO_SEMITONE.get(name)
    if semi is None:
        return None
    return (octave + 1) * 12 + semi


def sound_filename(name, octave):
    """Get the output filename for a note (e.g. 'Fs4.wav')."""
    safe = NAME_TO_FILESAFE.get(name, name.replace("#", "s"))
    return f"{safe}{octave}.wav"


def urbanpan_filename(name, octave):
    """Get the urbanPan sample filename (e.g. '2-FS4.wav')."""
    up = NAME_TO_URBANPAN.get(name)
    if up is None:
        return None
    return f"2-{up}{octave}.wav"


# ---------------------------------------------------------------------------
# Step 1: Load note layout
# ---------------------------------------------------------------------------

def load_layout():
    """Load the tenor pan note layout from file or defaults."""

    # 1. Try pan_layout.json
    if os.path.exists(LAYOUT_FILE):
        with open(LAYOUT_FILE, "r") as f:
            data = json.load(f)
        notes = data.get("notes", data) if isinstance(data, dict) else data
        print(f"Layout: loaded {len(notes)} notes from {LAYOUT_FILE}")
        return notes, "file"

    # 2. Try parsing player.html
    if os.path.exists(PLAYER_HTML):
        try:
            with open(PLAYER_HTML, "r") as f:
                html = f.read()
            # Find noteShapes array
            marker = "const noteShapes = "
            start = html.find(marker)
            if start >= 0:
                arr_start = start + len(marker)
                depth = 0
                end = arr_start
                for i, c in enumerate(html[arr_start:], arr_start):
                    if c == "[":
                        depth += 1
                    elif c == "]":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                shapes = json.loads(html[arr_start:end])
                notes = [
                    {"name": s["name"], "octave": s["octave"],
                     "ring": s["ring"], "idx": s["idx"]}
                    for s in shapes
                ]
                print(f"Layout: parsed {len(notes)} notes from {PLAYER_HTML}")
                return notes, "html"
        except Exception as e:
            print(f"  Warning: could not parse player.html: {e}")

    # 3. Hardcoded default
    print(f"Layout: using built-in default ({len(DEFAULT_LAYOUT)} notes)")
    return DEFAULT_LAYOUT, "default"


def save_layout(notes):
    """Save layout to pan_layout.json for future runs."""
    with open(LAYOUT_FILE, "w") as f:
        json.dump({"notes": notes}, f, indent=2)
    print(f"Saved layout to {LAYOUT_FILE}")


# ---------------------------------------------------------------------------
# Step 2: Sound sourcing
# ---------------------------------------------------------------------------

def download_urbanpan(name, octave, dest_path):
    """Try to download a sample from urbanPan. Returns True on success."""
    fname = urbanpan_filename(name, octave)
    if fname is None:
        return False
    url = f"{GITHUB_RAW_BASE}/{fname}"
    try:
        urllib.request.urlretrieve(url, dest_path)
        return True
    except (urllib.error.HTTPError, urllib.error.URLError):
        return False


def try_local_sample(name, octave):
    """Check if we already have the urbanPan sample in samples/ dir."""
    fname = urbanpan_filename(name, octave)
    if fname is None:
        return None
    path = os.path.join(SAMPLES_DIR, fname)
    return path if os.path.exists(path) else None


def copy_wav(src, dest):
    """Copy a WAV file from src to dest."""
    import shutil
    shutil.copy2(src, dest)


def pitch_shift_octave_up(src_path, dest_path):
    """Load a WAV, resample to shift up one octave, save."""
    sr, audio = wavfile.read(src_path)

    # Convert to float
    if audio.dtype == np.int16:
        audio_f = audio.astype(np.float32) / 32768.0
    elif audio.dtype == np.int32:
        audio_f = audio.astype(np.float32) / 2147483648.0
    else:
        audio_f = audio.astype(np.float32)

    # Handle stereo
    if len(audio_f.shape) > 1:
        # Resample each channel: half the samples = double the pitch
        new_len = len(audio_f) // 2
        channels = []
        for ch in range(audio_f.shape[1]):
            channels.append(signal.resample(audio_f[:, ch], new_len))
        shifted = np.column_stack(channels)
    else:
        new_len = len(audio_f) // 2
        shifted = signal.resample(audio_f, new_len)

    # Normalize
    peak = np.max(np.abs(shifted))
    if peak > 0:
        shifted = shifted / peak * 0.82

    # Convert to int16
    audio_int = (shifted * 32767).astype(np.int16)

    # Ensure stereo
    if len(audio_int.shape) == 1:
        audio_int = np.column_stack((audio_int, audio_int))

    wavfile.write(dest_path, sr, audio_int)


def synthesize_note(name, octave, dest_path):
    """Synthesize a note using the calibrated synth engine."""
    from synth import generate_note, load_calibration, get_note_params, midi_to_freq

    midi = note_to_midi(name, octave)
    if midi is None:
        return False

    calibration = load_calibration()
    params = get_note_params(calibration, midi)
    freq = midi_to_freq(midi)
    audio = generate_note(freq, params)

    # Convert to stereo int16
    audio_int = (audio * 32767).astype(np.int16)
    stereo = np.column_stack((audio_int, audio_int))
    wavfile.write(dest_path, SAMPLE_RATE, stereo)
    return True


def ensure_sound(name, octave, force=False, verbose=False):
    """Ensure a WAV file exists for this note. Returns the method used."""
    fname = sound_filename(name, octave)
    dest = os.path.join(SOUNDS_DIR, fname)

    # 1. Already exists
    if os.path.exists(dest) and not force:
        if verbose:
            size = os.path.getsize(dest) // 1024
            print(f"  {name:3s}{octave}  {fname:10s}  exists ({size} KB)")
        return "exists"

    # 2. Copy from local samples/ if available
    local = try_local_sample(name, octave)
    if local:
        copy_wav(local, dest)
        if verbose:
            print(f"  {name:3s}{octave}  {fname:10s}  copied from samples/")
        return "local"

    # 3. Download from urbanPan
    if download_urbanpan(name, octave, dest):
        size = os.path.getsize(dest) // 1024
        if verbose:
            print(f"  {name:3s}{octave}  {fname:10s}  downloaded ({size} KB)")
        return "downloaded"

    # 4. Pitch-shift from lower octave
    lower_octave = octave - 1
    # Try local samples/ first
    lower_local = try_local_sample(name, lower_octave)
    if lower_local:
        pitch_shift_octave_up(lower_local, dest)
        if verbose:
            print(f"  {name:3s}{octave}  {fname:10s}  shifted from {name}{lower_octave} (local)")
        return "shifted"

    # Try downloading the lower octave
    lower_fname = urbanpan_filename(name, lower_octave)
    if lower_fname:
        lower_tmp = os.path.join(SOUNDS_DIR, f"_tmp_{lower_fname}")
        if download_urbanpan(name, lower_octave, lower_tmp):
            pitch_shift_octave_up(lower_tmp, dest)
            os.remove(lower_tmp)
            if verbose:
                print(f"  {name:3s}{octave}  {fname:10s}  shifted from {name}{lower_octave} (downloaded)")
            return "shifted"
        # Clean up failed download
        if os.path.exists(lower_tmp):
            os.remove(lower_tmp)

    # 5. Synthesize
    if synthesize_note(name, octave, dest):
        if verbose:
            print(f"  {name:3s}{octave}  {fname:10s}  synthesized")
        return "synthesized"

    print(f"  {name:3s}{octave}  {fname:10s}  FAILED - could not produce sound")
    return "failed"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def prepare_sounds(force=False, verbose=False):
    """Main entry point: load layout, ensure all sounds exist."""
    os.makedirs(SOUNDS_DIR, exist_ok=True)

    notes, source = load_layout()

    # Save layout if it was generated
    if source != "file":
        save_layout(notes)

    print(f"\nPreparing {len(notes)} sounds in {SOUNDS_DIR}/\n")

    stats = {"exists": 0, "local": 0, "downloaded": 0, "shifted": 0,
             "synthesized": 0, "failed": 0}

    for note in notes:
        name = note["name"]
        octave = note["octave"]
        method = ensure_sound(name, octave, force=force, verbose=verbose)
        stats[method] = stats.get(method, 0) + 1

        if not verbose:
            fname = sound_filename(name, octave)
            sym = {"exists": ".", "local": "L", "downloaded": "D",
                   "shifted": "S", "synthesized": "~", "failed": "!"}
            print(f"  {sym.get(method, '?')} {name:3s}{octave}  {fname}", flush=True)

    print(f"\nDone: {len(notes)} notes")
    parts = []
    if stats["exists"]:
        parts.append(f'{stats["exists"]} already existed')
    if stats["local"]:
        parts.append(f'{stats["local"]} copied from samples/')
    if stats["downloaded"]:
        parts.append(f'{stats["downloaded"]} downloaded')
    if stats["shifted"]:
        parts.append(f'{stats["shifted"]} octave-shifted')
    if stats["synthesized"]:
        parts.append(f'{stats["synthesized"]} synthesized')
    if stats["failed"]:
        parts.append(f'{stats["failed"]} FAILED')
    print("  " + ", ".join(parts))

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Prepare all tenor pan note WAV files in sounds/"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-generate all files even if they exist"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detail for each note"
    )
    args = parser.parse_args()
    prepare_sounds(force=args.force, verbose=args.verbose)


if __name__ == "__main__":
    main()
