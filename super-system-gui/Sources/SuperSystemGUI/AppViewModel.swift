import Foundation
import SwiftUI

@Observable
final class AppViewModel {
    var sessions: [SessionInfo] = []
    var entries: [ChatEntry] = []
    var isSessionRunning = false
    var currentSessionId: String?
    var previewURL: String = "http://localhost:3000"
    var workingDirectory: String = NSHomeDirectory()
    var lastError: String?

    var totalTurns: Int = 0
    var totalCost: Double = 0
    var durationMs: Int = 0
    var sessionStatus: SessionStatus = .idle

    let backend = BackendProcess()
    let ws = WebSocketClient()

    private let apiBase = "http://127.0.0.1:9810"
    private var startTime: Date?
    private var durationTimer: Timer?

    enum SessionStatus: String {
        case idle, running, completed, failed, interrupted
    }

    init() {
        ws.onEvent = { [weak self] event in
            self?.handleEvent(event)
        }

        if let saved = UserDefaults.standard.string(forKey: "lastWorkingDirectory"),
           FileManager.default.fileExists(atPath: saved) {
            workingDirectory = saved
        }
    }

    func startBackend() {
        backend.start()
        pollUntilReady()
    }

    func stopBackend() {
        ws.disconnect()
        backend.stop()
    }

    private func pollUntilReady() {
        Timer.scheduledTimer(withTimeInterval: 0.3, repeats: true) { [weak self] timer in
            guard let self else {
                timer.invalidate()
                return
            }
            if self.backend.isReady {
                timer.invalidate()
                self.ws.connect()
                self.fetchSessions()
            } else if !self.backend.isRunning {
                timer.invalidate()
                self.lastError = "Backend process failed to start."
            }
        }
    }

    func resetForNewSession() {
        guard !isSessionRunning else { return }
        entries.removeAll()
        totalTurns = 0
        totalCost = 0
        durationMs = 0
        sessionStatus = .idle
        currentSessionId = nil
        lastError = nil
    }

    func startSession(prompt: String) {
        guard !isSessionRunning else { return }
        guard !prompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }

        entries.removeAll()
        totalTurns = 0
        totalCost = 0
        durationMs = 0
        sessionStatus = .running
        isSessionRunning = true
        currentSessionId = nil
        lastError = nil
        startTime = Date()

        entries.append(.status(id: UUID(), message: "Starting session\u{2026}", timestamp: Date()))

        UserDefaults.standard.set(workingDirectory, forKey: "lastWorkingDirectory")

        startDurationTimer()
        ws.sendStart(prompt: prompt, cwd: workingDirectory)
    }

    func resumeSession(sessionId: String, prompt: String) {
        guard !isSessionRunning else { return }

        entries.removeAll()
        totalTurns = 0
        totalCost = 0
        durationMs = 0
        sessionStatus = .running
        isSessionRunning = true
        currentSessionId = nil
        lastError = nil
        startTime = Date()

        let resolvedPrompt = prompt.isEmpty ? "Continue from where you left off." : prompt

        entries.append(.status(id: UUID(), message: "Resuming session\u{2026}", timestamp: Date()))

        startDurationTimer()
        ws.sendStart(prompt: resolvedPrompt, cwd: workingDirectory, resume: sessionId)
    }

    func interruptSession() {
        ws.sendInterrupt()
    }

    func chooseWorkingDirectory() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.message = "Choose the project working directory"
        panel.prompt = "Select"

        if panel.runModal() == .OK, let url = panel.url {
            workingDirectory = url.path
            UserDefaults.standard.set(workingDirectory, forKey: "lastWorkingDirectory")
        }
    }

    func fetchSessions() {
        guard let url = URL(string: "\(apiBase)/api/sessions") else { return }
        URLSession.shared.dataTask(with: url) { [weak self] data, _, error in
            guard let data, error == nil else { return }
            if let decoded = try? JSONDecoder().decode([SessionInfo].self, from: data) {
                DispatchQueue.main.async {
                    self?.sessions = decoded.reversed()
                }
            }
        }.resume()
    }

    var formattedDuration: String {
        let totalSec = durationMs / 1000
        let mins = totalSec / 60
        let secs = totalSec % 60
        return String(format: "%02d:%02d", mins, secs)
    }

    var workingDirectoryDisplay: String {
        let home = NSHomeDirectory()
        if workingDirectory.hasPrefix(home) {
            return "~" + workingDirectory.dropFirst(home.count)
        }
        return workingDirectory
    }

    var workingDirectoryName: String {
        (workingDirectory as NSString).lastPathComponent
    }

    private func handleEvent(_ event: AgentEvent) {
        switch event {
        case .text(let content):
            entries.append(.text(id: UUID(), content: content, timestamp: Date()))

        case .agentDispatch(let agent, let desc):
            entries.append(.agentDispatch(id: UUID(), agent: agent, description: desc, timestamp: Date()))

        case .result(let turns, let cost, let duration, let isError, let errorText):
            totalTurns = turns
            totalCost = cost
            durationMs = duration
            sessionStatus = isError ? .failed : .completed
            isSessionRunning = false
            stopDurationTimer()
            entries.append(.result(id: UUID(), turns: turns, cost: cost, durationMs: duration, isError: isError, errorText: errorText))
            fetchSessions()

        case .sessionId(let sid):
            currentSessionId = sid
            entries.append(.status(id: UUID(), message: "Session started: \(sid.prefix(16))", timestamp: Date()))

        case .error(let msg):
            lastError = msg
            entries.append(.error(id: UUID(), message: msg, timestamp: Date()))
            if !isSessionRunning { return }
            sessionStatus = .failed
            isSessionRunning = false
            stopDurationTimer()

        case .interrupted:
            sessionStatus = .interrupted
            isSessionRunning = false
            stopDurationTimer()
            entries.append(.status(id: UUID(), message: "Session interrupted", timestamp: Date()))
            fetchSessions()
        }
    }

    private func startDurationTimer() {
        durationTimer?.invalidate()
        durationTimer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            guard let self, let start = self.startTime, self.isSessionRunning else { return }
            self.durationMs = Int(Date().timeIntervalSince(start) * 1000)
        }
    }

    private func stopDurationTimer() {
        durationTimer?.invalidate()
        durationTimer = nil
    }
}
