"""
File operations tool handlers for MCP server.
Handles file listing and project structure operations with intelligent relevance scoring.
"""

from pathlib import Path
from typing import Any, Dict

from config.constants import MAX_PROJECT_FILES
from config.load_weights import (
    MAX_HIGH_PRIORITY_DISPLAY, 
    MAX_MEDIUM_PRIORITY_DISPLAY, 
    MAX_TOP_FILES_DISPLAY,
    ENABLE_CONTEXT_INTELLIGENCE
)
from src.tool_calls.file.file_cache import get_cached_files
from src.context_intelligence import get_context_intelligence
from src.utils import log_info


def handle_list_files(arguments: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    """Handle list_project_files tool call with relevance scoring."""
    max_files = int(arguments.get("max_files", MAX_PROJECT_FILES))
    file_types = arguments.get("file_types", [])
    include_hidden = arguments.get("include_hidden", False)
    use_relevance_scoring = arguments.get("use_relevance_scoring", True)
    
    files = get_cached_files(project_root, max_files)
    
    # Filter by file types if specified
    if file_types:
        filtered_files = []
        for file_path in files:
            if any(file_path.endswith(ext) for ext in file_types):
                filtered_files.append(file_path)
        files = filtered_files
    
    # Filter hidden files if not included
    if not include_hidden:
        files = [f for f in files if not any(part.startswith('.') for part in Path(f).parts)]
    
    # Apply intelligent relevance scoring (only if enabled globally and requested)
    if use_relevance_scoring and ENABLE_CONTEXT_INTELLIGENCE:
        context_intel = get_context_intelligence(project_root)
        context_summary = context_intel.get_context_summary(files)
        
        output_sections = []
        
        # High priority files section
        if context_summary['high_priority_files']:
            high_files = "\n".join(f"  {file}" for file in context_summary['high_priority_files'][:MAX_HIGH_PRIORITY_DISPLAY])
            output_sections.append(f"HIGH PRIORITY FILES:\n{high_files}")
        
        # Medium priority files section
        if context_summary['medium_priority_files']:
            medium_files = "\n".join(f"  {file}" for file in context_summary['medium_priority_files'][:MAX_MEDIUM_PRIORITY_DISPLAY])
            output_sections.append(f"MEDIUM PRIORITY FILES:\n{medium_files}")
        
        # Top files by relevance section
        if context_summary['top_X_files']:
            top_files = "\n".join(f"  {file}" for file in context_summary['top_X_files'][:MAX_TOP_FILES_DISPLAY])
            output_sections.append(f"TOP FILES BY RELEVANCE:\n{top_files}")
        
        summary_text = f"""
SUMMARY: {context_summary['total_files']} total files
High priority: {len(context_summary['high_priority_files'])} 
Medium priority: {len(context_summary['medium_priority_files'])} 
Low priority: {len(context_summary['low_priority_files'])} 
"""
        
        output_sections.append(summary_text)
        
        result_text = "\n\n".join(output_sections)
        log_info(f"Listed {len(files)} files with intelligent prioritization")
        
    else:
        result_text = f"Found {len(files)} files:\n" + "\n".join(files)
        log_info(f"Listed {len(files)} files (basic mode)")
    
    return {
        "content": [
            {
                "type": "text",
                "text": result_text
            }
        ]
    }


# Tool registry for file operations
FILE_TOOL_HANDLERS = {
    "list_project_files": handle_list_files,
} 