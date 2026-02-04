# PaniPuri

A sample-based steel pan MIDI instrument for Python. Uses real recordings of a Double Seconds steel pan from the [urbanPan](https://github.com/urbansmash/urbanPan) project, with automatic sound preparation, octave pitch-shifting for missing notes, and a calibrated synthesis fallback.

## Features

- **Real steel pan samples** - recorded WAV files from a Double Seconds pan, not synthesized
- **Prepared sounds** - `sounds/` directory with one WAV per note, ready to play (included in repo)
- **Automatic preparation** - `prepare_sounds.py` sources sounds from urbanPan downloads, octave pitch-shifting, or synthesis
- **Calibrated synthesizer** - `--synth` mode generates tones matched to the real samples, no downloads needed
- **Interactive web player** - `player.html` with SVG pan layout, hover-to-play, synth/samples toggle
- **Tenor pan range** - C4 to E6 (29 notes across 3 rings: 4ths, 5ths, 6ths)
- **16-voice polyphony** - play chords and fast runs without note stealing
- **Multiple interfaces**:
  - Interactive web player (`player.html`) with SVG pan visualization
  - Interactive pygame keyboard with visual piano display
  - MIDI file playback
  - MIDI controller input (any USB/Bluetooth MIDI keyboard)
  - Demo melody generator

## Quick Start

### Install

```bash
pip install pygame mido numpy

# Optional: for MIDI controller support
pip install python-rtmidi
```

### Run

```bash
# Interactive keyboard mode (default)
python panipuri.py

# Or open the web-based player directly
open player.html

# Prepare/regenerate sound files
python prepare_sounds.py
```

The `sounds/` directory contains prepared WAV files for all 29 tenor pan notes and is included in the repo. If missing, PaniPuri auto-generates them via `prepare_sounds.py`.

## Usage

### Interactive Keyboard

```bash
python panipuri.py
```

Opens a pygame window with a visual piano keyboard. Play using your computer keyboard:

| Keys | Notes |
|------|-------|
| `Z X C V B N M` | C4-B4 white keys |
| `S D G H J` | C#4-A#4 black keys |
| `Q W E R T Y U I` | C5-C6 white keys |
| `2 3 5 6 7` | C#5-A#5 black keys |
| `, . / L ; '` | F3-A#3 (low register) |
| `UP / DOWN` | Change velocity |
| `ESC` | Quit |

### Play a MIDI File

```bash
python panipuri.py --play mysong.mid
```

Any MIDI file will work. Notes outside the C4-E6 range are silently skipped. Velocity is mapped to volume via a power curve.

### Create and Play a Demo

```bash
python panipuri.py --create-demo
```

Generates a short Caribbean-flavored melody as a MIDI file (`demo.mid`) and plays it through the sampler.

### Play a Song File

```bash
python panipuri.py --song songs/in_the_mood.txt
```

Song files are simple text with comma-separated note names. Default octave is 5, so `G` means G5. Override per-note with `D6`, `B4`, etc. Example:

```
# title: In the Mood
tempo=160
octave=5
velocity=90
duration=0.5

G4,B4,D,G,G,G,G,G,F#,G,D,B4
G4,B4,D,G,G,G,G,G,F#,G,D,B4
```

**Song file format:**

| Element | Meaning |
|---------|---------|
| `G` | G at default octave (5), default duration |
| `F#` | F-sharp at default octave |
| `D6` | D at octave 6 |
| `Bb4` | B-flat at octave 4 |
| `G:2` | G at default octave, held for 2 beats |
| `D6:0.25` | D6, sixteenth note (0.25 beats) |
| `R` or `-` | Rest for default duration |
| `R:2` | Rest for 2 beats |
| `# comment` | Comment line (ignored) |
| `tempo=N` | Set tempo in BPM |
| `octave=N` | Set default octave |
| `velocity=N` | Set MIDI velocity (1-127) |
| `duration=N` | Set default note duration in beats |

A demo song file is included at `songs/in_the_mood.txt`.

### Prepare Sounds

```bash
# Populate sounds/ with WAVs for all 29 tenor pan notes
python prepare_sounds.py

# Re-generate all files even if they exist
python prepare_sounds.py --force

# Show detail for each note
python prepare_sounds.py --verbose
```

For each note, `prepare_sounds.py` tries in order:
1. Already exists in `sounds/`
2. Copy from local `samples/` directory (urbanPan layer 2)
3. Download from urbanPan GitHub
4. Pitch-shift from an octave-below sample (2x playback rate)
5. Synthesize using calibrated parameters

### Synthesizer Mode

```bash
# Play with synthesized sounds (no sample download needed)
python panipuri.py --synth

# All playback modes work with --synth:
python panipuri.py --synth --create-demo
python panipuri.py --synth --song songs/in_the_mood.txt
python panipuri.py --synth --play file.mid
```

The synthesizer uses per-note parameters calibrated from the real urbanPan samples. The calibration data (`calibration.json`) is included in the repo, so `--synth` mode works immediately without downloading samples.

To re-run calibration on your own samples:

```bash
python panipuri.py --download     # Download samples first
python panipuri.py --calibrate    # Analyze samples, update calibration.json
```

Or run the calibration tool directly:

```bash
python calibrate.py --verbose
```

### MIDI Controller Input

```bash
# List available MIDI devices
python panipuri.py --list-midi

# Connect to a specific device
python panipuri.py --midi-input 0
```

Listens for note-on/note-off messages from a hardware MIDI controller. Velocity is passed through to select sample layers.

### Options

| Flag | Description |
|------|-------------|
| `--download` | Download samples without starting the player |
| `--force-download` | Re-download all samples |
| `--play FILE` | Play a MIDI file |
| `--song FILE` | Play a text song file (see `songs/` for examples) |
| `--create-demo` | Generate and play a demo melody |
| `--list-midi` | List MIDI input devices |
| `--midi-input N` | Listen on MIDI device index N |
| `--velocity V` | Set default velocity, 1-127 (default: 100) |
| `--polyphony N` | Max simultaneous notes (default: 16) |
| `--synth` | Use calibrated synthesizer instead of WAV samples |
| `--calibrate` | Run calibration on downloaded samples |

## How It Works

### Sound Pipeline

PaniPuri uses a prepared `sounds/` directory containing one WAV file per tenor pan note (29 notes, C4-E6). These are included in the repository for immediate use.

The `prepare_sounds.py` script generates these files using a cascading fallback:

1. **urbanPan recordings** (25 notes) - Layer 2 (forte) samples from the [urbanPan](https://github.com/urbansmash/urbanPan) project
2. **Octave pitch-shifting** (4 notes: C#6, D6, Eb6, E6) - Resampled from octave-below recordings at 2x rate via `scipy.signal.resample`
3. **Calibrated synthesis** (fallback) - Generated using per-note parameters extracted from the real samples

### Web Player

`player.html` is a self-contained interactive player with:
- SVG-based tenor pan layout (outer ring red, central ring blue, inner ring green)
- Hover-to-play interaction
- Synth/Samples toggle (defaults to samples mode)
- Per-note calibrated synthesis via Web Audio API
- Octave pitch-shifting for notes without direct samples

### Velocity Curve

MIDI velocity (0-127) maps to volume with a power curve (`v^0.7`) for a more natural dynamic feel rather than a linear mapping.

### Polyphony

PaniPuri uses round-robin channel allocation across 16 pygame mixer channels, allowing chords, arpeggios, and overlapping notes.

## Sample Source

The prepared WAV files in `sounds/` are included in this repository. The original multi-velocity recordings come from the [urbanPan](https://github.com/urbansmash/urbanPan) project by [urbansmash](https://github.com/urbansmash).

To download the full multi-velocity sample set (78 WAV files, ~30 MB):

```bash
python panipuri.py --download
```

This stores files in `samples/` (excluded from git via `.gitignore`).

## Requirements

- Python 3.8+
- pygame
- mido
- numpy
- scipy (for synthesizer mode)
- python-rtmidi (optional, for MIDI controller input)

## Credits

- Steel pan samples from [urbanPan](https://github.com/urbansmash/urbanPan) by urbansmash
- Built as a companion to the [deepPan](https://github.com/plewis/deepPan) 3D-printable steel pan project

## License

MIT
