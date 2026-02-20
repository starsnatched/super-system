import Foundation

enum AgentEvent: Decodable {
    case text(String)
    case agentDispatch(agent: String, description: String)
    case result(turns: Int, cost: Double, durationMs: Int, isError: Bool, errorText: String)
    case sessionId(String)
    case error(String)
    case interrupted

    private enum CodingKeys: String, CodingKey {
        case type, content, agent, description, turns, cost
        case durationMs = "duration_ms"
        case isError = "is_error"
        case errorText = "error_text"
        case id, message
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)

        switch type {
        case "text":
            let content = try container.decode(String.self, forKey: .content)
            self = .text(content)
        case "agent_dispatch":
            let agent = try container.decode(String.self, forKey: .agent)
            let desc = try container.decodeIfPresent(String.self, forKey: .description) ?? ""
            self = .agentDispatch(agent: agent, description: desc)
        case "result":
            let turns = try container.decode(Int.self, forKey: .turns)
            let cost = try container.decode(Double.self, forKey: .cost)
            let duration = try container.decode(Int.self, forKey: .durationMs)
            let isError = try container.decodeIfPresent(Bool.self, forKey: .isError) ?? false
            let errorText = try container.decodeIfPresent(String.self, forKey: .errorText) ?? ""
            self = .result(turns: turns, cost: cost, durationMs: duration, isError: isError, errorText: errorText)
        case "session_id":
            let sid = try container.decode(String.self, forKey: .id)
            self = .sessionId(sid)
        case "error":
            let msg = try container.decode(String.self, forKey: .message)
            self = .error(msg)
        case "interrupted":
            self = .interrupted
        default:
            throw DecodingError.dataCorruptedError(
                forKey: .type, in: container,
                debugDescription: "Unknown event type: \(type)"
            )
        }
    }
}

struct StartCommand: Encodable {
    let type = "start"
    let prompt: String
    let cwd: String
    let resume: String?
    let fork: Bool
}

struct InterruptCommand: Encodable {
    let type = "interrupt"
}

struct SessionInfo: Codable, Identifiable {
    let sessionId: String
    let promptPreview: String
    let startedAt: Double
    let status: String
    let costUsd: Double
    let numTurns: Int
    let durationMs: Int

    var id: String { sessionId }

    var startedDate: Date {
        Date(timeIntervalSince1970: startedAt)
    }

    private enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case promptPreview = "prompt_preview"
        case startedAt = "started_at"
        case status
        case costUsd = "cost_usd"
        case numTurns = "num_turns"
        case durationMs = "duration_ms"
    }
}

struct AgentMeta {
    let name: String
    let icon: String
    let hue: Double

    static let all: [AgentMeta] = [
        AgentMeta(name: "researcher", icon: "◇", hue: 190),
        AgentMeta(name: "architect", icon: "△", hue: 300),
        AgentMeta(name: "backend-coder", icon: "◆", hue: 130),
        AgentMeta(name: "frontend-coder", icon: "●", hue: 50),
        AgentMeta(name: "infra-coder", icon: "■", hue: 25),
        AgentMeta(name: "reviewer", icon: "◎", hue: 200),
        AgentMeta(name: "tester", icon: "▲", hue: 160),
        AgentMeta(name: "security-auditor", icon: "◉", hue: 0),
        AgentMeta(name: "doc-writer", icon: "□", hue: 280),
        AgentMeta(name: "product-manager", icon: "▶", hue: 40),
        AgentMeta(name: "performance-optimizer", icon: "⚡", hue: 175),
        AgentMeta(name: "ux-analyst", icon: "○", hue: 310),
    ]

    static func find(_ name: String) -> AgentMeta? {
        all.first { $0.name == name }
    }
}

enum ChatEntry: Identifiable {
    case text(id: UUID, content: String, timestamp: Date)
    case agentDispatch(id: UUID, agent: String, description: String, timestamp: Date)
    case result(id: UUID, turns: Int, cost: Double, durationMs: Int, isError: Bool, errorText: String)
    case error(id: UUID, message: String, timestamp: Date)
    case status(id: UUID, message: String, timestamp: Date)

    var entryId: UUID {
        switch self {
        case .text(let id, _, _): return id
        case .agentDispatch(let id, _, _, _): return id
        case .result(let id, _, _, _, _, _): return id
        case .error(let id, _, _): return id
        case .status(let id, _, _): return id
        }
    }

    var id: UUID { entryId }
}
