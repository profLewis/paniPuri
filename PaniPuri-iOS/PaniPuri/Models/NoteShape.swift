import Foundation

/// Represents the geometric shape data for a single note on the steel pan.
/// Decoded from entries in `note_shapes.json`.
struct NoteShape: Codable, Identifiable {

    /// Unique index identifier (e.g. "I4", "O7").
    let idx: String

    /// Musical note name (e.g. "Eb", "F#", "C").
    let name: String

    /// Ring position on the pan — "inner" or "outer".
    let ring: String

    /// Octave number for this note.
    let octave: Int

    /// Path coordinates defining the groove boundary.
    /// Each element is a two-element array `[x, y]`.
    let grove_path: [[Double]]

    /// Path coordinates defining the pan (outer) boundary.
    /// Each element is a two-element array `[x, y]`.
    let pan_path: [[Double]]

    /// Centroid of the note region as `[x, y]`.
    let centroid: [Double]

    // MARK: - Identifiable

    var id: String { idx }

    // MARK: - Computed Properties

    /// MIDI note number derived from the note name and octave.
    var midiNote: Int {
        NoteIdentity.toMidi(name: name, octave: octave)
    }

    /// Audio sample file name stem (e.g. "Ds6") for this note.
    var sampleFileName: String {
        NoteIdentity.sampleFileName(name: name, octave: octave)
    }

    // MARK: - Loading

    /// Loads all note shapes from the bundle's `note_shapes.json`.
    /// Returns an empty array if the file is missing or cannot be decoded.
    static func loadAll() -> [NoteShape] {
        guard let url = Bundle.main.url(forResource: "note_shapes", withExtension: "json") else {
            print("NoteShape: note_shapes.json not found in bundle")
            return []
        }
        do {
            let data = try Data(contentsOf: url)
            let shapes = try JSONDecoder().decode([NoteShape].self, from: data)
            return shapes
        } catch {
            print("NoteShape: failed to decode note_shapes.json — \(error)")
            return []
        }
    }
}
