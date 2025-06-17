"""
Simple, modular MCP server implementation using only Python standard library and shell commands.
"""

import argparse
import json
import os
import sys
import threading
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add the server directory to Python path so we can import modules
sys.path.insert(0, str(Path(__file__).parent))

from config.constants import (
    MCP_PROTOCOL_VERSION,
    SERVER_CAPABILITIES,
    SERVER_INFO,
    SESSION_CONTEXT_MESSAGES,
    AUTO_STORE_THRESHOLD,
    STORE_CONVERSATIONS,
    DISABLE_TEST_CONVERSATIONS
)
from config.tool_definitions import TOOL_DEFINITIONS
from src.tool_calls.conversations.conversation_cache import get_conversation_cache
from src.utils import log_error, log_info

# Import organized tool handlers
from src.tool_calls.git.git_operations import GIT_TOOL_HANDLERS
from src.tool_calls.file.file_operations import FILE_TOOL_HANDLERS
from src.tool_calls.project_operations import PROJECT_TOOL_HANDLERS
from src.tool_calls.conversations.conversation_operations import CONVERSATION_TOOL_HANDLERS

# Aggregate all tool handlers into a single registry
ALL_TOOL_HANDLERS = {
    **GIT_TOOL_HANDLERS,
    **FILE_TOOL_HANDLERS,
    **PROJECT_TOOL_HANDLERS,
    **CONVERSATION_TOOL_HANDLERS,
}


class GandalfMCP:
    """Gandalf for intelligent code assistance in Cursor."""

    def __init__(self, project_root: str = None):
        # If no project root specified, detect it dynamically based on current working directory
        # This allows a single server to work with multiple projects automatically
        if project_root is None:
            # Try to detect from environment or current working directory
            project_root = os.environ.get('PWD', os.getcwd())
        
        # The actual project directory we're analyzing, can be dynamic
        self.project_root = Path(project_root).resolve()
        
        # For dynamic mode, don't require the directory to exist at startup
        # It will be validated when tools are actually called
        if not self.project_root.exists():
            log_info(f"Warning: Project root does not exist yet: {project_root}")
        
        # Auto-conversation tracking with SHA-based session ID, for debugging, analytics,
        # and usage patterns.
        # This storage only happens when MCP tools are called via JSON-RPC. Conversations that do not
        # invoke tool calls will not be tracked here.
        # Control via: export STORE_CONVERSATIONS=false to disable
        
        session_data = f"{datetime.now().isoformat()}-{str(self.project_root)}-{os.getpid()}"
        session_hash = hashlib.sha256(session_data.encode()).digest()
        self.session_id = session_hash.hex()[:16]
        
        self.session_messages = []
        self.session_tools_used = set()
        self.session_start_time = datetime.now()
        self.auto_store_lock = threading.Lock()
        self.async_storage_in_progress = False
        self.session_stored = False
        
        log_info(f"Gandalf initialized for project: {self.project_root}")
        log_info(f"Auto-tracking session: {self.session_id}")

        # Request handlers
        self.handlers = {
            "initialize": self._initialize,
            "notifications/initialized": lambda r: None,
            "tools/list": self._tools_list,
            "tools/call": self._tools_call,
            "ListOfferings": self._list_offerings,
        }

    def _detect_current_project_root(self) -> Path:
        """
        Detect the current project root based on working directory.
        This allows a single server instance to work with multiple projects.
        """
        current_dir = Path(os.environ.get('PWD', os.getcwd())).resolve()
        
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'], 
                cwd=current_dir,
                capture_output=True, 
                text=True, 
                check=True
            )
            git_root = Path(result.stdout.strip()).resolve()
            log_info(f"Detected git root: {git_root}")
            return git_root
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to current dir if not in a git repo
            log_info(f"No git root found, using current directory: {current_dir}")
            return current_dir

    def _update_project_root_if_needed(self) -> None:
        """Update project root, if we're in a different directory."""
        detected_root = self._detect_current_project_root()
        
        if detected_root != self.project_root:
            log_info(f"Project root changed from {self.project_root} to {detected_root}")
            self.project_root = detected_root
            
            # Reset session for new project
            session_data = f"{datetime.now().isoformat()}-{str(self.project_root)}-{os.getpid()}"
            session_hash = hashlib.sha256(session_data.encode()).digest()
            self.session_id = session_hash.hex()[:16]
            
            # Store existing session before switching
            if self.session_messages:
                self._auto_store_conversation()
                
            # Reset session
            self.session_messages = []
            self.session_tools_used = set()
            self.session_start_time = datetime.now()
            self.session_stored = False

    def _generate_session_name(self) -> str:
        """Generate a meaningful name for the current session based on tools used."""
        time_str = self.session_start_time.strftime("%H:%M")
        
        if not self.session_tools_used:
            return f"Session {time_str}"
        
        tools_list = sorted(list(self.session_tools_used))
        if len(tools_list) == 1:
            tool_name = tools_list[0].replace('_', ' ').title()
            return f"{tool_name} - {time_str}"
        elif len(tools_list) <= 3:
            tool_names = ", ".join([t.replace('_', ' ').title() for t in tools_list])
            return f"{tool_names} - {time_str}"
        else:
            return f"Multi-tool Session ({len(tools_list)} tools) - {time_str}"

    def _add_to_session(self, tool_name: str, request_data: Dict[str, Any], response_data: Dict[str, Any]) -> None:
        """
        Add interaction to current session for auto-tracking.
        
        This creates debug/analytics data for every MCP tool call.
        """
        should_auto_store = False
        
        with self.auto_store_lock:
            try:
                self.session_tools_used.add(tool_name)
                
                # Create user message representing the tool call
                user_message = {
                    "role": "user",
                    "content": f"Called tool: {tool_name}",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "tool_name": tool_name,
                        "arguments": request_data.get("params", {}).get("arguments", {}),
                        "session_id": self.session_id
                    }
                }
                
                # Create assistant response
                assistant_message = {
                    "role": "assistant", 
                    "content": f"Tool {tool_name} executed successfully",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "tool_name": tool_name,
                        "response_type": "tool_result",
                        "session_id": self.session_id
                    }
                }
                
                self.session_messages.extend([user_message, assistant_message])
                
                # Auto-store conversation after N tool interactions to avoid memory buildup and ensure context persistence
                # Threshold defined in config/constants.py as AUTO_STORE_THRESHOLD (default: 1 tool call)
                # Each tool call adds 2 messages (user + assistant), so multiply threshold by 2
                # Check if we should auto-store, but don't do it while holding the lock to prevent deadlock
                # If we're at the threshold, we'll auto-store in the background.
                if len(self.session_messages) >= AUTO_STORE_THRESHOLD * 2:
                    should_auto_store = True
                    
            except Exception as e:
                log_error(e, "adding to session")
        
        # Each save overwrites the same session file with all accumulated messages
        # Keeps last SESSION_CONTEXT_MESSAGES in memory for continuity between saves
        if should_auto_store:
            self._auto_store_conversation_async()

    def _auto_store_conversation(self) -> None:
        """
        Automatically store the current session conversation.
        
        This is the 'AUTO-SESSION STORAGE' mechanism portion of the 'AUTO-SESSION TRACKING' system.
        TRIGGERED BY: MCP tool calls (JSON-RPC requests)
        NOT TRIGGERED BY: 'gdlf conv' commands
        """
        if not STORE_CONVERSATIONS or DISABLE_TEST_CONVERSATIONS:
            return
            
        try:
            with self.auto_store_lock:
                if not self.session_messages or self.session_stored:
                    return
                    
                # Generate conversation with title
                session_name = self._generate_session_name()
                
                cache = get_conversation_cache(str(self.project_root))
                
                # Store as single JSON file directly in project conversations directory
                conversation_file = cache.project_conversations_dir / f"{self.session_id}.json"
                
                # Ensure conversations directory exists
                cache.project_conversations_dir.mkdir(parents=True, exist_ok=True)
                
                # Use atomic write to prevent json corruption
                temp_file = conversation_file.with_suffix('.tmp')
                
                enhanced_data = {
                    "conversation_id": self.session_id,
                    "title": session_name,
                    "project_name": cache.project_name,
                    "project_root": str(cache.project_root),
                    "timestamp": time.time(),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "messages": self.session_messages.copy(),
                    "message_count": len(self.session_messages),
                    "session_tools": list(self.session_tools_used),
                    "auto_generated": True
                }
                
                # Write to temp first, then atomic rename
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
                
                temp_file.rename(conversation_file)
                
                self.session_stored = True
                
                log_info(f"Auto-stored conversation '{session_name}' ({self.session_id}) with {len(self.session_messages)} messages")
                
                # Keep last messages for context continuity
                self.session_messages = self.session_messages[-SESSION_CONTEXT_MESSAGES:]
                
        except Exception as e:
            log_error(e, "auto-storing conversation")

    def _auto_store_conversation_async(self) -> None:
        """
        This should reduce latency impact on tool calls.
        Falls back to synchronous storage on thread creation failures.
        """
        try:
            with self.auto_store_lock:
                if self.async_storage_in_progress:
                    log_info(f"Async storage already in progress for session {self.session_id[:8]}, skipping")
                    return
                self.async_storage_in_progress = True
                
            storage_thread = threading.Thread(
                target=self._auto_store_conversation_worker,
                daemon=False,  # Don't terminate thread when process exits
                name=f"GandalfStorage-{self.session_id[:8]}"
            )
            storage_thread.start()
            log_info(f"Started async storage thread for session {self.session_id[:8]}")
            
        except Exception as e:
            log_error(e, "creating async storage thread, falling back to synchronous storage")
            with self.auto_store_lock:
                self.async_storage_in_progress = False
            self._auto_store_conversation()
    
    def _auto_store_conversation_worker(self) -> None:
        """
        Worker method that performs the actual storage operation in background thread.
        
        This is called by _auto_store_conversation_async and should not be called directly.
        Includes thread safety and error handling.
        """
        thread_name = threading.current_thread().name
        log_info(f"[{thread_name}] Starting async conversation storage")
        
        try:
            with self.auto_store_lock:
                if not self.session_messages or self.session_stored:
                    log_info(f"[{thread_name}] No messages to store or already stored for session {self.session_id[:8]}")
                    return
                    
                messages_copy = self.session_messages.copy()
                tools_used_copy = self.session_tools_used.copy()
                session_id = self.session_id
            
                session_name = self._generate_session_name_from_data(tools_used_copy)
                
                cache = get_conversation_cache(str(self.project_root))
                conversation_file = cache.project_conversations_dir / f"{session_id}.json"
                
                cache.project_conversations_dir.mkdir(parents=True, exist_ok=True)
                
                temp_file = conversation_file.with_suffix('.tmp')
                
                enhanced_data = {
                    "conversation_id": session_id,
                    "title": session_name,
                    "project_name": cache.project_name,
                    "project_root": str(cache.project_root),
                    "timestamp": time.time(),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "messages": messages_copy,
                    "message_count": len(messages_copy),
                    "session_tools": list(tools_used_copy),
                    "auto_generated": True,
                    "stored_async": True  # Flag to indicate async storage
                }
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
                
                temp_file.rename(conversation_file)
                
                self.session_stored = True
                
                log_info(f"[{thread_name}] Async-stored conversation '{session_name}' ({session_id[:8]}) with {len(messages_copy)} messages")
                
                self.session_messages = self.session_messages[-SESSION_CONTEXT_MESSAGES:]
                
        except Exception as e:
            log_error(e, f"async storage worker for session {session_id[:8] if 'session_id' in locals() else 'unknown'}")
        finally:
            # Always clear flag
            with self.auto_store_lock:
                self.async_storage_in_progress = False

    def _generate_session_name_from_data(self, tools_used: set) -> str:
        """Generate session name from provided tools data (for async operations)."""
        time_str = self.session_start_time.strftime("%H:%M")
        
        if not tools_used:
            return f"Session {time_str}"
        
        tools_list = sorted(list(tools_used))
        if len(tools_list) == 1:
            tool_name = tools_list[0].replace('_', ' ').title()
            return f"{tool_name} - {time_str}"
        elif len(tools_list) <= 3:
            tool_names = ", ".join([t.replace('_', ' ').title() for t in tools_list])
            return f"{tool_names} - {time_str}"
        else:
            return f"Multi-tool Session ({len(tools_list)} tools) - {time_str}"

    def _initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": SERVER_CAPABILITIES,
                "serverInfo": SERVER_INFO,
            },
        }

    def _tools_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Return available tools list."""
        return {"jsonrpc": "2.0", "result": {"tools": TOOL_DEFINITIONS}}

    def _list_offerings(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """List available offerings for Cursor integration."""
        cursor_offerings = {
            "tools": [
                {"name": tool["name"], "description": tool["description"]}
                for tool in TOOL_DEFINITIONS
            ],
            "resources": [],
            "resourceTemplates": [],
        }
        
        log_info(f"Found {len(cursor_offerings['tools'])} tools, {len(cursor_offerings['resources'])} resources, and {len(cursor_offerings['resourceTemplates'])} resource templates")
        
        return {"jsonrpc": "2.0", "result": cursor_offerings}

    def _tools_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool calls using organized tool handlers."""
        # Skip dynamic detection if explicitly disabled
        # Check environment variable directly since it might be set at runtime
        disable_dynamic = os.environ.get('GANDALF_DISABLE_DYNAMIC_DETECTION', 'false').lower() in ('true', '1', 'yes', 'on')
        
        if not disable_dynamic:
            self._update_project_root_if_needed()
        
        tool_name = request.get("params", {}).get("name", "")
        arguments = request.get("params", {}).get("arguments", {})
        
        log_info(f"Calling tool '{tool_name}' for project: {self.project_root}")

        if tool_name not in ALL_TOOL_HANDLERS:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": f"Unknown tool: {tool_name}",
                },
            }

        try:
            # Call the appropriate tool handler with correct parameters
            tool_handler = ALL_TOOL_HANDLERS[tool_name]
            
            # 'conversation' tools use the new Path-based signature
            if tool_name in ["get_conversation_context", "list_conversations", "store_conversation", "search_conversations", "get_conversation_summary"]:
                result_data = tool_handler(
                    project_root=Path(self.project_root),
                    arguments=arguments,
                    auto_store_callback=lambda: self._auto_store_conversation() if self.session_messages else None
                )
            # All other tools use the original signature
            else:
                result_data = tool_handler(arguments, self.project_root)
                
            result = {"jsonrpc": "2.0", "result": result_data}
            
            self._add_to_session(tool_name, request, result)
            
            log_info(f"Successfully called tool '{tool_name}' for project: {self.project_root}")
            return result
        except Exception as e:
            log_error(e, f"tool: {tool_name}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Tool failed: {str(e)}"},
            }

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming JSON-RPC requests."""
        method = request.get("method", "")

        if method not in self.handlers:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

        try:
            return self.handlers[method](request)
        except Exception as e:
            log_error(e, f"handler: {method}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                },
            }

    def shutdown(self) -> None:
        """Gracefully shutdown the server and store final conversation."""
        try:
            max_wait_time = 5.0
            wait_interval = 0.1
            waited = 0.0
            
            while self.async_storage_in_progress and waited < max_wait_time:
                time.sleep(wait_interval)
                waited += wait_interval
            
            if self.async_storage_in_progress:
                log_info(f"Async storage still in progress after {max_wait_time}s, proceeding with shutdown")
                return  # Don't try to store if we're still going crazy with it
            
            # Auto-store any remaining session data on shutdown
            if self.session_messages:
                self._auto_store_conversation()
                log_info(f"Final conversation stored on shutdown: {self.session_id}")
                
        except Exception as e:
            log_error(e, "shutdown conversation storage")


def main() -> None:
    """Main entry point for Gandalf."""
    parser = argparse.ArgumentParser(description="Gandalf")
    parser.add_argument(
        "--project-root",
        "-p",
        default=".",
        help="Path to the project root (default: current directory)",
    )

    try:
        args = parser.parse_args()
        server = GandalfMCP(args.project_root)
    except Exception as e:
        print(f"Failed to start server: {e}", file=sys.stderr)
        sys.exit(1)

    # Configure stdin/stdout for JSON-RPC communication
    try:
        sys.stdin.reconfigure(line_buffering=True)
        sys.stdout.reconfigure(line_buffering=False)
    except AttributeError:
        pass  # reconfigure not available in older Python versions

    log_info("Gandalf started and listening for requests")

    # Main server loop
    try:
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                    response = server.handle_request(request)

                    if response is not None:
                        if "id" in request:
                            response["id"] = request["id"]
                        print(json.dumps(response))
                        sys.stdout.flush()

                except json.JSONDecodeError:
                    error = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "Parse error"},
                        "id": None,
                    }
                    print(json.dumps(error))
                    sys.stdout.flush()

            except (BrokenPipeError, EOFError, KeyboardInterrupt):
                log_info("Gandalf shutting down")
                break
            except Exception as e:
                log_error(e, "main server loop")
                continue
    finally:
        # Ensure conversation is stored on shutdown
        server.shutdown()


if __name__ == "__main__":
    main()
