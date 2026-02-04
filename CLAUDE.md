# CLAUDE.md - Project Guide for Claude Code

## Project Overview

PaniPuri is a sample-based steel pan MIDI instrument written in Python. It downloads real WAV recordings of a Double Seconds steel pan from the urbanPan project and maps them to MIDI notes for interactive playback with velocity-sensitive layering.

## Architecture

Single-file application (`panipuri.py`) with these components:

- **Sample Downloader** - Fetches WAV files from urbanPan GitHub repo on first run
- **SteelPanSampler class** - Core engine: loads samples, maps velocity to layers, manages polyphony via round-robin channel allocation
- **Interactive Mode** - Pygame-based visual keyboard with computer key-to-MIDI mapping
- **MIDI File Player** - Reads MIDI files via mido and triggers sampler
- **MIDI Controller Input** - Listens on hardware MIDI devices via python-rtmidi

## Key Technical Details

- **Note range**: F3 (MIDI 53) to C6 (MIDI 84) - 32 chromatic notes
- **Velocity layers**: 4 layers (0=pp, 1=mp, 2=f, 3=ff), fallback to nearest available
- **Sample naming**: `{layer}-{note}{octave}.wav` where sharps use S (e.g., `2-FS4.wav` = F#4 forte)
- **Audio**: pygame.mixer at 44100 Hz, 16-bit stereo, 512-sample buffer
- **Polyphony**: 16 channels, round-robin allocation

## File Structure

```
panipuri.py          # Main application (all modes)
samples/             # Downloaded WAV files (not in git)
demo.mid             # Generated demo MIDI file (not in git)
README.md            # User documentation
CLAUDE.md            # This file
requirements.txt     # Python dependencies
```

## Dependencies

- pygame - audio playback and interactive UI
- mido - MIDI file reading/writing
- numpy - imported but minimally used (available for future DSP)
- python-rtmidi - optional, for hardware MIDI controller input

## Common Tasks

```bash
# Run interactive mode
python panipuri.py

# Download samples only
python panipuri.py --download

# Play a MIDI file
python panipuri.py --play file.mid

# Create and play demo
python panipuri.py --create-demo

# List MIDI devices
python panipuri.py --list-midi
```

## Sample Source

All audio samples are from https://github.com/urbansmash/urbanPan
Downloaded to `samples/` directory, excluded from git via .gitignore.
