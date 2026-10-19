// README 영상 자막: "이름: 말" 한 줄을 반투명 띠 위에 그린 PNG를 만든다(게임 채팅처럼 이름은 주황색).
//   xcrun swift caption.swift <out.png> <width> <name> <text>
import AppKit

let args = CommandLine.arguments
guard args.count == 5, let width = Double(args[2]) else {
    FileHandle.standardError.write("usage: caption.swift <out.png> <width> <name> <text>\n".data(using: .utf8)!)
    exit(2)
}
let font = NSFont.systemFont(ofSize: 26, weight: .semibold)
let line = NSMutableAttributedString(
    string: args[3] + ": ",
    attributes: [.font: font, .foregroundColor: NSColor(calibratedRed: 1.0, green: 0.62, blue: 0.2, alpha: 1)])
line.append(NSAttributedString(string: args[4], attributes: [.font: font, .foregroundColor: NSColor.white]))
let pad = 18.0
let box = line.boundingRect(
    with: NSSize(width: width - 4 * pad, height: 1000), options: [.usesLineFragmentOrigin, .usesFontLeading])
let height = ceil(box.height) + 2 * pad
guard let rep = NSBitmapImageRep(
    bitmapDataPlanes: nil, pixelsWide: Int(width), pixelsHigh: Int(height), bitsPerSample: 8, samplesPerPixel: 4,
    hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)
else { exit(1) }
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
let band = NSRect(x: pad, y: 0, width: width - 2 * pad, height: height)
NSColor(calibratedWhite: 0, alpha: 0.62).setFill()
NSBezierPath(roundedRect: band, xRadius: 10, yRadius: 10).fill()
line.draw(with: NSRect(x: 2 * pad, y: pad, width: width - 4 * pad, height: box.height), options: [.usesLineFragmentOrigin, .usesFontLeading])
NSGraphicsContext.restoreGraphicsState()
guard let png = rep.representation(using: .png, properties: [:]) else { exit(1) }
try png.write(to: URL(fileURLWithPath: args[1]))
