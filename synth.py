#!/usr/bin/env python3
"""
Calibrated steel pan synthesizer for PaniPuri.

Generates steel pan tones using per-note parameters extracted from real
urbanPan samples. Drop-in replacement for SteelPanSampler with the same
note_on/note_off interface.

The synthesis architecture matches deepPan's generate_sounds.py:
- 7 partials: sub-bass (0.5x), fundamental with +/- detune (1.0x), harmonics 2-4
- Per-partial ADSR envelopes with decay multipliers
- Attack "bloom" effect (8ms sine burst)
- Butterworth low-pass filter
- High-shelf brightness adjustment
- Soft limiting via tanh

Usage:
    # As a module (used by panipuri.py --synth):
    from synth import SynthSteelPan
    synth = SynthSteelPan()
    synth.note_on(60, 100)  # Play middle C at velocity 100

    # Standalone test:
    python synth.py              # Play a test scale
    python synth.py --note C5    # Play a single note
"""

import os
import json
import argparse
import numpy as np
from scipy import signal

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SAMPLE_RATE = 44100
NOTE_DURATION = 1.5  # seconds

CALIBRATION_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "calibration.json"
)

MIDI_LOW = 53   # F3
MIDI_HIGH = 84  # C6

NOTE_NAMES_DISPLAY = [
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"
]

# Fallback defaults if no calibration data
DEFAULT_PARAMS = {
    'attack': 15,
    'decay': 500,
    'sustain': 20,
    'release': 300,
    'sub_bass': 20,
    'fundamental': 100,
    'harmonic2': 30,
    'harmonic3': 10,
    'harmonic4': 5,
    'filter': 6000,
    'brightness': 50,
    'detune': 2,
}


def midi_to_freq(midi_note):
    """Convert MIDI note number to frequency (A4=440Hz)."""
    return 440.0 * (2 ** ((midi_note - 69) / 12))


def midi_to_display(midi_note):
    """Convert MIDI note to readable name."""
    octave = (midi_note // 12) - 1
    note_idx = midi_note % 12
    return f"{NOTE_NAMES_DISPLAY[note_idx]}{octave}"


# ---------------------------------------------------------------------------
# Calibration data loading
# ---------------------------------------------------------------------------

def load_calibration(path=CALIBRATION_PATH):
    """Load calibration data from JSON file."""
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return json.load(f)


def get_note_params(calibration, midi_note):
    """Get synthesis parameters for a MIDI note.

    Uses calibration data if available, interpolates from nearest
    calibrated notes if not, falls back to defaults.
    """
    if calibration is None:
        return DEFAULT_PARAMS.copy()

    notes = calibration.get('notes', {})
    defaults = calibration.get('defaults', DEFAULT_PARAMS)
    key = str(midi_note)

    # Exact match
    if key in notes:
        params = defaults.copy()
        params.update(notes[key])
        if 'detune' not in params:
            params['detune'] = defaults.get('detune', 2)
        return params

    # Interpolate from nearest calibrated notes
    calibrated_notes = sorted([int(k) for k in notes.keys()])
    if not calibrated_notes:
        return defaults.copy()

    # Find nearest below and above
    below = [n for n in calibrated_notes if n < midi_note]
    above = [n for n in calibrated_notes if n > midi_note]

    if below and above:
        lo = below[-1]
        hi = above[0]
        t = (midi_note - lo) / (hi - lo)
        lo_params = notes[str(lo)]
        hi_params = notes[str(hi)]

        params = defaults.copy()
        for k in ['attack', 'decay', 'sustain', 'release',
                   'sub_bass', 'fundamental', 'harmonic2', 'harmonic3', 'harmonic4',
                   'filter', 'brightness']:
            lo_val = lo_params.get(k, defaults.get(k, 0))
            hi_val = hi_params.get(k, defaults.get(k, 0))
            params[k] = int(lo_val + t * (hi_val - lo_val))
        params['detune'] = defaults.get('detune', 2)
        return params
    elif below:
        params = defaults.copy()
        params.update(notes[str(below[-1])])
        params.setdefault('detune', defaults.get('detune', 2))
        return params
    elif above:
        params = defaults.copy()
        params.update(notes[str(above[0])])
        params.setdefault('detune', defaults.get('detune', 2))
        return params

    return defaults.copy()


# ---------------------------------------------------------------------------
# Synthesis engine
# ---------------------------------------------------------------------------

def generate_note(frequency, params, duration=NOTE_DURATION, sample_rate=SAMPLE_RATE):
    """Generate a steel pan tone with given parameters.

    Synthesis architecture matches deepPan's generate_sounds.py:
    - 7 partials with per-partial ADSR envelopes
    - Attack bloom effect
    - Butterworth low-pass filter
    - Brightness adjustment
    - Soft limiting
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    attack_time = params.get('attack', 15) / 1000
    decay_time = params.get('decay', 500) / 1000
    sustain_level = params.get('sustain', 20) / 100
    detune_cents = params.get('detune', 2)

    partials = [
        (0.50, params.get('sub_bass', 20) / 100, 1.0),
        (1.00 - detune_cents / 1000, params.get('fundamental', 100) / 100 * 0.1, 1.0),
        (1.00, params.get('fundamental', 100) / 100, 1.0),
        (1.00 + detune_cents / 1000, params.get('fundamental', 100) / 100 * 0.1, 1.0),
        (2.00, params.get('harmonic2', 30) / 100, 1.3),
        (3.00, params.get('harmonic3', 10) / 100, 1.8),
        (4.00, params.get('harmonic4', 5) / 100, 2.2),
    ]

    attack_samples = int(attack_time * sample_rate)
    decay_samples = int(decay_time * sample_rate)

    sound = np.zeros_like(t)

    for ratio, amp, decay_mult in partials:
        if amp < 0.01:
            continue

        freq = frequency * ratio
        if freq > sample_rate / 2 - 500 or freq < 30:
            continue

        # Per-partial ADSR envelope
        env = np.ones_like(t)

        # Attack
        if attack_samples > 0:
            attack_env = np.sin(np.linspace(0, np.pi / 2, attack_samples)) ** 1.5
            env[:attack_samples] = attack_env

        # Decay to sustain
        decay_start = attack_samples
        decay_end = min(decay_start + decay_samples, len(t))
        if decay_end > decay_start:
            env[decay_start:decay_end] = np.linspace(1.0, sustain_level, decay_end - decay_start)

        # Sustain with exponential decay (higher harmonics decay faster)
        sustain_start = decay_end
        sustain_tau = decay_time / decay_mult
        if sustain_start < len(t):
            env[sustain_start:] = sustain_level * np.exp(
                -(t[sustain_start:] - t[sustain_start]) / sustain_tau
            )

        phase = np.random.uniform(0, 2 * np.pi)
        sound += amp * env * np.sin(2 * np.pi * freq * t + phase)

    # Attack bloom (8ms sine burst)
    bloom_len = int(0.008 * sample_rate)
    if bloom_len > 0:
        bloom_t = np.linspace(0, 0.008, bloom_len)
        bloom = np.sin(2 * np.pi * frequency * bloom_t)
        bloom *= np.exp(-bloom_t * 200)
        bloom *= 0.08
        sound[:bloom_len] += bloom

    # Butterworth low-pass filter
    nyq = sample_rate / 2
    cutoff = min(params.get('filter', 6000), nyq - 100) / nyq
    if 0.01 < cutoff < 0.99:
        b, a = signal.butter(2, cutoff, btype='low')
        sound = signal.filtfilt(b, a, sound)

    # Brightness adjustment (high-shelf)
    brightness = params.get('brightness', 50)
    if brightness != 50:
        brightness_boost = (brightness - 50) / 50
        if brightness_boost > 0:
            high_cutoff = 2000 / nyq
            if high_cutoff < 0.99:
                b, a = signal.butter(1, high_cutoff, btype='high')
                highs = signal.filtfilt(b, a, sound)
                sound += highs * brightness_boost * 0.5

    # Soft limiting
    sound = np.tanh(sound * 1.2) / 1.2

    # Normalize
    max_val = np.max(np.abs(sound))
    if max_val > 0:
        sound = sound / max_val * 0.85

    return sound


# ---------------------------------------------------------------------------
# SynthSteelPan - drop-in replacement for SteelPanSampler
# ---------------------------------------------------------------------------

class SynthSteelPan:
    """Calibrated steel pan synthesizer with the same interface as SteelPanSampler."""

    def __init__(self, max_polyphony=16, calibration_path=CALIBRATION_PATH):
        import pygame
        import pygame.mixer

        self.pygame = pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)

        self.max_polyphony = max_polyphony
        self.calibration = load_calibration(calibration_path)
        self.loaded = False
        self._cache = {}  # {midi_note: pygame.mixer.Sound}

        # Set up mixer channels
        pygame.mixer.set_num_channels(max_polyphony)
        self.channels = [pygame.mixer.Channel(i) for i in range(max_polyphony)]
        self._next_channel = 0

        # Pre-build a dict for compatibility with interactive_mode
        # (it reads sampler.samples for display)
        self.samples = {}

        if self.calibration:
            cal_notes = len(self.calibration.get('notes', {}))
            print(f"Synth engine loaded with {cal_notes} calibrated notes")
        else:
            print("Synth engine loaded (no calibration data - using defaults)")

    def load_samples(self):
        """Pre-generate and cache all notes. Called for compatibility with SteelPanSampler."""
        print("Pre-generating synthesized notes...")
        for midi_note in range(MIDI_LOW, MIDI_HIGH + 1):
            self._get_or_generate(midi_note)
        self.loaded = True
        print(f"Generated {len(self._cache)} synthesized notes "
              f"({MIDI_LOW}-{MIDI_HIGH})")
        # Populate samples dict for compatibility
        for midi_note in self._cache:
            self.samples[(2, midi_note)] = self._cache[midi_note]

    def _get_or_generate(self, midi_note):
        """Get a cached sound or generate it."""
        if midi_note in self._cache:
            return self._cache[midi_note]

        frequency = midi_to_freq(midi_note)
        params = get_note_params(self.calibration, midi_note)
        audio = generate_note(frequency, params)

        # Convert to 16-bit stereo for pygame
        audio_int = (audio * 32767).astype(np.int16)
        stereo = np.column_stack((audio_int, audio_int))

        sound = self.pygame.sndarray.make_sound(stereo)
        self._cache[midi_note] = sound
        return sound

    def _get_channel(self):
        """Round-robin channel allocation."""
        ch = self.channels[self._next_channel]
        self._next_channel = (self._next_channel + 1) % self.max_polyphony
        return ch

    def note_on(self, midi_note, velocity=100):
        """Play a synthesized steel pan note."""
        sound = self._get_or_generate(midi_note)

        # Scale volume by velocity with power curve
        vol = (velocity / 127.0) ** 0.7
        sound.set_volume(vol)

        ch = self._get_channel()
        ch.play(sound)
        return ch

    def note_off(self, midi_note):
        """Stop a note (steel pan notes naturally decay)."""
        pass

    def all_notes_off(self):
        """Stop all playing notes."""
        self.pygame.mixer.stop()

    def get_note_range(self):
        """Return the MIDI note range."""
        return MIDI_LOW, MIDI_HIGH


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PaniPuri calibrated steel pan synthesizer"
    )
    parser.add_argument(
        '--note', help="Play a single note (e.g., C5, F#4)"
    )
    parser.add_argument(
        '--calibration', default=CALIBRATION_PATH,
        help="Path to calibration.json"
    )

    args = parser.parse_args()

    import pygame
    pygame.init()
    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)

    synth = SynthSteelPan(calibration_path=args.calibration)

    if args.note:
        # Parse note name to MIDI number
        note_str = args.note.upper().replace('#', '#')
        # Simple parser
        note_map = {
            'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
            'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11,
            'DB': 1, 'EB': 3, 'GB': 6, 'AB': 8, 'BB': 10,
        }
        # Extract note name and octave
        if len(note_str) >= 3 and note_str[1] in '#B' and note_str[1:2] != '':
            name = note_str[:2]
            octave = int(note_str[2:])
        else:
            name = note_str[0]
            octave = int(note_str[1:])

        semitone = note_map.get(name)
        if semitone is None:
            print(f"Unknown note: {args.note}")
            return
        midi_note = (octave + 1) * 12 + semitone

        print(f"Playing {args.note} (MIDI {midi_note}, {midi_to_freq(midi_note):.1f} Hz)")
        synth.note_on(midi_note, 100)
        pygame.time.wait(2000)
    else:
        # Play a test scale
        import time
        print("Playing test scale: C4 D4 E4 F4 G4 A4 B4 C5")
        scale = [60, 62, 64, 65, 67, 69, 71, 72]
        for midi_note in scale:
            name = midi_to_display(midi_note)
            print(f"  {name}", end="  ", flush=True)
            synth.note_on(midi_note, 100)
            time.sleep(0.4)
        print()
        pygame.time.wait(1500)

    pygame.quit()


if __name__ == '__main__':
    main()
