// Thorkell.app: 토르켈과 같이 플레이하는 창.
// 엔진은 brain의 `thorkell play --ui jsonl`이다. 이 앱은 그 표준 입출력의 JSON 줄로 상태를 받고 명령을 보낸다.
// 빌드: tools/gui/build.sh (레포 경로를 Info.plist의 ThorkellRepo에 넣는다)
// 점검용: Thorkell.app/Contents/MacOS/Thorkell --selftest  (창 없이 점검 모드를 돌리고 결과를 출력)
// 개발용: Thorkell.app/Contents/MacOS/Thorkell --snapshot 경로.png  (예시 대화를 채운 창을 그림으로 저장하고 종료)

import AppKit
import SwiftUI

@main
enum Main {
    static func main() {
        signal(SIGPIPE, SIG_IGN)  // 엔진이 먼저 끝난 뒤 파이프에 쓰더라도 앱이 죽지 않게
        if CommandLine.arguments.contains("--selftest") {
            MainActor.assumeIsolated { SelfTest.run() }
            return
        }
        ThorkellApp.main()
    }
}

struct ThorkellApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate

    var body: some Scene {
        Window("토르켈", id: "main") {
            ContentView().environmentObject(delegate.engine)
        }
        .defaultSize(width: 780, height: 700)
    }
}

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    let engine = Engine(repo: Engine.repoFromBundle())

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    func applicationDidFinishLaunching(_ notification: Notification) {
        guard let path = Snapshot.path else { return }
        // cacheDisplay는 흰 바탕으로 그리므로, 확인용 그림은 라이트 모드로 그린다.
        NSApp.appearance = NSAppearance(named: .aqua)
        engine.loadDemo()
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { Snapshot.save(to: path) }
    }

    // 창을 닫거나 종료하면 토르켈을 먼저 정리한다(캐릭터 저장, 격리 확인). 내 게임 창은 그대로 둔다.
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard engine.running, !engine.demo else { return .terminateNow }
        engine.onEnded = { NSApp.reply(toApplicationShouldTerminate: true) }
        engine.stop()
        DispatchQueue.main.asyncAfter(deadline: .now() + 60) { [engine] in
            if engine.running { engine.kill() }
            NSApp.reply(toApplicationShouldTerminate: true)
        }
        return .terminateLater
    }
}

// MARK: - 엔진

struct Entry: Identifiable {
    enum Kind: String { case thorkell, me, heard, status, step, hint, decision, warn, error, isolationOK, isolationBad, tech }
    let id = UUID()
    let kind: Kind
    let text: String
}

@MainActor
final class Engine: ObservableObject {
    enum Phase: String {
        case idle, checking, ready, waitingServer = "waiting_server", startingBot = "starting_bot"
        case connected, stopping, finished, failed
    }

    @Published private(set) var phase: Phase = .idle
    @Published private(set) var phaseText = "시작 전"
    @Published private(set) var entries: [Entry] = []
    @Published private(set) var hint = ""
    @Published private(set) var whereText = ""
    @Published private(set) var running = false
    @Published var passwordPrompt: String?

    let repo: URL?
    var onEnded: (() -> Void)?
    private(set) var demo = false
    private var process: Process?
    private var input: FileHandle?
    private var outBuffer = Data()
    private var errBuffer = Data()

    init(repo: URL?) { self.repo = repo }

    static func repoFromBundle() -> URL? {
        guard let path = Bundle.main.object(forInfoDictionaryKey: "ThorkellRepo") as? String else { return nil }
        return URL(fileURLWithPath: path)
    }

    var usesModels: Bool {
        guard let repo else { return false }
        return FileManager.default.fileExists(atPath: repo.appendingPathComponent(".env").path)
    }

    func start(world: String, checkOnly: Bool, newWorld: Bool = false, english: Bool = false) {
        guard !running else { return }
        guard let repo else {
            append(.error, "앱에 레포 경로가 없습니다. 레포에서 tools/gui/build.sh로 앱을 다시 만들어 주세요.")
            phase = .failed
            return
        }
        entries.removeAll()
        hint = ""
        whereText = ""
        var args = ["uv", "run"]
        if usesModels { args += ["--env-file", "../.env"] }
        args += ["thorkell", "play", "--rehearsal", world, "--ui", "jsonl", "--build"]
        // 영어: 두 게임과 리더의 말, 토르켈의 생각·말을 모두 영어로(README 영상).
        if usesModels { args += ["--config", english ? "thorkell.play.en.toml" : "thorkell.play.toml"] }
        if checkOnly { args.append("--check") }
        if newWorld { args.append("--new") }  // 백업 월드 대신 이 이름으로 새 월드를 만들어 처음부터
        let brain = repo.appendingPathComponent("brain").path
        let command = "cd \(quote(brain)) && exec " + args.map(quote).joined(separator: " ")

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/zsh")
        process.arguments = ["-l", "-c", command]  // 로그인 셸: 터미널에서 쓰는 PATH(uv, dotnet)를 그대로 쓴다
        var environment = ProcessInfo.processInfo.environment
        environment["PYTHONUNBUFFERED"] = "1"
        process.environment = environment
        let out = Pipe(), err = Pipe(), inp = Pipe()
        process.standardOutput = out
        process.standardError = err
        process.standardInput = inp
        out.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            Task { @MainActor in self?.consume(data, stderr: false) }
        }
        err.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            Task { @MainActor in self?.consume(data, stderr: true) }
        }
        process.terminationHandler = { [weak self] finished in
            out.fileHandleForReading.readabilityHandler = nil
            err.fileHandleForReading.readabilityHandler = nil
            let restOut = out.fileHandleForReading.readDataToEndOfFile()
            let restErr = err.fileHandleForReading.readDataToEndOfFile()
            let status = finished.terminationStatus
            Task { @MainActor in
                self?.consume(restOut, stderr: false)
                self?.consume(restErr, stderr: true)
                self?.ended(status)
            }
        }
        do {
            try process.run()
        } catch {
            append(.error, "엔진을 시작하지 못했습니다: \(error.localizedDescription)")
            phase = .failed
            return
        }
        self.process = process
        input = inp.fileHandleForWriting
        running = true
        phase = .checking
        phaseText = checkOnly ? "점검하는 중" : "준비하는 중"
    }

    func say(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, running else { return }
        append(.me, trimmed)
        send(["type": "say", "text": trimmed])
    }

    func askStatus() { send(["type": "status"]) }

    func stop() {
        guard running else { return }
        phaseText = "토르켈을 정리하는 중"
        send(["type": "quit"])
    }

    func kill() { process?.terminate() }

    func submitPassword(_ password: String) {
        passwordPrompt = nil
        send(["type": "password", "value": password])
    }

    private func send(_ message: [String: String]) {
        guard let input, let data = try? JSONSerialization.data(withJSONObject: message) else { return }
        do {
            try input.write(contentsOf: data + Data([0x0A]))
        } catch {
            append(.warn, "엔진에 보내지 못했습니다(이미 끝났을 수 있음).")
        }
    }

    private func consume(_ data: Data, stderr: Bool) {
        guard !data.isEmpty else { return }
        if stderr {
            errBuffer.append(data)
            while let line = takeLine(&errBuffer) { append(.tech, line) }
            return
        }
        outBuffer.append(data)
        while let line = takeLine(&outBuffer) {
            guard let json = try? JSONSerialization.jsonObject(with: Data(line.utf8)) as? [String: Any] else {
                append(.tech, line)
                continue
            }
            handle(json)
        }
    }

    private func takeLine(_ buffer: inout Data) -> String? {
        guard let newline = buffer.firstIndex(of: 0x0A) else { return nil }
        let line = String(decoding: buffer[buffer.startIndex..<newline], as: UTF8.self)
        buffer.removeSubrange(buffer.startIndex...newline)
        return line
    }

    private func handle(_ message: [String: Any]) {
        let text = message["text"] as? String ?? ""
        switch message["type"] as? String {
        case "phase":
            if let value = message["phase"] as? String, let next = Phase(rawValue: value) { phase = next }
            phaseText = text
        case "step": append(.step, text)
        case "hint":
            hint = text
            append(.hint, text)
        case "thorkell": append(.thorkell, text)
        case "heard": append(.heard, text)
        case "decision": append(.decision, "\(message["decision"] as? String ?? ""): \(text)")
        case "status": append(.status, text)
        case "warn": append(.warn, text)
        case "error": append(.error, text)
        case "isolation": append((message["ok"] as? Bool ?? false) ? .isolationOK : .isolationBad, text)
        case "need_password": passwordPrompt = text
        case "where": whereText = text  // 걷는 동안 계속 바뀌므로 로그가 아니라 머리글에 둔다
        default: append(.tech, text)
        }
    }

    private func ended(_ status: Int32) {
        running = false
        process = nil
        input = nil
        passwordPrompt = nil
        if status != 0 && phase != .failed {
            phase = .failed
            phaseText = "멈춤"
            append(.error, "엔진이 종료 코드 \(status)로 끝났습니다. '기술 로그'를 켜서 원인을 확인하세요.")
        } else if phase != .failed && phase != .ready {
            phase = .finished
        }
        onEnded?()
        onEnded = nil
    }

    // 개발용 화면 확인(--snapshot): 엔진 없이 접속 중인 모습을 채운다.
    func loadDemo() {
        demo = true
        running = true
        phase = .connected
        phaseText = "토르켈이 접속했습니다"
        hint = "토르켈 창을 띄웠습니다. 처음엔 시작 신전에 나타납니다."
        whereText = "토르켈은 내 북동쪽 40m에 있어요"
        append(.step, "✓ Steam 실행 중, 진짜 Valheim은 꺼져 있음")
        append(.step, "✓ 백업 20261002-122853에 'helloworld' 있음")
        append(.hint, "게임 창에서 캐릭터를 고르고 월드 'helloworld'를 선택한 뒤, '서버 시작'을 켜고 시작해 주세요.")
        append(.me, "토르켈, 이 도끼 받아")
        append(.decision, "adopt: 건네준 것 받기")
        append(.thorkell, "돌 도끼 받았어. 고마워!")
        append(.me, "나무 10개 캐줘")
        append(.thorkell, "나무 10개 해 올게.")
        append(.decision, "suspend: 그레이드워프가 공격해 와서 잠깐 멈춤")
        append(.thorkell, "그레이드워프가 날 공격했어!")
        append(.warn, "토르켈 체력 40%")
        append(.isolationOK, "확인: 내 실제 세이브·Steam Cloud·설정은 바뀌지 않았습니다.")
    }

    private func append(_ kind: Entry.Kind, _ text: String) {
        entries.append(Entry(kind: kind, text: text))
        if entries.count > 3000 { entries.removeFirst(entries.count - 3000) }
    }

    private func quote(_ text: String) -> String { "'" + text.replacingOccurrences(of: "'", with: "'\\''") + "'" }
}

// MARK: - 창

struct ContentView: View {
    @EnvironmentObject private var engine: Engine
    @AppStorage("world") private var world = "helloworld"
    @AppStorage("newWorld") private var newWorld = false
    @AppStorage("english") private var english = false
    @AppStorage("showDecisions") private var showDecisions = true
    @AppStorage("showTechnical") private var showTechnical = false
    @State private var message = ""
    @State private var password = ""

    private var quickLines: [String] {
        english
            ? ["Follow me", "Wait here", "Stop", "What are you doing?", "Take this", "Chop 10 wood"]
            : ["따라와", "기다려", "멈춰", "뭐해?", "이거 받아", "나무 10개 캐줘"]
    }

    var body: some View {
        VStack(spacing: 0) {
            header
            if engine.running, !engine.hint.isEmpty, engine.phase != .connected {
                Label(engine.hint, systemImage: "lightbulb.fill")
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(12)
                    .background(Color.yellow.opacity(0.18))
            }
            Divider()
            log
            Divider()
            footer
        }
        .frame(minWidth: 660, minHeight: 560)
        .sheet(isPresented: Binding(get: { engine.passwordPrompt != nil }, set: { _ in })) {
            PasswordSheet(prompt: engine.passwordPrompt ?? "", password: $password) {
                engine.submitPassword(password)
                password = ""
            } cancel: {
                engine.stop()
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                Text("토르켈").font(.title2.bold())
                StatusPill(phase: engine.phase, text: engine.phaseText)
                if engine.running, !engine.whereText.isEmpty {
                    Label(engine.whereText, systemImage: "location.fill")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button("Steam 열기") { NSWorkspace.shared.open(URL(fileURLWithPath: "/Applications/Steam.app")) }
                    .buttonStyle(.borderless)
            }
            HStack(spacing: 10) {
                Text("월드").foregroundStyle(.secondary)
                TextField("helloworld", text: $world).frame(width: 140).disabled(engine.running)
                Toggle("새 월드", isOn: $newWorld).toggleStyle(.checkbox).disabled(engine.running)
                    .help("백업한 내 월드 대신 이 이름으로 새 월드를 만들어 처음부터 같이 합니다(게임 메뉴에서 만듭니다)")
                Toggle("English", isOn: $english).toggleStyle(.checkbox)
                    .disabled(engine.running || !engine.usesModels)
                    .help("게임 화면, 리더의 말, 토르켈의 생각과 말을 영어로 합니다(모델이 있어야 합니다)")
                Text(engine.usesModels ? "두뇌: Gemini Flash + Jev" : "두뇌: 모델 없음(.env 없음)")
                    .font(.caption).foregroundStyle(.secondary)
                Spacer()
                Button("점검") { engine.start(world: world, checkOnly: true, newWorld: newWorld, english: english) }
                    .disabled(engine.running)
                Button("리허설 시작") {
                    engine.start(world: world, checkOnly: false, newWorld: newWorld, english: english)
                }
                    .buttonStyle(.borderedProminent)
                    .disabled(engine.running)
                Button("끝내기") { engine.stop() }
                    .disabled(!engine.running)
            }
            HStack(spacing: 14) {
                Toggle("결정 기록", isOn: $showDecisions)
                Toggle("기술 로그", isOn: $showTechnical)
            }
            .toggleStyle(.checkbox)
            .font(.caption)
        }
        .padding(14)
    }

    private var log: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 8) {
                    if engine.entries.isEmpty {
                        Text(engine.repo == nil
                             ? "앱에 레포 경로가 없습니다. tools/gui/build.sh로 다시 만들어 주세요."
                             : "‘리허설 시작’을 누르면 내 게임 창(리허설 복사본)이 뜨고 토르켈을 부를 준비를 합니다.\n진짜 Valheim은 꺼 두고 Steam은 켜 두세요.")
                            .foregroundStyle(.secondary)
                            .padding(.top, 24)
                    }
                    ForEach(visibleEntries) { entry in
                        EntryRow(entry: entry).id(entry.id)
                    }
                }
                .padding(14)
            }
            .onChange(of: engine.entries.count) { _, _ in
                if let last = visibleEntries.last {
                    withAnimation(.easeOut(duration: 0.15)) { proxy.scrollTo(last.id, anchor: .bottom) }
                }
            }
        }
    }

    private var visibleEntries: [Entry] {
        engine.entries.filter { entry in
            switch entry.kind {
            case .decision: return showDecisions
            case .tech: return showTechnical
            default: return true
            }
        }
    }

    private var footer: some View {
        let canTalk = engine.running && (engine.phase == .connected || engine.phase == .startingBot)
        return VStack(spacing: 8) {
            HStack(spacing: 6) {
                ForEach(quickLines, id: \.self) { line in
                    Button(line) { engine.say(line) }.disabled(!canTalk)
                }
                Spacer()
                Button("상태 묻기") { engine.askStatus() }.disabled(!canTalk)
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            HStack {
                TextField(canTalk ? "게임 채팅으로 말하면 됩니다. 여기에 써도 똑같이 전해집니다" : "토르켈이 접속하면 게임 채팅(또는 여기)으로 말을 걸 수 있습니다",
                          text: $message)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit(send)
                    .disabled(!canTalk)
                Button("보내기", action: send)
                    .keyboardShortcut(.return, modifiers: [.command])
                    .disabled(!canTalk || message.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .padding(14)
    }

    private func send() {
        engine.say(message)
        message = ""
    }
}

struct StatusPill: View {
    let phase: Engine.Phase
    let text: String

    var body: some View {
        HStack(spacing: 6) {
            Circle().fill(color).frame(width: 9, height: 9)
            Text(text).font(.callout)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 4)
        .background(color.opacity(0.14), in: Capsule())
    }

    private var color: Color {
        switch phase {
        case .idle, .stopping, .finished: return .gray
        case .checking, .startingBot: return .blue
        case .ready, .connected: return .green
        case .waitingServer: return .orange
        case .failed: return .red
        }
    }
}

struct EntryRow: View {
    let entry: Entry

    var body: some View {
        switch entry.kind {
        case .thorkell: bubble("토르켈", color: .blue.opacity(0.16), leading: true)
        case .status: bubble("토르켈(상태)", color: .blue.opacity(0.10), leading: true)
        case .me: bubble("나(이 창)", color: .gray.opacity(0.18), leading: false)
        case .heard: bubble("나(게임 채팅)", color: .green.opacity(0.16), leading: false)
        case .step: step
        case .hint:
            Label(entry.text, systemImage: "lightbulb").font(.callout)
                .padding(8).background(Color.yellow.opacity(0.14), in: RoundedRectangle(cornerRadius: 8))
        case .decision: Text("· " + entry.text).font(.caption.monospaced()).foregroundStyle(.secondary)
        case .warn: Label(entry.text, systemImage: "exclamationmark.triangle").foregroundStyle(.orange)
        case .error: Label(entry.text, systemImage: "xmark.octagon.fill").foregroundStyle(.red)
        case .isolationOK: Label(entry.text, systemImage: "lock.shield").foregroundStyle(.green)
        case .isolationBad: Label(entry.text, systemImage: "exclamationmark.shield").foregroundStyle(.red)
        case .tech: Text(entry.text).font(.caption2.monospaced()).foregroundStyle(.tertiary).textSelection(.enabled)
        }
    }

    // 엔진의 단계 문구는 "✓ 끝남", "· 참고", 그 밖(진행 중)으로 시작한다. 기호는 아이콘으로 바꿔 보여 준다.
    private var step: some View {
        let (icon, text): (String, String) = entry.text.hasPrefix("✓ ")
            ? ("checkmark.circle.fill", String(entry.text.dropFirst(2)))
            : entry.text.hasPrefix("· ") ? ("info.circle", String(entry.text.dropFirst(2))) : ("arrow.forward.circle", entry.text)
        return Label(text, systemImage: icon).font(.callout).foregroundStyle(.secondary)
    }

    private func bubble(_ who: String, color: Color, leading: Bool) -> some View {
        HStack {
            if !leading { Spacer(minLength: 80) }
            VStack(alignment: leading ? .leading : .trailing, spacing: 3) {
                Text(who).font(.caption).foregroundStyle(.secondary)
                Text(entry.text)
                    .textSelection(.enabled)
                    .padding(.horizontal, 12).padding(.vertical, 8)
                    .background(color, in: RoundedRectangle(cornerRadius: 12))
            }
            if leading { Spacer(minLength: 80) }
        }
    }
}

struct PasswordSheet: View {
    let prompt: String
    @Binding var password: String
    let submit: () -> Void
    let cancel: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("서버 비밀번호").font(.headline)
            Text(prompt)
            Text("리허설 게임에서 서버를 열 때 이 비밀번호를 똑같이 넣어 주세요. 이 맥에만, 권한 600 파일로 저장됩니다.")
                .font(.caption).foregroundStyle(.secondary)
            SecureField("5자 이상", text: $password)
                .textFieldStyle(.roundedBorder)
                .onSubmit { if password.count >= 5 { submit() } }
            HStack {
                Spacer()
                Button("취소", role: .cancel, action: cancel)
                Button("저장하고 계속", action: submit)
                    .keyboardShortcut(.defaultAction)
                    .disabled(password.count < 5)
            }
        }
        .padding(20)
        .frame(width: 440)
    }
}

// MARK: - 개발용 창 그림

@MainActor
enum Snapshot {
    static var path: String? {
        let args = CommandLine.arguments
        guard let index = args.firstIndex(of: "--snapshot"), index + 1 < args.count else { return nil }
        return args[index + 1]
    }

    static func save(to path: String) {
        guard let view = NSApp.windows.first(where: { $0.isVisible })?.contentView,
              let bitmap = view.bitmapImageRepForCachingDisplay(in: view.bounds) else {
            print("snapshot: no window")
            exit(1)
        }
        view.cacheDisplay(in: view.bounds, to: bitmap)
        do {
            try bitmap.representation(using: .png, properties: [:])?.write(to: URL(fileURLWithPath: path))
        } catch {
            print("snapshot: \(error)")
            exit(1)
        }
        exit(0)
    }
}

// MARK: - 창 없이 점검 (빌드 확인용)

@MainActor
enum SelfTest {
    static func run() {
        let engine = Engine(repo: Engine.repoFromBundle())
        let world = CommandLine.arguments.drop(while: { $0 != "--world" }).dropFirst().first ?? "helloworld"
        engine.start(world: world, checkOnly: true)
        let deadline = Date().addingTimeInterval(300)
        while engine.running && Date() < deadline {
            RunLoop.main.run(until: Date().addingTimeInterval(0.1))
        }
        for entry in engine.entries { print("\(entry.kind.rawValue)\t\(entry.text)") }
        print("phase\t\(engine.phase.rawValue)")
        exit(engine.phase == .ready ? 0 : 1)
    }
}
