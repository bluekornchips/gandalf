"""
File operations tools for the Gandalf MCP server.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.config.constants.system import MAX_PROJECT_FILES
from src.core.file_scoring import (
    clear_file_scores,
    get_files_list,
    get_files_with_scores,
)
from src.utils.common import log_debug
from src.utils.performance import log_operation_time, start_timer
from src.utils.security import SecurityValidator, validate_file_types

MAX_FILE_TYPES = 20
MAX_FILE_EXTENSION_LENGTH = 10
MAX_FILES_LIMIT = 10000
HIGH_PRIORITY_DISPLAY_LIMIT = 20
MEDIUM_PRIORITY_DISPLAY_LIMIT = 15
LOW_PRIORITY_DISPLAY_LIMIT = 10
TOP_FILES_DISPLAY_LIMIT = 15


def validate_max_files(max_files: int) -> tuple[bool, str]:
    """Validate max_files parameter."""

    if max_files < 1:
        return False, "max_files must be at least 1"

    if max_files > MAX_FILES_LIMIT:
        return False, f"max_files cannot exceed {MAX_FILES_LIMIT}"

    return True, ""


TOOL_LIST_PROJECT_FILES = {
    "name": "list_project_files",
    "description": "List project files with relevance scoring and filtering",
    "inputSchema": {
        "type": "object",
        "properties": {
            "file_types": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": MAX_FILE_TYPES,
                "description": "Filter by file extensions (e.g., ['.py', '.js', '.md'])",
            },
            "max_files": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_FILES_LIMIT,
                "default": 1000,
                "description": "Maximum number of files to return",
            },
            "use_relevance_scoring": {
                "type": "boolean",
                "default": True,
                "description": "Enable relevance scoring and prioritization",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "List Project Files",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}


def handle_list_project_files(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """Handle list_project_files tool call with enhanced security and error handling."""
    start_time = start_timer()

    try:
        file_types = arguments.get("file_types", [])
        max_files = arguments.get("max_files", MAX_PROJECT_FILES)
        use_relevance_scoring = arguments.get("use_relevance_scoring", False)

        if file_types:
            valid, error_msg = validate_file_types(file_types)
            if not valid:
                return SecurityValidator.create_error_response(error_msg)

        if (
            not isinstance(max_files, int)
            or max_files < 1
            or max_files > MAX_FILES_LIMIT
        ):
            return SecurityValidator.create_error_response(
                f"max_files must be an integer between 1 and {MAX_FILES_LIMIT}"
            )

        # use_relevance_scoring
        if not isinstance(use_relevance_scoring, bool):
            return SecurityValidator.create_error_response(
                "use_relevance_scoring must be a boolean"
            )

        # project_root
        valid, error_msg = SecurityValidator.validate_path(
            project_root, "project_root"
        )
        if not valid:
            return SecurityValidator.create_error_response(error_msg)

        if not project_root.exists() or not project_root.is_dir():
            return SecurityValidator.create_error_response(
                "Invalid project root directory"
            )

        # Apply file filtering and scoring
        if use_relevance_scoring:
            log_debug("Using relevance scoring for file prioritization")
            scored_files = get_files_with_scores(project_root)

            # Re check security for cached files, no tricks
            if not _validate_cache_security(project_root, scored_files):
                log_debug("Cache security validation failed, refreshing cache")
                clear_file_scores(project_root)
                scored_files = get_files_with_scores(project_root)

            # Apply file type filtering if specified
            if file_types:
                filtered_files = []
                extensions = set()
                for file_type in file_types:
                    if file_type.startswith("."):
                        extensions.add(file_type.lower())
                    else:
                        extensions.add(f".{file_type.lower()}")

                for file_path, score in scored_files:
                    try:
                        path_obj = Path(file_path)
                        if path_obj.suffix.lower() in extensions:
                            filtered_files.append((file_path, score))
                    except (OSError, ValueError) as e:
                        log_debug(
                            f"Skipping file due to path error: {file_path}, {e}"
                        )
                        continue
                scored_files = filtered_files

            # Sort by score: higher should always be first. Limit results.
            sorted_files = sorted(
                scored_files, key=lambda x: x[1], reverse=True
            )
            if max_files:
                sorted_files = sorted_files[:max_files]

            files_to_return = [f[0] for f in sorted_files]
            scores = {f[0]: f[1] for f in sorted_files}

            # Formatted output with priority levels
            high_priority = [f for f, s in scores.items() if s >= 0.8]
            medium_priority = [f for f, s in scores.items() if 0.5 <= s < 0.8]
            low_priority = [f for f, s in scores.items() if s < 0.5]

            output_lines = []

            if high_priority:
                output_lines.append("HIGH PRIORITY FILES:")
                for file in high_priority[:HIGH_PRIORITY_DISPLAY_LIMIT]:
                    output_lines.append(f"  {file}")

            if medium_priority:
                output_lines.append("\nMEDIUM PRIORITY FILES:")
                for file in medium_priority[:MEDIUM_PRIORITY_DISPLAY_LIMIT]:
                    output_lines.append(f"  {file}")

            if low_priority:
                output_lines.append("\nLOW PRIORITY FILES:")
                for file in low_priority[:LOW_PRIORITY_DISPLAY_LIMIT]:
                    output_lines.append(f"  {file}")

            output_lines.append(f"\nTOP FILES BY RELEVANCE:")
            top_files = sorted_files[
                : min(TOP_FILES_DISPLAY_LIMIT, len(sorted_files))
            ]
            for file, score in top_files:
                output_lines.append(f"  {file} (score: {score:.2f})")

            output_lines.append(
                f"\nSUMMARY: {len(files_to_return)} total files"
            )
            output_lines.append(f"High priority: {len(high_priority)}")
            output_lines.append(f"Medium priority: {len(medium_priority)}")
            output_lines.append(f"Low priority: {len(low_priority)}")

            content = "\n".join(output_lines)

        else:
            log_debug("Using simple file listing without relevance scoring")
            files = get_files_list(project_root)

            if file_types:
                filtered_files = []
                extensions = set()
                for file_type in file_types:
                    if file_type.startswith("."):
                        extensions.add(file_type.lower())
                    else:
                        extensions.add(f".{file_type.lower()}")

                for file_path in files:
                    try:
                        path_obj = Path(file_path)
                        if path_obj.suffix.lower() in extensions:
                            filtered_files.append(file_path)
                    except (OSError, ValueError) as e:
                        log_debug(
                            f"Skipping file due to path error: {file_path}, {e}"
                        )
                        continue
                files = filtered_files

            if max_files:
                files = files[:max_files]

            content = f"FILES ({len(files)} total):\n" + "\n".join(
                f"  {f}" for f in files
            )

        log_operation_time("list_project_files", start_time)
        return SecurityValidator.create_success_response(content)

    except (OSError, ValueError, TypeError, KeyError) as e:
        log_debug(e, "list_project_files")
        return SecurityValidator.create_error_response(
            f"Error listing files: {str(e)}"
        )


def _validate_cache_security(
    project_root: Path, scored_files: List[Tuple[str, float]]
) -> bool:
    """Validate that cached files are still within project boundaries."""
    try:
        project_root_str = str(project_root.resolve())

        for file_path, _ in scored_files:
            try:
                resolved_path = Path(file_path).resolve()
                if not str(resolved_path).startswith(project_root_str):
                    log_debug(
                        f"Security: File outside project root: {file_path}"
                    )
                    return False
            except (OSError, ValueError) as e:
                log_debug(
                    f"Security: Invalid file path in cache: {file_path}, {e}"
                )
                return False

        return True
    except (OSError, ValueError, PermissionError) as e:
        log_debug(f"Security validation error: {e}")
        return False


FILE_TOOL_HANDLERS = {
    "list_project_files": handle_list_project_files,
}

FILE_TOOL_DEFINITIONS = [
    TOOL_LIST_PROJECT_FILES,
]
