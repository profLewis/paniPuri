import SwiftUI
import UIKit

/// SwiftUI wrapper around `PanTouchUIView`, providing multi-touch hit testing
/// against the steel pan note geometry.
struct PanTouchView: UIViewRepresentable {

    let noteShapes: [NoteShape]
    var viewBoxSize: CGFloat = 40.0
    let onNotePlayed: (NoteShape) -> Void

    func makeUIView(context: Context) -> PanTouchUIView {
        let view = PanTouchUIView()
        view.noteShapes = noteShapes
        view.viewBoxSize = viewBoxSize
        view.onNotePlayed = onNotePlayed
        view.isMultipleTouchEnabled = true
        view.backgroundColor = .clear
        return view
    }

    func updateUIView(_ uiView: PanTouchUIView, context: Context) {
        uiView.noteShapes = noteShapes
        uiView.viewBoxSize = viewBoxSize
        uiView.onNotePlayed = onNotePlayed
    }
}

/// Custom UIView subclass that handles multi-touch events and performs
/// hit testing against steel pan note polygons.
class PanTouchUIView: UIView {

    var noteShapes: [NoteShape] = []
    var viewBoxSize: CGFloat = 40.0
    var onNotePlayed: ((NoteShape) -> Void)?

    /// Tracks which note each active touch is currently over, keyed by touch
    /// identity. Prevents retriggering the same note on `touchesMoved`.
    private var touchNoteMap: [UITouch: String] = [:]

    /// Note shapes sorted for hit-test priority: inner ring first, then
    /// anything that is not outer (i.e. central), then outer ring.
    private var sortedShapes: [NoteShape] {
        let inner = noteShapes.filter { $0.ring == "inner" }
        let central = noteShapes.filter { $0.ring != "inner" && $0.ring != "outer" }
        let outer = noteShapes.filter { $0.ring == "outer" }
        return inner + central + outer
    }

    // MARK: - Coordinate Conversion

    /// Converts a screen point to the pan coordinate system used by the
    /// SVG / JSON geometry (origin at center, viewBox units).
    private func panCoordinates(for point: CGPoint) -> (Double, Double) {
        let scale = min(bounds.width, bounds.height) / viewBoxSize
        let panX = Double((point.x - bounds.midX) / scale)
        let panY = Double((point.y - bounds.midY) / scale)
        return (panX, panY)
    }

    // MARK: - Hit Testing

    /// Returns the first note shape whose `pan_path` polygon contains the
    /// given pan-coordinate point, respecting ring priority order.
    private func hitTest(panX: Double, panY: Double) -> NoteShape? {
        for shape in sortedShapes {
            if pointInPolygon(x: panX, y: panY, polygon: shape.pan_path) {
                return shape
            }
        }
        return nil
    }

    /// Processes a set of touches, triggering `onNotePlayed` only when a
    /// finger moves to a new note.
    private func handleTouches(_ touches: Set<UITouch>) {
        for touch in touches {
            let point = touch.location(in: self)
            let (panX, panY) = panCoordinates(for: point)

            if let shape = hitTest(panX: panX, panY: panY) {
                let previousNote = touchNoteMap[touch]
                if previousNote != shape.idx {
                    touchNoteMap[touch] = shape.idx
                    onNotePlayed?(shape)
                }
            } else {
                // Finger moved off all notes
                touchNoteMap[touch] = nil
            }
        }
    }

    // MARK: - Touch Events

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        handleTouches(touches)
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {
        handleTouches(touches)
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        for touch in touches {
            touchNoteMap.removeValue(forKey: touch)
        }
    }

    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {
        for touch in touches {
            touchNoteMap.removeValue(forKey: touch)
        }
    }
}
