import Foundation

/// Static utility struct for note name conversions, MIDI calculations,
/// and sample file name resolution.
struct NoteIdentity {

    // MARK: - Semitone Mapping

    /// Maps note names (including enharmonic equivalents) to semitone offsets
    /// within an octave (C = 0 ... B = 11).
    static let NOTE_TO_SEMITONE: [String: Int] = [
        "C":  0,
        "C#": 1,  "Db": 1,
        "D":  2,
        "D#": 3,  "Eb": 3,
        "E":  4,  "Fb": 4,
        "F":  5,  "E#": 5,
        "F#": 6,  "Gb": 6,
        "G":  7,
        "G#": 8,  "Ab": 8,
        "A":  9,
        "A#": 10, "Bb": 10,
        "B":  11, "Cb": 11
    ]

    // MARK: - Sample Name Mapping

    /// Maps note names to the stem used in audio sample file names.
    /// Sharps are represented with a lowercase 's' (e.g. "C#" -> "Cs").
    /// Flats resolve to their enharmonic sharp equivalent.
    static let NAME_TO_SAMPLE: [String: String] = [
        "C":  "C",
        "C#": "Cs", "Db": "Cs",
        "D":  "D",
        "D#": "Ds", "Eb": "Ds",
        "E":  "E",  "Fb": "E",
        "F":  "F",  "E#": "F",
        "F#": "Fs", "Gb": "Fs",
        "G":  "G",
        "G#": "Gs", "Ab": "Gs",
        "A":  "A",
        "A#": "As", "Bb": "As",
        "B":  "B",  "Cb": "B"
    ]

    // MARK: - Conversions

    /// Converts a note name and octave to a MIDI note number.
    /// Uses the standard formula: (octave + 1) * 12 + semitone.
    /// - Parameters:
    ///   - name: Note name such as "C", "F#", "Eb".
    ///   - octave: Octave number (e.g. 4 for middle C).
    /// - Returns: MIDI note number (e.g. 60 for C4).
    static func toMidi(name: String, octave: Int) -> Int {
        let semitone = NOTE_TO_SEMITONE[name] ?? 0
        return (octave + 1) * 12 + semitone
    }

    /// Converts a MIDI note number to its frequency in Hz.
    /// Uses equal-temperament tuning with A4 = 440 Hz.
    /// - Parameter midi: MIDI note number (0-127).
    /// - Returns: Frequency in Hz.
    static func midiToFreq(_ midi: Int) -> Double {
        440.0 * pow(2.0, Double(midi - 69) / 12.0)
    }

    /// Builds the sample file name for a given note name and octave.
    /// For example, ("F#", 4) -> "Fs4", ("Eb", 6) -> "Ds6".
    /// - Parameters:
    ///   - name: Note name such as "C", "F#", "Eb".
    ///   - octave: Octave number.
    /// - Returns: Sample file name stem (without extension).
    static func sampleFileName(name: String, octave: Int) -> String {
        let sample = NAME_TO_SAMPLE[name] ?? name
        return "\(sample)\(octave)"
    }
}
