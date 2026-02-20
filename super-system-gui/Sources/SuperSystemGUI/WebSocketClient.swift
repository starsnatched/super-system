import Foundation

@Observable
final class WebSocketClient {
    private(set) var isConnected = false
    private var task: URLSessionWebSocketTask?
    private var session: URLSession?
    var onEvent: ((AgentEvent) -> Void)?

    private let url: URL
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    init(url: URL = URL(string: "ws://127.0.0.1:9810/ws")!) {
        self.url = url
    }

    func connect() {
        let session = URLSession(configuration: .default)
        self.session = session
        let task = session.webSocketTask(with: url)
        self.task = task
        task.resume()
        isConnected = true
        receiveLoop()
    }

    func disconnect() {
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        session?.invalidateAndCancel()
        session = nil
        isConnected = false
    }

    func sendStart(prompt: String, cwd: String, resume: String? = nil, fork: Bool = false) {
        let cmd = StartCommand(prompt: prompt, cwd: cwd, resume: resume, fork: fork)
        send(cmd)
    }

    func sendInterrupt() {
        send(InterruptCommand())
    }

    private func send<T: Encodable>(_ value: T) {
        guard let data = try? encoder.encode(value) else { return }
        guard let str = String(data: data, encoding: .utf8) else { return }
        task?.send(.string(str)) { [weak self] error in
            if error != nil {
                self?.handleDisconnect()
            }
        }
    }

    private func receiveLoop() {
        task?.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .success(let message):
                self.handleMessage(message)
                self.receiveLoop()
            case .failure:
                self.handleDisconnect()
            }
        }
    }

    private func handleMessage(_ message: URLSessionWebSocketTask.Message) {
        let data: Data
        switch message {
        case .string(let text):
            guard let d = text.data(using: .utf8) else { return }
            data = d
        case .data(let d):
            data = d
        @unknown default:
            return
        }

        guard let event = try? decoder.decode(AgentEvent.self, from: data) else { return }
        DispatchQueue.main.async { [weak self] in
            self?.onEvent?(event)
        }
    }

    private func handleDisconnect() {
        DispatchQueue.main.async { [weak self] in
            self?.isConnected = false
        }
    }
}
