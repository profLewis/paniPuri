# PaniPuri

A sample-based steel pan MIDI instrument for Python. Downloads real multi-velocity recordings of a Double Seconds steel pan from the [urbanPan](https://github.com/urbansmash/urbanPan) project and plays them back with MIDI mapping, velocity-sensitive layering, and 16-voice polyphony.

## Features

- **Real steel pan samples** - recorded WAV files from a Double Seconds pan, not synthesized
- **Velocity-sensitive** - 4 dynamic layers (pp, mp, f, ff) selected automatically by MIDI velocity
- **Full chromatic range** - F3 to C6 (MIDI 53-84), 32 notes
- **16-voice polyphony** - play chords and fast runs without note stealing
- **Auto-download** - samples are fetched from GitHub on first run
- **Multiple interfaces**:
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

# Samples download automatically on first run.
# To download manually:
python panipuri.py --download
```

On first run, PaniPuri downloads ~30 MB of WAV samples from the urbanPan GitHub repository into a `samples/` directory.

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

Any MIDI file will work. Notes outside the F3-C6 range are silently skipped. Velocity values from the MIDI file select the appropriate sample layer.

### Create and Play a Demo

```bash
python panipuri.py --create-demo
```

Generates a short Caribbean-flavored melody as a MIDI file (`demo.mid`) and plays it through the sampler.

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
| `--create-demo` | Generate and play a demo melody |
| `--list-midi` | List MIDI input devices |
| `--midi-input N` | Listen on MIDI device index N |
| `--velocity V` | Set default velocity, 1-127 (default: 100) |
| `--polyphony N` | Max simultaneous notes (default: 16) |

## How It Works

### Sample-Based Approach

PaniPuri follows the same approach as [urbanPan](https://github.com/urbansmash/urbanPan): playing back pre-recorded WAV files of a real steel pan rather than synthesizing sounds. This gives authentic timbre that synthesis cannot easily replicate.

The urbanPan project recorded a Double Seconds steel pan at multiple dynamic levels:

| Layer | Dynamic | Coverage |
|-------|---------|----------|
| 0 | pp (pianissimo) | 10 notes (sparse) |
| 1 | mp (mezzo-piano) | 32 notes (full) |
| 2 | f (forte) | 32 notes (full) |
| 3 | ff (fortissimo) | 4 notes (sparse) |

When a note is triggered, PaniPuri selects the best matching velocity layer. If the exact layer isn't available for that note, it falls back to the nearest available layer.

### Velocity Curve

MIDI velocity (0-127) maps to volume with a power curve (`v^0.7`) for a more natural dynamic feel rather than a linear mapping.

### Polyphony

Unlike the original urbanPan (single voice), PaniPuri uses round-robin channel allocation across 16 pygame mixer channels, allowing chords, arpeggios, and overlapping notes.

## Sample Source

**The WAV samples used by PaniPuri are not included in this repository.** They are downloaded at runtime from a separate GitHub repository:

> **Source repository:** [https://github.com/urbansmash/urbanPan](https://github.com/urbansmash/urbanPan)
>
> Specifically, from the [`urbanPan/Samples/`](https://github.com/urbansmash/urbanPan/tree/master/urbanPan/Samples) directory of that repo.

The urbanPan repository by [urbansmash](https://github.com/urbansmash) contains recordings of a real Double Seconds steel pan. PaniPuri downloads these files on first run (or via `--download`) and stores them locally in the `samples/` directory, which is excluded from version control via `.gitignore`.

The download includes:

- **78 WAV files** (~30 MB total) covering 4 velocity layers across the chromatic range F3-C6
- **`urbanPan.sf2`** - a SoundFont file for use in DAWs
- **`FN03.wav`, `FS03.wav`** - additional recordings

No samples are bundled with PaniPuri itself. If the urbanPan repository becomes unavailable, you would need to supply your own WAV files in the `samples/` directory following the naming convention `{layer}-{note}{octave}.wav` (e.g., `2-FS4.wav` for F#4 at velocity layer 2).

## Requirements

- Python 3.8+
- pygame
- mido
- numpy
- python-rtmidi (optional, for MIDI controller input)

## Credits

- Steel pan samples from [urbanPan](https://github.com/urbansmash/urbanPan) by urbansmash
- Built as a companion to the [deepPan](https://github.com/plewis/deepPan) 3D-printable steel pan project

## License

MIT
