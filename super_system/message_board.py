from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from claude_agent_sdk import create_sdk_mcp_server, tool
from claude_agent_sdk.types import McpSdkServerConfig

COMMS_TOOLS = [
    "send_message",
    "read_messages",
    "read_thread",
    "share_artifact",
    "get_artifact",
    "list_artifacts",
]


@dataclass
class Message:
    id: str
    from_agent: str
    to_agent: str
    kind: Literal["question", "answer", "info", "request"]
    subject: str
    body: str
    thread_id: str
    timestamp: float
    read_by: set[str] = field(default_factory=set)


class MessageBoard:
    def __init__(self) -> None:
        self._messages: list[Message] = []
        self._artifacts: dict[str, tuple[str, str]] = {}
        self._on_message: list[Callable[[Message], None]] = []
        self._on_artifact: list[Callable[[str, str, str], None]] = []

    def post(
        self,
        from_agent: str,
        to_agent: str,
        kind: str,
        subject: str,
        body: str,
        thread_id: str | None = None,
    ) -> Message:
        msg = Message(
            id=uuid.uuid4().hex[:12],
            from_agent=from_agent,
            to_agent=to_agent,
            kind=kind,
            subject=subject,
            body=body,
            thread_id=thread_id or uuid.uuid4().hex[:12],
            timestamp=time.time(),
        )
        self._messages.append(msg)
        for cb in self._on_message:
            cb(msg)
        return msg

    def read(
        self,
        reader: str,
        *,
        from_agent: str | None = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Message]:
        results: list[Message] = []
        for msg in reversed(self._messages):
            if msg.to_agent not in (reader, "all"):
                continue
            if from_agent and msg.from_agent != from_agent:
                continue
            if unread_only and reader in msg.read_by:
                continue
            results.append(msg)
            msg.read_by.add(reader)
            if len(results) >= limit:
                break
        return list(reversed(results))

    def read_thread(self, reader: str, thread_id: str) -> list[Message]:
        results: list[Message] = []
        for msg in self._messages:
            if msg.thread_id == thread_id:
                results.append(msg)
                msg.read_by.add(reader)
        return results

    def store_artifact(self, owner: str, key: str, content: str) -> None:
        self._artifacts[key] = (owner, content)
        for cb in self._on_artifact:
            cb(owner, key, content)

    def get_artifact(self, key: str) -> tuple[str, str] | None:
        return self._artifacts.get(key)

    def list_artifacts(self) -> list[tuple[str, str]]:
        return [(k, owner) for k, (owner, _) in self._artifacts.items()]

    def on_message(self, callback: Callable[[Message], None]) -> None:
        self._on_message.append(callback)

    def on_artifact(self, callback: Callable[[str, str, str], None]) -> None:
        self._on_artifact.append(callback)

    @property
    def pending_questions(self) -> list[Message]:
        answered_threads: set[str] = set()
        for msg in self._messages:
            if msg.kind == "answer":
                answered_threads.add(msg.thread_id)
        return [
            m
            for m in self._messages
            if m.kind == "question" and m.thread_id not in answered_threads
        ]


def _format_message(msg: Message) -> str:
    return (
        f"[{msg.id}] {msg.from_agent} -> {msg.to_agent} ({msg.kind})\n"
        f"Subject: {msg.subject}\n"
        f"Thread: {msg.thread_id}\n"
        f"---\n{msg.body}"
    )


def _format_messages(messages: list[Message]) -> str:
    if not messages:
        return "No messages found."
    return "\n\n===\n\n".join(_format_message(m) for m in messages)


_SEND_SCHEMA = {
    "type": "object",
    "properties": {
        "from_agent": {
            "type": "string",
            "description": "Your agent name (e.g. 'backend-coder', 'architect')",
        },
        "to_agent": {
            "type": "string",
            "description": (
                "Target agent name, or 'all' to broadcast. "
                "Valid agents: researcher, architect, backend-coder, frontend-coder, "
                "infra-coder, reviewer, tester, security-auditor, doc-writer, "
                "product-manager, performance-optimizer, ux-analyst, orchestrator"
            ),
        },
        "kind": {
            "type": "string",
            "enum": ["question", "answer", "info", "request"],
            "description": (
                "Message type: question (need info from another agent), "
                "answer (responding to a question), "
                "info (sharing findings/status), "
                "request (asking another agent to do something)"
            ),
        },
        "subject": {
            "type": "string",
            "description": "Brief subject line summarizing the message",
        },
        "body": {
            "type": "string",
            "description": "Full message content with all relevant details",
        },
        "thread_id": {
            "type": "string",
            "description": "Thread ID to continue an existing conversation. Omit to start a new thread.",
        },
    },
    "required": ["from_agent", "to_agent", "kind", "subject", "body"],
}

_READ_SCHEMA = {
    "type": "object",
    "properties": {
        "reader": {
            "type": "string",
            "description": "Your agent name",
        },
        "from_agent": {
            "type": "string",
            "description": "Filter to messages from a specific agent (optional)",
        },
        "unread_only": {
            "type": "boolean",
            "description": "Only show unread messages (default: false)",
        },
        "limit": {
            "type": "integer",
            "description": "Max number of messages to return (default: 50)",
        },
    },
    "required": ["reader"],
}

_THREAD_SCHEMA = {
    "type": "object",
    "properties": {
        "reader": {
            "type": "string",
            "description": "Your agent name",
        },
        "thread_id": {
            "type": "string",
            "description": "Thread ID to read",
        },
    },
    "required": ["reader", "thread_id"],
}

_SHARE_ARTIFACT_SCHEMA = {
    "type": "object",
    "properties": {
        "owner": {
            "type": "string",
            "description": "Your agent name",
        },
        "key": {
            "type": "string",
            "description": (
                "Artifact name. Use descriptive kebab-case names like "
                "'architecture-spec', 'research-brief', 'security-report', "
                "'test-results', 'review-feedback'"
            ),
        },
        "content": {
            "type": "string",
            "description": "Full artifact content",
        },
    },
    "required": ["owner", "key", "content"],
}

_GET_ARTIFACT_SCHEMA = {
    "type": "object",
    "properties": {
        "key": {
            "type": "string",
            "description": "Artifact name to retrieve",
        },
    },
    "required": ["key"],
}

_LIST_ARTIFACTS_SCHEMA: dict = {
    "type": "object",
    "properties": {},
}


def build_message_board_server(board: MessageBoard) -> McpSdkServerConfig:
    @tool(
        "send_message",
        (
            "Send a message to another agent or broadcast to all agents. "
            "Use to ask questions, share findings, flag blockers, or coordinate work."
        ),
        _SEND_SCHEMA,
    )
    async def send_message(args: dict) -> dict:
        msg = board.post(
            from_agent=args["from_agent"],
            to_agent=args["to_agent"],
            kind=args["kind"],
            subject=args["subject"],
            body=args["body"],
            thread_id=args.get("thread_id"),
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Message sent. ID: {msg.id}, Thread: {msg.thread_id}",
                }
            ]
        }

    @tool(
        "read_messages",
        (
            "Read messages directed to you or broadcast to all agents. "
            "Call this at the START of every task to check for context, "
            "questions, or coordination notes from other agents."
        ),
        _READ_SCHEMA,
    )
    async def read_messages(args: dict) -> dict:
        messages = board.read(
            reader=args["reader"],
            from_agent=args.get("from_agent"),
            unread_only=args.get("unread_only", False),
            limit=args.get("limit", 50),
        )
        return {"content": [{"type": "text", "text": _format_messages(messages)}]}

    @tool(
        "read_thread",
        "Read all messages in a conversation thread by thread ID.",
        _THREAD_SCHEMA,
    )
    async def read_thread(args: dict) -> dict:
        messages = board.read_thread(
            reader=args["reader"],
            thread_id=args["thread_id"],
        )
        return {"content": [{"type": "text", "text": _format_messages(messages)}]}

    @tool(
        "share_artifact",
        (
            "Store a named artifact that other agents can retrieve later. "
            "Use to share specs, research briefs, review reports, test results, "
            "or any structured output that downstream agents need."
        ),
        _SHARE_ARTIFACT_SCHEMA,
    )
    async def share_artifact(args: dict) -> dict:
        board.store_artifact(
            owner=args["owner"],
            key=args["key"],
            content=args["content"],
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Artifact '{args['key']}' stored. "
                        "Other agents can retrieve it with get_artifact."
                    ),
                }
            ]
        }

    @tool(
        "get_artifact",
        (
            "Retrieve a shared artifact by name. Use to pull specs, reports, "
            "or findings produced by other agents."
        ),
        _GET_ARTIFACT_SCHEMA,
    )
    async def get_artifact(args: dict) -> dict:
        result = board.get_artifact(args["key"])
        if result is None:
            available = board.list_artifacts()
            keys = ", ".join(k for k, _ in available) if available else "none"
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Artifact '{args['key']}' not found. Available: {keys}",
                    }
                ],
                "is_error": True,
            }
        owner, content = result
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Artifact '{args['key']}' (by {owner}):\n\n{content}",
                }
            ]
        }

    @tool(
        "list_artifacts",
        "List all shared artifacts on the message board.",
        _LIST_ARTIFACTS_SCHEMA,
    )
    async def list_artifacts(_args: dict) -> dict:
        artifacts = board.list_artifacts()
        if not artifacts:
            return {"content": [{"type": "text", "text": "No artifacts shared yet."}]}
        lines = [f"- {key} (by {owner})" for key, owner in artifacts]
        return {
            "content": [
                {"type": "text", "text": "Shared artifacts:\n" + "\n".join(lines)}
            ]
        }

    return create_sdk_mcp_server(
        name="message-board",
        tools=[
            send_message,
            read_messages,
            read_thread,
            share_artifact,
            get_artifact,
            list_artifacts,
        ],
    )
