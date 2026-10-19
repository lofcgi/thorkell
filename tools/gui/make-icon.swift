// Thorkell.app 아이콘 원본(1024px PNG)을 그린다: 어두운 바탕에 룬 ᚦ(Thorkell의 Th).
// 사용: xcrun swift tools/gui/make-icon.swift <출력.png>
import AppKit

let size = 1024
let output = CommandLine.arguments.dropFirst().first ?? "icon.png"
guard let bitmap = NSBitmapImageRep(
    bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size, bitsPerSample: 8, samplesPerPixel: 4,
    hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0
) else { fatalError("bitmap") }
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)

let canvas = NSRect(x: 0, y: 0, width: size, height: size)
let plate = NSBezierPath(roundedRect: canvas.insetBy(dx: 100, dy: 100), xRadius: 185, yRadius: 185)
NSGradient(colors: [
    NSColor(calibratedRed: 0.13, green: 0.20, blue: 0.27, alpha: 1),
    NSColor(calibratedRed: 0.05, green: 0.08, blue: 0.11, alpha: 1),
])!.draw(in: plate, angle: -90)
NSColor(calibratedRed: 0.80, green: 0.62, blue: 0.32, alpha: 1).setStroke()
plate.lineWidth = 18
plate.stroke()

let style = NSMutableParagraphStyle()
style.alignment = .center
let rune = NSAttributedString(string: "ᚦ", attributes: [
    .font: NSFont.systemFont(ofSize: 560, weight: .bold),
    .foregroundColor: NSColor(calibratedRed: 0.93, green: 0.88, blue: 0.78, alpha: 1),
    .paragraphStyle: style,
])
let height = rune.size().height
rune.draw(in: NSRect(x: 0, y: (CGFloat(size) - height) / 2 - 10, width: CGFloat(size), height: height))

NSGraphicsContext.restoreGraphicsState()
guard let png = bitmap.representation(using: .png, properties: [:]) else { fatalError("png") }
try png.write(to: URL(fileURLWithPath: output))
