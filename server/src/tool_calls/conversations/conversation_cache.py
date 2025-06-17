"""Conversation caching system for MCP server to store and retrieve conversation history."""

import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils import debug_log, log_error


class ConversationCache:
    """Cache for storing and retrieving conversation history."""
    
    def __init__(self, project_root: Path):
        """Initialize conversation cache.
        
        Args:
            project_root: Root directory of the project (used for project identification)
        """
        self.project_root = project_root
        self.project_name = project_root.name
        
        # Create conversations directory
        home_dir = Path.home()
        self.conversations_dir = home_dir / ".gandalf" / "conversations"
        self.project_conversations_dir = self.conversations_dir / self.project_name
        
        # Separate directories for real conversations vs analytics
        self.real_conversations_dir = self.project_conversations_dir / "conversations"
        self.analytics_sessions_dir = self.project_conversations_dir / "sessions"
        
        # Ensure directories exist
        self._ensure_directories()
        
        self._cache_lock = threading.Lock()
        
        # Path to the gandalf script
        gandalf_root = self.project_root / "gandalf"
        self.gandalf_script = gandalf_root / "scripts" / "conversations.sh"
        
    def _ensure_directories(self) -> None:
        """Ensure conversation directories exist."""
        try:
            self.conversations_dir.mkdir(parents=True, exist_ok=True)
            self.project_conversations_dir.mkdir(parents=True, exist_ok=True)
            self.real_conversations_dir.mkdir(parents=True, exist_ok=True)
            self.analytics_sessions_dir.mkdir(parents=True, exist_ok=True)
            debug_log(f"Conversation directories ensured: {self.project_conversations_dir}")
        except Exception as e:
            log_error(e, "creating conversation directories")
    
    def _run_gandalf_command(self, args: List[str], input_data: str = None, cwd: str = None) -> Optional[Dict[str, Any]]:
        """Run a gandalf conversation command and return parsed output.
        """
        try:
            cmd = ["bash", str(self.gandalf_script)] + args
            
            if cwd is None:
                cwd = str(self.project_root)
            
            result = subprocess.run(
                cmd,
                input=input_data,
                text=True,
                capture_output=True,
                cwd=cwd,
                timeout=30
            )
            
            if result.returncode != 0:
                log_error(None, f"Gandalf command failed: {' '.join(args)}\nStderr: {result.stderr}")
                return None
            
            if result.stdout.strip():
                try:
                    parsed_json = json.loads(result.stdout.strip())
                    if isinstance(parsed_json, (list, dict)):
                        return parsed_json
                    else:
                        return {"text": result.stdout.strip()}
                except json.JSONDecodeError:
                    return {"text": result.stdout.strip()}
            
            return {"text": ""}
            
        except subprocess.TimeoutExpired:
            log_error(None, f"Gandalf command timed out: {' '.join(args)}")
            return None
        except Exception as e:
            log_error(e, f"running gandalf command: {' '.join(args)}")
            return None
    
    def store_conversation(self, conversation_id: str, messages: List[Dict[str, Any]]) -> None:
        """Store an analytics session (legacy method for tool call tracking).
        
        Args:
            conversation_id: Unique identifier for the session
            messages: List of tool call messages (analytics data)
        """
        with self._cache_lock:
            try:
                conversation_data = {
                    "conversation_id": conversation_id,
                    "project_name": self.project_name,
                    "project_root": str(self.project_root),
                    "timestamp": time.time(),
                    "created_at": datetime.now().isoformat(),
                    "messages": messages,
                    "message_count": len(messages),
                    "conversation_type": "analytics"
                }
                
                input_json = json.dumps([conversation_data])
                title = f"Multi-tool Session ({len(messages)} tools) - {datetime.now().strftime('%H:%M')}"
                
                result = self._run_gandalf_command(
                    ["store", conversation_id, "-t", title],
                    input_data=input_json
                )
                
                if result:
                    debug_log(f"Stored analytics session {conversation_id} with {len(messages)} messages")
                else:
                    log_error(None, f"Failed to store analytics session {conversation_id}")
                
            except Exception as e:
                log_error(e, f"storing analytics session {conversation_id}")
    
    def store_real_conversation(self, conversation_id: str, messages: List[Dict[str, Any]], 
                               title: Optional[str] = None, tags: Optional[List[str]] = None) -> None:
        """Store a real conversation with actual user/assistant messages.
        
        Args:
            conversation_id: Unique identifier for the conversation
            messages: List of real conversation messages
            title: Optional conversation title
            tags: Optional list of tags for categorization
        """
        with self._cache_lock:
            try:
                input_json = json.dumps(messages)
                
                args = ["store", conversation_id]
                if title:
                    args.extend(["-t", title])
                if tags:
                    args.extend(["-g", ",".join(tags)])
                
                result = self._run_gandalf_command(args, input_data=input_json)
                
                if result:
                    debug_log(f"Stored real conversation {conversation_id} with {len(messages)} messages")
                else:
                    log_error(None, f"Failed to store real conversation {conversation_id}")
                
            except Exception as e:
                log_error(e, f"storing real conversation {conversation_id}")
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific conversation (checks both real and analytics).
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            Conversation data or None if not found
        """
        try:
            result = self._run_gandalf_command(["show", conversation_id, "-f", "json"])
            
            if result and "text" in result:
                try:
                    return json.loads(result["text"])
                except json.JSONDecodeError:
                    log_error(None, f"Failed to parse conversation JSON for {conversation_id}")
                    return None
            
            return result
            
        except Exception as e:
            log_error(e, f"retrieving conversation {conversation_id}")
            return None
    
    def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent conversations using gandalf script.
        """
        try:
            args = ["list", "-f", "json"]
            if limit:
                args.extend(["-n", str(limit)])
            
            debug_log(f"Running gandalf command: {args} from {self.project_root}")
            result = self._run_gandalf_command(args)
            debug_log(f"Gandalf command result type: {type(result)}")
            
            if result:
                if isinstance(result, list):
                    conversations_data = result
                    debug_log(f"Got direct list with {len(conversations_data)} items")
                elif isinstance(result, dict) and "text" in result:
                    debug_log(f"Got dict with text, length: {len(result['text'])}")
                    try:
                        conversations_data = json.loads(result["text"])
                        debug_log(f"Parsed JSON successfully, type: {type(conversations_data)}")
                    except json.JSONDecodeError:
                        log_error(None, "Failed to parse conversations list JSON")
                        return []
                else:
                    conversations_data = result
                    debug_log(f"Got other result type: {type(result)}")
                
                if isinstance(conversations_data, list):
                    conversations = []
                    for conv in conversations_data:
                        timestamp = conv.get("timestamp")
                        if timestamp is None:
                            timestamp = 0
                        elif isinstance(timestamp, str):
                            try:
                                timestamp = float(timestamp)
                            except (ValueError, TypeError):
                                timestamp = 0
                        
                        conversations.append({
                            "conversation_id": conv.get("conversation_id"),
                            "title": conv.get("title"),
                            "created_at": conv.get("created_at"),
                            "timestamp": timestamp,
                            "message_count": conv.get("message_count", 0),
                            "project_name": conv.get("project_name"),
                            "conversation_type": conv.get("conversation_type", "unknown"),
                            "tags": conv.get("tags", [])
                        })
                    
                    debug_log(f"Listed {len(conversations)} conversations via gandalf script")
                    return conversations
                else:
                    debug_log(f"Conversations data is not a list: {type(conversations_data)}")
            else:
                debug_log("No result from gandalf command")
            
            return []
            
        except Exception as e:
            log_error(e, "listing conversations via gandalf script")
            return []
    
    def list_real_conversations(self, limit: int = 50, sort_by: str = "created_at", 
                               sort_order: str = "desc", filter_tags: List[str] = None,
                               date_from: str = None, date_to: str = None) -> List[Dict[str, Any]]:
        """List real conversations with advanced filtering.
        
        Args:
            limit: Maximum number of conversations to return
            sort_by: Field to sort by ("created_at", "updated_at", "message_count", "title")
            sort_order: Sort order ("asc" or "desc")
            filter_tags: Filter by tags
            date_from: Filter conversations from this date (YYYY-MM-DD)
            date_to: Filter conversations to this date (YYYY-MM-DD)
            
        Returns:
            List of conversation metadata
        """
        try:
            # Get all conversations and filter in Python
            all_conversations = self.list_conversations(limit * 2)
            
            conversations = [c for c in all_conversations if c.get("conversation_type") == "real"]
            
            if date_from or date_to:
                filtered_conversations = []
                for conv in conversations:
                    conv_date = conv.get("created_at", "")[:10]  # YYYY-MM-DD
                    if date_from and conv_date < date_from:
                        continue
                    if date_to and conv_date > date_to:
                        continue
                    filtered_conversations.append(conv)
                conversations = filtered_conversations
            
            if filter_tags:
                filtered_conversations = []
                for conv in conversations:
                    conv_tags = conv.get("tags", [])
                    if any(tag in conv_tags for tag in filter_tags):
                        filtered_conversations.append(conv)
                conversations = filtered_conversations
            
            # Sort conversations
            reverse = (sort_order == "desc")
            if sort_by == "created_at":
                conversations.sort(key=lambda x: x.get("created_at", ""), reverse=reverse)
            elif sort_by == "updated_at":
                conversations.sort(key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=reverse)
            elif sort_by == "message_count":
                conversations.sort(key=lambda x: x.get("message_count", 0), reverse=reverse)
            elif sort_by == "title":
                conversations.sort(key=lambda x: x.get("title", "").lower(), reverse=reverse)
            elif sort_by == "timestamp":
                conversations.sort(key=lambda x: x.get("timestamp", 0) or 0, reverse=reverse)
            
            conversations = conversations[:limit]
            
            debug_log(f"Listed {len(conversations)} real conversations with filtering")
            return conversations
            
        except Exception as e:
            log_error(e, "listing real conversations with filtering")
            return []
    
    def search_conversations(self, query: str, conversation_type: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        """Search conversations by content, title, or tags.
        
        Args:
            query: Search query
            conversation_type: "real", "analytics", or "all"
            limit: Maximum number of results
            
        Returns:
            List of matching conversations
        """
        try:
            results = []
            query_lower = query.lower()
            
            # Search real conversations
            if conversation_type in ["real", "all"]:
                conversation_files = list(self.real_conversations_dir.glob("*.json"))
                for conversation_file in conversation_files:
                    try:
                        with open(conversation_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Search in title, tags, and message content
                        title = data.get("title", "").lower()
                        tags = " ".join(data.get("tags", [])).lower()
                        content = " ".join([msg.get("content", "") for msg in data.get("messages", [])]).lower()
                        
                        if query_lower in title or query_lower in tags or query_lower in content:
                            results.append({
                                **data,
                                "conversation_type": "real",
                                "match_score": self._calculate_match_score(query_lower, title, tags, content)
                            })
                            
                    except Exception as e:
                        log_error(e, f"searching conversation file {conversation_file}")
                        continue
            
            # Search analytics sessions
            if conversation_type in ["analytics", "all"]:
                session_files = list(self.analytics_sessions_dir.glob("*.json"))
                for session_file in session_files:
                    try:
                        with open(session_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Search in message content
                        content = " ".join([msg.get("content", "") for msg in data.get("messages", [])]).lower()
                        
                        if query_lower in content:
                            results.append({
                                **data,
                                "conversation_type": "analytics",
                                "match_score": self._calculate_match_score(query_lower, "", "", content)
                            })
                            
                    except Exception as e:
                        log_error(e, f"searching session file {session_file}")
                        continue
            
            # Sort by match score and limit results
            results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            return results[:limit]
            
        except Exception as e:
            log_error(e, "searching conversations")
            return []
    
    def _calculate_match_score(self, query: str, title: str, tags: str, content: str) -> float:
        """Calculate a simple match score for search results."""
        score = 0.0
        
        # Title matches are worth more
        if query in title:
            score += 10.0
        
        # Tag matches are worth medium
        if query in tags:
            score += 5.0
        
        # Content matches are worth less but still valuable
        content_matches = content.count(query)
        score += content_matches * 1.0
        
        return score
    
    def get_recent_conversations_context(self, limit: int = 10) -> str:
        """Get recent analytics sessions as context for the AI (legacy method).
        
        Args:
            limit: Maximum number of recent sessions to include
            
        Returns:
            Formatted string with session context
        """
        try:
            conversations = self.list_conversations(limit)
            
            if not conversations:
                return "No previous analytics sessions found for this project."
            
            context_parts = [
                f"Recent analytics sessions for project '{self.project_name}':",
                ""
            ]
            
            for conv in conversations:
                created_at = conv.get("created_at", "Unknown")
                message_count = conv.get("message_count", 0)
                conv_id = conv.get("conversation_id", "Unknown")
                
                context_parts.append(
                    f"- Session {conv_id}: {message_count} tool calls "
                    f"(Created: {created_at})"
                )
            
            context_parts.extend([
                "",
                f"Total sessions stored: {len(conversations)}",
                f"Sessions directory: {self.analytics_sessions_dir}"
            ])
            
            return "\n".join(context_parts)
            
        except Exception as e:
            log_error(e, "getting analytics session context")
            return f"Error retrieving analytics session context: {str(e)}"
    
    def get_real_conversation_context(self, limit: int = 10, include_messages: bool = False, 
                                     search_query: str = None) -> str:
        """Get recent real conversations as context for the AI.
        
        Args:
            limit: Maximum number of recent conversations to include
            include_messages: Whether to include actual message content
            search_query: Optional search query to filter conversations
            
        Returns:
            Formatted string with conversation context
        """
        try:
            if search_query:
                conversations = self.search_conversations(search_query, "real", limit)
            else:
                conversations = self.list_real_conversations(limit)
            
            if not conversations:
                return "No previous real conversations found for this project."
            
            context_parts = [
                f"Recent conversations for project '{self.project_name}':",
                ""
            ]
            
            for conv in conversations:
                title = conv.get("title", "Untitled")
                created_at = conv.get("created_at", "Unknown")
                message_count = conv.get("message_count", 0)
                conv_id = conv.get("conversation_id", "Unknown")
                tags = conv.get("tags", [])
                
                context_parts.append(f"## {title}")
                context_parts.append(f"- ID: {conv_id}")
                context_parts.append(f"- Created: {created_at}")
                context_parts.append(f"- Messages: {message_count}")
                if tags:
                    context_parts.append(f"- Tags: {', '.join(tags)}")
                
                if include_messages:
                    # Get full conversation data
                    full_conv = self.get_conversation(conv_id)
                    if full_conv and full_conv.get("messages"):
                        context_parts.append("- Recent messages:")
                        for msg in full_conv["messages"][-3:]:  # Last 3 messages
                            role = msg.get("role", "unknown")
                            content = msg.get("content", "")[:100]  # Truncate long messages
                            context_parts.append(f"  - {role}: {content}...")
                
                context_parts.append("")
            
            context_parts.extend([
                f"Total conversations stored: {len(conversations)}",
                f"Conversations directory: {self.real_conversations_dir}"
            ])
            
            return "\n".join(context_parts)
            
        except Exception as e:
            log_error(e, "getting real conversation context")
            return f"Error retrieving real conversation context: {str(e)}"
    
    def get_conversation_summary(self, conversation_id: str) -> Optional[str]:
        """Get a summary of a specific conversation.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            Summary string or None if conversation not found
        """
        conversation = self.get_conversation(conversation_id)
        
        if not conversation:
            return None
        
        messages = conversation.get("messages", [])
        created_at = conversation.get("created_at", "Unknown")
        conversation_type = conversation.get("conversation_type", "unknown")
        
        # Extract key information from messages
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        assistant_messages = [msg for msg in messages if msg.get("role") == "assistant"]
        
        summary_parts = [
            f"Conversation {conversation_id}",
            f"Type: {conversation_type}",
            f"Created: {created_at}",
            f"Total messages: {len(messages)}",
            f"User messages: {len(user_messages)}",
            f"Assistant messages: {len(assistant_messages)}"
        ]
        
        if conversation_type == "real":
            title = conversation.get("title", "")
            tags = conversation.get("tags", [])
            if title:
                summary_parts.append(f"Title: {title}")
            if tags:
                summary_parts.append(f"Tags: {', '.join(tags)}")
        
        # Add first and last user messages as context
        if user_messages:
            first_msg = user_messages[0].get("content", "")[:100]
            summary_parts.append(f"First user message: {first_msg}...")
            
            if len(user_messages) > 1:
                last_msg = user_messages[-1].get("content", "")[:100]
                summary_parts.append(f"Last user message: {last_msg}...")
        
        return "\n".join(summary_parts)
    
    def cleanup_old_conversations(self, days_to_keep: int = 30) -> int:
        """Clean up conversations older than specified days.
        
        Args:
            days_to_keep: Number of days to keep conversations
            
        Returns:
            Number of conversations deleted
        """
        try:
            result = self._run_gandalf_command(["cleanup", str(days_to_keep)])
            
            if result and "text" in result:
                output_text = result["text"]
                if "Cleaned up" in output_text:
                    import re
                    match = re.search(r"Cleaned up (\d+) conversations", output_text)
                    if match:
                        deleted_count = int(match.group(1))
                        debug_log(f"Cleaned up {deleted_count} old conversations via gandalf script")
                        return deleted_count
            
            return 0
            
        except Exception as e:
            log_error(e, "cleaning up old conversations via gandalf script")
            return 0


# Global conversation cache instance
_conversation_cache: Optional[ConversationCache] = None
_cache_lock = threading.Lock()


def get_conversation_cache(project_root: str) -> ConversationCache:
    """Get or create the global conversation cache instance."""
    global _conversation_cache
    
    project_path = Path(project_root)
    
    with _cache_lock:
        if _conversation_cache is None or _conversation_cache.project_root != project_path:
            _conversation_cache = ConversationCache(project_path)
    
    return _conversation_cache


def store_conversation(project_root: Path, conversation_id: str, messages: List[Dict[str, Any]]) -> None:
    """Store an analytics session for the project (legacy method).
    
    Args:
        project_root: Root directory of the project
        conversation_id: Unique identifier for the session
        messages: List of tool call messages (analytics data)
    """
    cache = get_conversation_cache(str(project_root))
    cache.store_conversation(conversation_id, messages)


def store_real_conversation(project_root: Path, conversation_id: str, messages: List[Dict[str, Any]], 
                           title: Optional[str] = None, tags: Optional[List[str]] = None) -> None:
    """Store a real conversation for the project.
    
    Args:
        project_root: Root directory of the project
        conversation_id: Unique identifier for the conversation
        messages: List of real conversation messages
        title: Optional conversation title
        tags: Optional list of tags for categorization
    """
    cache = get_conversation_cache(str(project_root))
    cache.store_real_conversation(conversation_id, messages, title, tags)


def get_conversation_context(project_root: Path, limit: int = 10) -> str:
    """Get recent analytics sessions as context for the AI (legacy method).
    
    Args:
        project_root: Root directory of the project
        limit: Maximum number of recent sessions to include
        
    Returns:
        Formatted string with session context
    """
    cache = get_conversation_cache(str(project_root))
    return cache.get_recent_conversations_context(limit)


def get_real_conversation_context(project_root: Path, limit: int = 10, include_messages: bool = False, 
                                 search_query: str = None) -> str:
    """Get recent real conversations as context for the AI.
    
    Args:
        project_root: Root directory of the project
        limit: Maximum number of recent conversations to include
        include_messages: Whether to include actual message content
        search_query: Optional search query to filter conversations
        
    Returns:
        Formatted string with conversation context
    """
    cache = get_conversation_cache(str(project_root))
    return cache.get_real_conversation_context(limit, include_messages, search_query) 