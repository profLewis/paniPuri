# CLAUDE.md - Project Guide for Claude Code

## Project Overview

PaniPuri is a sample-based steel pan MIDI instrument written in Python. It downloads real WAV recordings of a Double Seconds steel pan from the urbanPan project and maps them to MIDI notes for interactive playback with velocity-sensitive layering.

## Architecture

Main application (`panipuri.py`) with two playback engines and supporting tools:

- **Sample Downloader** - Fetches WAV files from urbanPan GitHub repo on first run
- **SteelPanSampler class** - Sample engine: loads WAV recordings, maps velocity to layers, manages polyphony via round-robin channel allocation
- **SynthSteelPan class** (`synth.py`) - Synthesis engine: generates tones using per-note parameters calibrated from real samples. Drop-in replacement for SteelPanSampler with same `note_on`/`note_off` interface
- **Calibration tool** (`calibrate.py`) - Analyzes urbanPan WAV samples to extract per-note synthesis parameters (pitch, harmonics, ADSR, spectral shape)
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
synth.py             # Calibrated synthesis engine (SynthSteelPan)
calibrate.py         # Sample analysis -> calibration.json
calibration.json     # Per-note synthesis parameters (committed)
samples/             # Downloaded WAV files (not in git)
songs/               # Song text files
demo.mid             # Generated demo MIDI file (not in git)
README.md            # User documentation
CLAUDE.md            # This file
requirements.txt     # Python dependencies
```

## Dependencies

- pygame - audio playback and interactive UI
- mido - MIDI file reading/writing
- numpy - array operations for synthesis and analysis
- scipy - signal processing (Butterworth filters, FFT) for synth engine
- python-rtmidi - optional, for hardware MIDI controller input

## Synth Architecture

The synthesizer (`synth.py`) generates steel pan tones matching the real urbanPan recordings:

- **7 partials**: sub-bass (0.5x), fundamental with +/- detune (1.0x), harmonics 2-4
- **Per-partial ADSR envelopes** with decay multipliers (higher harmonics decay faster)
- **Attack bloom**: 8ms sine burst for percussive attack transient
- **Butterworth low-pass filter**: 2nd-order, cutoff from calibration data
- **High-shelf brightness**: adjusts high-frequency content
- **Soft limiting**: tanh saturation to prevent clipping

**Calibration** (`calibrate.py`) extracts per-note parameters from layer-2 samples:
- Pitch: autocorrelation + Harmonic Product Spectrum, cross-validated against expected frequency
- Harmonics: FFT bin extraction at 0.5x, 1x, 2x, 3x, 4x with 5% tolerance windows
- ADSR: amplitude envelope with moving-average smoothing
- Brightness: spectral centroid and 85% energy rolloff

For notes without calibration data (outside F3-C6), parameters are interpolated from nearest calibrated notes.

## Common Tasks

```bash
# Run interactive mode (sample-based)
python panipuri.py

# Run interactive mode (synthesized)
python panipuri.py --synth

# Download samples only
python panipuri.py --download

# Re-calibrate from samples
python panipuri.py --calibrate

# Play a MIDI file
python panipuri.py --play file.mid

# Play with synth engine
python panipuri.py --synth --song songs/in_the_mood.txt

# Create and play demo
python panipuri.py --create-demo

# List MIDI devices
python panipuri.py --list-midi
```

## Sample Source

All audio samples are from https://github.com/urbansmash/urbanPan
Downloaded to `samples/` directory, excluded from git via .gitignore.
