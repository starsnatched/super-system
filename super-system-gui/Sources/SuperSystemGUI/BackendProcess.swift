import Foundation

@Observable
final class BackendProcess {
    private(set) var isRunning = false
    private(set) var isReady = false
    private var process: Process?
    private var healthTimer: Timer?
    private let port: Int
    private let projectRoot: String

    init(port: Int = 9810) {
        self.port = port
        let guiDir = Bundle.main.executableURL?
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .path ?? FileManager.default.currentDirectoryPath
        self.projectRoot = guiDir
    }

    func start() {
        guard !isRunning else { return }

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        proc.arguments = ["uv", "run", "python", "-m", "super_system.server"]
        proc.currentDirectoryURL = URL(fileURLWithPath: projectRoot)
        proc.environment = ProcessInfo.processInfo.environment

        let pipe = Pipe()
        proc.standardOutput = pipe
        proc.standardError = pipe

        proc.terminationHandler = { [weak self] _ in
            DispatchQueue.main.async {
                self?.isRunning = false
                self?.isReady = false
            }
        }

        do {
            try proc.run()
            process = proc
            isRunning = true
            startHealthPolling()
        } catch {
            isRunning = false
        }
    }

    func stop() {
        healthTimer?.invalidate()
        healthTimer = nil

        if let proc = process, proc.isRunning {
            proc.interrupt()
            DispatchQueue.global().asyncAfter(deadline: .now() + 2) { [weak self] in
                if let p = self?.process, p.isRunning {
                    p.terminate()
                }
            }
        }
        process = nil
        isRunning = false
        isReady = false
    }

    private func startHealthPolling() {
        healthTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] timer in
            guard let self else {
                timer.invalidate()
                return
            }
            self.checkHealth { ready in
                DispatchQueue.main.async {
                    if ready {
                        self.isReady = true
                        timer.invalidate()
                        self.healthTimer = nil
                    }
                }
            }
        }
    }

    private func checkHealth(completion: @escaping (Bool) -> Void) {
        guard let url = URL(string: "http://127.0.0.1:\(port)/api/health") else {
            completion(false)
            return
        }
        let task = URLSession.shared.dataTask(with: url) { data, response, error in
            guard error == nil,
                  let http = response as? HTTPURLResponse,
                  http.statusCode == 200
            else {
                completion(false)
                return
            }
            completion(true)
        }
        task.resume()
    }

    deinit {
        stop()
    }
}
