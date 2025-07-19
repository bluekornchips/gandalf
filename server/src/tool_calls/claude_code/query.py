"""
Claude Code query tool for accessing Claude Code session and conversation data.

This module provides tools to query and interact with Claude Code's conversation
history and session management system, adapting the patterns from Cursor IDE
for Claude Code's architecture.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.access_control import AccessValidator
from src.utils.common import log_debug, log_error, log_info


class ClaudeCodeQuery:
    """Query tool for Claude Code conversation data."""

    def __init__(self, silent: bool = False):
        self.silent = silent
        self.claude_home = self._get_claude_home()
        self.projects_dir = self.claude_home / "projects"
        self.sessions_dir = self.claude_home / "sessions"

    def _get_claude_home(self) -> Path:
        """Get Claude Code home directory."""
        # Check environment variables first
        claude_home = os.environ.get("CLAUDE_HOME")
        if claude_home:
            return Path(claude_home)

        # Default locations based on OS
        home = Path.home()

        # Check common Claude Code locations
        possible_locations = [
            home / ".claude",
            home / ".config" / "claude",
            home / "Library" / "Application Support" / "Claude",  # macOS
            home / "AppData" / "Local" / "Claude",  # Windows
        ]

        for location in possible_locations:
            if location.exists():
                return location

        # Default to ~/.claude
        return home / ".claude"

    def find_session_files(self, project_root: Path | None = None) -> list[Path]:
        """Find Claude Code session files."""
        session_files = []

        # Always search in all project directories since Claude Code stores
        # conversations by project
        if self.projects_dir.exists():
            # Search for JSONL files
            for project_dir in self.projects_dir.iterdir():
                if project_dir.is_dir():
                    session_files.extend(project_dir.glob("*.jsonl"))

        # check global sessions directory, if it exists
        if self.sessions_dir.exists():
            session_files.extend(self.sessions_dir.glob("*.jsonl"))

        # If a specific project root is provided, filter to only that project's
        # conversations for a targeted search
        if project_root:
            encoded_path = str(project_root).replace("/", "-")
            filtered_files = []
            for session_file in session_files:
                if encoded_path in str(session_file.parent):
                    filtered_files.append(session_file)
            session_files = filtered_files

        return sorted(session_files, key=lambda x: x.stat().st_mtime, reverse=True)

    def parse_session_file(self, session_file: Path) -> dict[str, Any]:
        """Parse a Claude Code session file (JSONL format)."""
        try:
            messages = []
            session_metadata = {}

            with open(session_file, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)

                        # Extract session metadata from first message
                        if line_num == 1:
                            session_metadata = {
                                "session_id": data.get("sessionId"),
                                "cwd": data.get("cwd"),
                                "version": data.get("version"),
                                "start_time": data.get("timestamp"),
                            }

                        # Store message data
                        messages.append(
                            {
                                "type": data.get("type"),
                                "content": data.get("message", {}).get("content", ""),
                                "role": data.get("message", {}).get("role"),
                                "timestamp": data.get("timestamp"),
                                "parent_uuid": data.get("parentUuid"),
                            }
                        )

                    except json.JSONDecodeError as e:
                        log_debug(
                            f"Error parsing line {line_num} in {session_file}: {e}"
                        )
                        continue

            return {
                "file_path": str(session_file),
                "session_metadata": session_metadata,
                "messages": messages,
                "message_count": len(messages),
                "last_modified": datetime.fromtimestamp(
                    session_file.stat().st_mtime
                ).isoformat(),
            }

        except (OSError, UnicodeDecodeError) as e:
            log_error(e, f"reading session file {session_file}")
            return {}

    def query_conversations(
        self, project_root: Path | None = None, limit: int = 50
    ) -> dict[str, Any]:
        """Query Claude Code conversations."""
        try:
            session_files = self.find_session_files(project_root)

            if not session_files:
                return {
                    "conversations": [],
                    "total_sessions": 0,
                    "query_timestamp": datetime.now().isoformat(),
                    "claude_home": str(self.claude_home),
                }

            conversations = []
            for session_file in session_files[:limit]:
                session_data = self.parse_session_file(session_file)
                if session_data:
                    conversations.append(session_data)

            return {
                "conversations": conversations,
                "total_sessions": len(conversations),
                "query_timestamp": datetime.now().isoformat(),
                "claude_home": str(self.claude_home),
                "project_root": str(project_root) if project_root else None,
            }

        except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
            log_error(e, "query_claude_conversations")
            return AccessValidator.create_error_response(
                f"Error querying Claude Code conversations: {str(e)}"
            )

    def search_conversations(
        self, query: str, project_root: Path | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Search Claude Code conversations for specific content."""
        try:
            session_files = self.find_session_files(project_root)
            matching_conversations = []

            for session_file in session_files:
                session_data = self.parse_session_file(session_file)
                if not session_data:
                    continue

                # Search in message content
                matches = []
                for message in session_data.get("messages", []):
                    content = str(message.get("content", "")).lower()
                    if query.lower() in content:
                        matches.append(
                            {
                                "message": message,
                                "snippet": self._extract_snippet(
                                    content, query.lower(), 100
                                ),
                            }
                        )

                if matches:
                    matching_conversations.append(
                        {
                            "session": session_data,
                            "matches": matches[:5],  # Limit matches per session
                            "match_count": len(matches),
                        }
                    )

                if len(matching_conversations) >= limit:
                    break

            return matching_conversations

        except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
            log_error(e, f"searching Claude Code conversations for '{query}'")
            return []

    def _extract_snippet(self, text: str, query: str, context_chars: int = 100) -> str:
        """Extract a snippet around the query match."""
        query_pos = text.find(query)
        if query_pos == -1:
            return text[:context_chars] + "..." if len(text) > context_chars else text

        start = max(0, query_pos - context_chars // 2)
        end = min(len(text), query_pos + len(query) + context_chars // 2)

        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    def format_as_markdown(self, data: dict[str, Any]) -> str:
        """Format conversation data as markdown."""
        md_lines = [
            "# Claude Code Conversations",
            f"Generated: {data.get('query_timestamp', 'Unknown')}",
            f"Total Sessions: {data.get('total_sessions', 0)}",
            f"Claude Home: {data.get('claude_home', 'Unknown')}",
            "",
        ]

        for i, conversation in enumerate(data.get("conversations", []), 1):
            session_meta = conversation.get("session_metadata", {})
            md_lines.extend(
                [
                    f"## Session {i}",
                    f"- **Session ID**: {session_meta.get('session_id', 'Unknown')}",
                    f"- **Working Directory**: {session_meta.get('cwd', 'Unknown')}",
                    f"- **Start Time**: {session_meta.get('start_time', 'Unknown')}",
                    f"- **Messages**: {conversation.get('message_count', 0)}",
                    f"- **Last Modified**: {conversation.get('last_modified', 'Unknown')}",
                    "",
                ]
            )

            # Add first few messages as preview
            messages = conversation.get("messages", [])[:3]
            for msg in messages:
                role = msg.get("role", "unknown")
                content = str(msg.get("content", ""))[:200]
                md_lines.extend(
                    [
                        f"### {role.title()}",
                        f"{content}{'...' if len(str(msg.get('content', ''))) > 200 else ''}",
                        "",
                    ]
                )

        return "\n".join(md_lines)


def handle_query_claude_conversations(
    arguments: dict[str, Any], project_root: Path, **kwargs
) -> dict[str, Any]:
    """Query Claude Code conversations with comprehensive data retrieval."""
    try:
        # Get parameters
        format_type = arguments.get("format", "json")
        summary = arguments.get("summary", False)
        limit = arguments.get("limit", 50)

        # Validate format
        if format_type not in ["json", "markdown"]:
            return AccessValidator.create_error_response(
                "format must be one of: json, markdown"
            )

        # Initialize query tool
        query_tool = ClaudeCodeQuery(silent=True)

        # Query data.
        # Claude Code needs to use project root
        log_info("Querying conversations from Claude Code sessions...")
        data = query_tool.query_conversations(project_root, limit=limit)

        if summary:
            # Return summary statistics only
            total_conversations = len(data.get("conversations", []))
            total_messages = sum(
                conv.get("message_count", 0) for conv in data.get("conversations", [])
            )

            # Get recent conversation previews
            recent_conversations = []
            for conv in data.get("conversations", [])[:5]:
                session_meta = conv.get("session_metadata", {})
                recent_conversations.append(
                    {
                        "session_id": session_meta.get("session_id", "Unknown"),
                        "start_time": session_meta.get("start_time", "Unknown"),
                        "message_count": conv.get("message_count", 0),
                    }
                )

            summary_data = {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "claude_home": data.get("claude_home"),
                "query_timestamp": data.get("query_timestamp"),
                "recent_conversations": recent_conversations,
            }

            log_info(
                f"Summary: {total_conversations} conversations with {total_messages} total messages"
            )
            return AccessValidator.create_success_response(
                json.dumps(summary_data, indent=2)
            )

        # Format output based on requested format
        if format_type == "markdown":
            content = query_tool.format_as_markdown(data)
        else:  # json
            content = json.dumps(data, indent=2)

        log_info(
            f"Queried {len(data.get('conversations', []))} conversations in {format_type} format"
        )
        return AccessValidator.create_success_response(content)

    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        log_error(e, "query_claude_conversations")
        return AccessValidator.create_error_response(
            f"Error querying Claude Code conversations: {str(e)}"
        )


# Tool definitions
TOOL_QUERY_CLAUDE_CONVERSATIONS = {
    "name": "query_claude_conversations",
    "description": "Query conversations from Claude Code session history for context analysis",
    "inputSchema": {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "enum": ["json", "markdown"],
                "default": "json",
                "description": "Output format for conversation data",
            },
            "summary": {
                "type": "boolean",
                "default": False,
                "description": "Return summary statistics instead of full conversation data",
            },
            "limit": {
                "type": "integer",
                "default": 50,
                "minimum": 1,
                "maximum": 200,
                "description": "Maximum number of conversations to return",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Query Claude Code Conversations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

# Tool handlers and definitions
CLAUDE_CODE_QUERY_TOOL_HANDLERS = {
    "query_claude_conversations": handle_query_claude_conversations,
}

CLAUDE_CODE_QUERY_TOOL_DEFINITIONS = [
    TOOL_QUERY_CLAUDE_CONVERSATIONS,
]
