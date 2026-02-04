import Foundation

/// Ray-casting algorithm for point-in-polygon testing.
/// polygon is an array of [x, y] coordinate pairs.
func pointInPolygon(x: Double, y: Double, polygon: [[Double]]) -> Bool {
    var inside = false
    let n = polygon.count
    guard n > 2 else { return false }
    var j = n - 1
    for i in 0..<n {
        let xi = polygon[i][0], yi = polygon[i][1]
        let xj = polygon[j][0], yj = polygon[j][1]
        if ((yi > y) != (yj > y)) &&
           (x < (xj - xi) * (y - yi) / (yj - yi) + xi) {
            inside.toggle()
        }
        j = i
    }
    return inside
}
