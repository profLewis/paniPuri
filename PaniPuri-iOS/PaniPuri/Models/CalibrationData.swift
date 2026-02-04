import Foundation

/// Per-note calibration parameters extracted from recorded steel pan samples.
/// All values are `Double` to support interpolation between calibrated notes.
struct CalibrationNote: Codable {
    let freq: Double
    let attack: Double
    let decay: Double
    let sustain: Double
    let release: Double
    let sub_bass: Double
    let fundamental: Double
    let harmonic2: Double
    let harmonic3: Double
    let harmonic4: Double
    let filter: Double
    let brightness: Double
}

/// Default synthesis parameters used when a note has no exact calibration match
/// or as a fallback baseline.
struct CalibrationDefaults: Codable {
    let attack: Double
    let decay: Double
    let sustain: Double
    let release: Double
    let sub_bass: Double
    let fundamental: Double
    let harmonic2: Double
    let harmonic3: Double
    let harmonic4: Double
    let filter: Double
    let brightness: Double
    let detune: Double
}

/// Top-level container for `calibration.json`, holding per-note entries
/// keyed by MIDI note number (as a string) and a set of defaults.
struct CalibrationData: Codable {

    /// Per-note calibration entries keyed by MIDI note number string (e.g. "53").
    let notes: [String: CalibrationNote]

    /// Default/fallback synthesis parameters.
    let defaults: CalibrationDefaults

    // MARK: - Loading

    /// Loads calibration data from the bundle's `calibration.json`.
    /// Falls back to empty notes and zeroed defaults if the file is
    /// missing or cannot be decoded.
    static func load() -> CalibrationData {
        guard let url = Bundle.main.url(forResource: "calibration", withExtension: "json") else {
            print("CalibrationData: calibration.json not found in bundle")
            return CalibrationData.empty
        }
        do {
            let data = try Data(contentsOf: url)
            let cal = try JSONDecoder().decode(CalibrationData.self, from: data)
            return cal
        } catch {
            print("CalibrationData: failed to decode calibration.json — \(error)")
            return CalibrationData.empty
        }
    }

    // MARK: - Parameter Lookup

    /// Returns calibration parameters for the given MIDI note.
    ///
    /// If an exact match exists in `notes`, it is returned directly.
    /// Otherwise the two nearest calibrated MIDI notes (one below, one above)
    /// are found and all parameters are linearly interpolated between them.
    /// If only one neighbour exists (note is below the lowest or above the
    /// highest calibrated note), that neighbour's values are returned as-is.
    func params(forMidi midi: Int) -> CalibrationNote {
        let key = String(midi)

        // Exact match
        if let exact = notes[key] {
            return exact
        }

        // Collect all calibrated MIDI numbers, sorted.
        let calibratedMidis = notes.keys.compactMap { Int($0) }.sorted()

        guard !calibratedMidis.isEmpty else {
            // No calibration data at all — synthesize from defaults.
            let freq = NoteIdentity.midiToFreq(midi)
            return CalibrationNote(
                freq: freq,
                attack: defaults.attack,
                decay: defaults.decay,
                sustain: defaults.sustain,
                release: defaults.release,
                sub_bass: defaults.sub_bass,
                fundamental: defaults.fundamental,
                harmonic2: defaults.harmonic2,
                harmonic3: defaults.harmonic3,
                harmonic4: defaults.harmonic4,
                filter: defaults.filter,
                brightness: defaults.brightness
            )
        }

        // Find the closest lower and upper calibrated notes.
        var lower: Int?
        var upper: Int?

        for m in calibratedMidis {
            if m < midi {
                lower = m
            } else if m > midi {
                upper = m
                break
            }
        }

        // Only one side available — clamp to that neighbour.
        guard let lo = lower, let loNote = notes[String(lo)] else {
            // midi is at or below the lowest calibrated note.
            if let up = upper, let upNote = notes[String(up)] {
                return upNote
            }
            return notes[String(calibratedMidis.first!)]!
        }

        guard let hi = upper, let hiNote = notes[String(hi)] else {
            // midi is at or above the highest calibrated note.
            return loNote
        }

        // Linear interpolation factor.
        let t = Double(midi - lo) / Double(hi - lo)

        func lerp(_ a: Double, _ b: Double) -> Double {
            a + (b - a) * t
        }

        return CalibrationNote(
            freq: NoteIdentity.midiToFreq(midi),
            attack: lerp(loNote.attack, hiNote.attack),
            decay: lerp(loNote.decay, hiNote.decay),
            sustain: lerp(loNote.sustain, hiNote.sustain),
            release: lerp(loNote.release, hiNote.release),
            sub_bass: lerp(loNote.sub_bass, hiNote.sub_bass),
            fundamental: lerp(loNote.fundamental, hiNote.fundamental),
            harmonic2: lerp(loNote.harmonic2, hiNote.harmonic2),
            harmonic3: lerp(loNote.harmonic3, hiNote.harmonic3),
            harmonic4: lerp(loNote.harmonic4, hiNote.harmonic4),
            filter: lerp(loNote.filter, hiNote.filter),
            brightness: lerp(loNote.brightness, hiNote.brightness)
        )
    }

    // MARK: - Private

    /// Empty fallback instance with zeroed defaults.
    private static let empty = CalibrationData(
        notes: [:],
        defaults: CalibrationDefaults(
            attack: 0, decay: 0, sustain: 0, release: 0,
            sub_bass: 0, fundamental: 100, harmonic2: 0,
            harmonic3: 0, harmonic4: 0, filter: 2000,
            brightness: 50, detune: 0
        )
    )
}
