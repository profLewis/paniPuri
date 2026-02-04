import SwiftUI

struct SteelPanView: View {
    let noteShapes: [NoteShape]
    let activeNotes: Set<String>
    let onNotePlayed: (NoteShape) -> Void

    var body: some View {
        GeometryReader { geometry in
            let size = geometry.size
            let scale = min(size.width, size.height) / 40.0
            let centerX = size.width / 2.0
            let centerY = size.height / 2.0

            Canvas { context, canvasSize in
                // 1. Draw the bowl circle with radial gradient
                let bowlRadius = 19.0 * scale
                let bowlCenter = CGPoint(x: centerX, y: centerY)
                let bowlRect = CGRect(
                    x: centerX - bowlRadius,
                    y: centerY - bowlRadius,
                    width: bowlRadius * 2,
                    height: bowlRadius * 2
                )

                let bowlGradient = Gradient(colors: [
                    Color(red: 0.290, green: 0.290, blue: 0.290), // #4a4a4a
                    Color(red: 0.165, green: 0.165, blue: 0.165), // #2a2a2a
                    Color(red: 0.102, green: 0.102, blue: 0.102)  // #1a1a1a
                ])

                context.fill(
                    Circle().path(in: bowlRect),
                    with: .radialGradient(
                        bowlGradient,
                        center: bowlCenter,
                        startRadius: 0,
                        endRadius: bowlRadius
                    )
                )

                // 2. Draw each note shape
                for noteShape in noteShapes {
                    let isActive = activeNotes.contains(noteShape.idx)
                    let ringColors = colorsForRing(noteShape.ring, isActive: isActive)

                    // Draw groove polygon
                    let groovePath = polygonPath(
                        from: noteShape.grove_path,
                        scale: scale,
                        centerX: centerX,
                        centerY: centerY
                    )
                    context.fill(
                        groovePath,
                        with: .color(Color(red: 0.102, green: 0.102, blue: 0.102)) // #1a1a1a
                    )
                    context.stroke(
                        groovePath,
                        with: .color(Color(red: 0.2, green: 0.2, blue: 0.2)), // #333333
                        lineWidth: 1
                    )

                    // Draw pan polygon (the note face)
                    let panPath = polygonPath(
                        from: noteShape.pan_path,
                        scale: scale,
                        centerX: centerX,
                        centerY: centerY
                    )
                    context.fill(panPath, with: .color(ringColors.fill))
                    context.stroke(panPath, with: .color(ringColors.stroke), lineWidth: 1.5)

                    // Draw note label at centroid
                    if noteShape.centroid.count >= 2 {
                        let labelX = centerX + noteShape.centroid[0] * scale
                        let labelY = centerY + noteShape.centroid[1] * scale
                        let labelPoint = CGPoint(x: labelX, y: labelY)

                        let fontSize = max(8, scale * 1.2)
                        let label = Text(noteShape.name)
                            .font(.system(size: fontSize, weight: .semibold))
                            .foregroundColor(.white)

                        context.draw(label, at: labelPoint)
                    }
                }
            }
            .overlay {
                // Use the existing PanTouchView for multi-touch handling
                PanTouchView(
                    noteShapes: noteShapes,
                    viewBoxSize: 40.0,
                    onNotePlayed: onNotePlayed
                )
            }
        }
    }

    // MARK: - Ring Colors

    private struct RingColors {
        let fill: Color
        let stroke: Color
    }

    private func colorsForRing(_ ring: String, isActive: Bool) -> RingColors {
        let multiplier: Double = isActive ? 1.5 : 1.0

        switch ring {
        case "outer":
            return RingColors(
                fill: Color(
                    red: min(0.753 * multiplier, 1.0),
                    green: min(0.224 * multiplier, 1.0),
                    blue: min(0.169 * multiplier, 1.0)
                ), // #c0392b
                stroke: Color(
                    red: min(0.906 * multiplier, 1.0),
                    green: min(0.298 * multiplier, 1.0),
                    blue: min(0.235 * multiplier, 1.0)
                )  // #e74c3c
            )
        case "central":
            return RingColors(
                fill: Color(
                    red: min(0.141 * multiplier, 1.0),
                    green: min(0.443 * multiplier, 1.0),
                    blue: min(0.639 * multiplier, 1.0)
                ), // #2471a3
                stroke: Color(
                    red: min(0.204 * multiplier, 1.0),
                    green: min(0.596 * multiplier, 1.0),
                    blue: min(0.859 * multiplier, 1.0)
                )  // #3498db
            )
        case "inner":
            return RingColors(
                fill: Color(
                    red: min(0.118 * multiplier, 1.0),
                    green: min(0.518 * multiplier, 1.0),
                    blue: min(0.286 * multiplier, 1.0)
                ), // #1e8449
                stroke: Color(
                    red: min(0.180 * multiplier, 1.0),
                    green: min(0.800 * multiplier, 1.0),
                    blue: min(0.443 * multiplier, 1.0)
                )  // #2ecc71
            )
        default:
            return RingColors(
                fill: Color(red: 0.3, green: 0.3, blue: 0.3),
                stroke: Color(red: 0.5, green: 0.5, blue: 0.5)
            )
        }
    }

    // MARK: - Path Helpers

    /// Converts an array of [x, y] coordinate pairs into a closed SwiftUI Path,
    /// applying the scale and center offset for screen coordinates.
    private func polygonPath(
        from points: [[Double]],
        scale: Double,
        centerX: Double,
        centerY: Double
    ) -> Path {
        Path { path in
            guard let first = points.first, first.count >= 2 else { return }
            path.move(to: CGPoint(
                x: centerX + first[0] * scale,
                y: centerY + first[1] * scale
            ))
            for point in points.dropFirst() {
                guard point.count >= 2 else { continue }
                path.addLine(to: CGPoint(
                    x: centerX + point[0] * scale,
                    y: centerY + point[1] * scale
                ))
            }
            path.closeSubpath()
        }
    }
}

#Preview {
    SteelPanView(
        noteShapes: [],
        activeNotes: [],
        onNotePlayed: { _ in }
    )
    .frame(width: 350, height: 350)
    .background(Color.black)
}
