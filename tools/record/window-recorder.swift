// README 영상: 한 프로세스의 게임 창 하나만 녹화한다(ScreenCaptureKit). 창의 내용 자체를 찍으므로 다른 창에
// 가려져도 게임 화면만 담기고, 화면의 다른 것은 담기지 않는다. 표준 입력이 닫히거나 "q"가 오면 마무리한다.
//   record-window <pid> <out.mp4> [fps]
import AppKit
import AVFoundation
import CoreMedia
import Foundation
import ScreenCaptureKit

final class Writer: NSObject, SCStreamOutput, SCStreamDelegate {
    let writer: AVAssetWriter
    let input: AVAssetWriterInput
    var started = false
    // 진단: 10초마다 받은 프레임을 상태별로 센다(표준 오류 → recorder.log).
    var counts: [Int: Int] = [:]
    var lastReport = Date()

    init(url: URL, width: Int, height: Int) throws {
        writer = try AVAssetWriter(outputURL: url, fileType: .mp4)
        // 10초마다 조각을 써 두면 녹화 중에도(또는 비정상 종료 뒤에도) 파일을 읽을 수 있다.
        writer.movieFragmentInterval = CMTime(seconds: 10, preferredTimescale: 600)
        input = AVAssetWriterInput(mediaType: .video, outputSettings: [
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: width,
            AVVideoHeightKey: height,
            AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 4_000_000],
        ])
        input.expectsMediaDataInRealTime = true
        writer.add(input)
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer buffer: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen, buffer.isValid,
              let attachments = CMSampleBufferGetSampleAttachmentsArray(buffer, createIfNecessary: false) as? [[SCStreamFrameInfo: Any]],
              let raw = attachments.first?[.status] as? Int
        else { return }
        counts[raw, default: 0] += 1
        if Date().timeIntervalSince(lastReport) >= 10 {
            let line = counts.sorted { $0.key < $1.key }.map { "status\($0.key)=\($0.value)" }.joined(separator: " ")
            FileHandle.standardError.write("\(Int(Date().timeIntervalSince1970)) frames \(line)\n".data(using: .utf8)!)
            counts = [:]
            lastReport = Date()
        }
        guard SCFrameStatus(rawValue: raw) == .complete else { return }
        if !started {
            writer.startWriting()
            writer.startSession(atSourceTime: CMSampleBufferGetPresentationTimeStamp(buffer))
            started = true
            print("started \(Date().timeIntervalSince1970)")
            fflush(stdout)
        }
        if input.isReadyForMoreMediaData { input.append(buffer) }
        // 쓰기가 실패하면 그 뒤 프레임은 버려진다(실게임 녹화가 234초에서 말없이 멈췄다). 알리고 끝내면
        // 부른 쪽이 새 파일로 이어 간다.
        if writer.status == .failed {
            print("failed \(writer.error?.localizedDescription ?? "unknown")")
            fflush(stdout)
            exit(5)
        }
    }

    // 시스템이 스트림을 끊으면(실게임 녹화 중 110초 만에 끊겼다) 지금까지를 마무리하고 알린다.
    // 녹화를 이어 가는 것은 부른 쪽이 새 파일로 다시 시작해서 한다.
    func stream(_ stream: SCStream, didStopWithError error: Error) {
        print("stopped \(error.localizedDescription)")
        fflush(stdout)
        input.markAsFinished()
        writer.finishWriting { exit(4) }
    }
}

@main
struct RecordWindow {
    static func main() async throws {
        // 명령줄 도구는 그래픽 세션을 직접 열어야 ScreenCaptureKit이 동작한다.
        _ = NSApplication.shared
        let args = CommandLine.arguments
        guard args.count >= 3, let pid = Int32(args[1]) else {
            FileHandle.standardError.write("usage: record-window <pid> <out.mp4> [fps]\n".data(using: .utf8)!)
            exit(2)
        }
        let fps = args.count > 3 ? Int32(args[3]) ?? 30 : 30
        let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: false)
        let windows = content.windows.filter { $0.owningApplication?.processID == pid && $0.frame.width >= 640 }
        guard let window = windows.max(by: { $0.frame.width * $0.frame.height < $1.frame.width * $1.frame.height }) else {
            FileHandle.standardError.write("no window for pid \(pid)\n".data(using: .utf8)!)
            exit(3)
        }
        let config = SCStreamConfiguration()
        config.width = 1280
        config.height = 720
        // 창에는 위쪽에 제목 표시줄이 있다. 게임이 그리는 아래쪽 그림만 찍는다(포인트, 창의 왼쪽 위 기준).
        let picture = CGSize(width: window.frame.width, height: window.frame.width * 9 / 16)
        config.sourceRect = CGRect(x: 0, y: window.frame.height - picture.height, width: picture.width, height: picture.height)
        config.minimumFrameInterval = CMTime(value: 1, timescale: fps)
        config.showsCursor = false
        let writer = try Writer(url: URL(fileURLWithPath: args[2]), width: config.width, height: config.height)
        let stream = SCStream(filter: SCContentFilter(desktopIndependentWindow: window), configuration: config, delegate: writer)
        try stream.addStreamOutput(writer, type: .screen, sampleHandlerQueue: DispatchQueue(label: "frames"))
        try await stream.startCapture()
        // 멈추라는 신호: 표준 입력에서 "q" 또는 입력이 닫힘.
        await withCheckedContinuation { (done: CheckedContinuation<Void, Never>) in
            DispatchQueue.global().async {
                while let line = readLine(), !line.hasPrefix("q") {}
                done.resume()
            }
        }
        try await stream.stopCapture()
        writer.input.markAsFinished()
        await writer.writer.finishWriting()
        print("finished \(writer.writer.status.rawValue)")
    }
}
