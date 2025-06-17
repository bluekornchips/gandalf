"""File filtering and gitignore handling for the MCP server."""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Set

from config.constants import FIND_EXCLUDE_DIRS, FIND_EXCLUDE_PATTERNS, MAX_PROJECT_FILES
from src.utils import debug_log, log_error


def filter_files(project_root: Path, max_files: int = MAX_PROJECT_FILES) -> List[str]:
    """
    Get filtered list of files using shell commands for performance.
    Respects gitignore and common exclusion patterns.
    """
    try:
        # Build find command with exclusions
        find_cmd = ["find", str(project_root), "-type", "f"]
        
        # Add directory exclusions
        for exclude_dir in FIND_EXCLUDE_DIRS:
            find_cmd.extend(["-not", "-path", f"*/{exclude_dir}/*"])
        
        # Add pattern exclusions
        for pattern in FIND_EXCLUDE_PATTERNS:
            find_cmd.extend(["-not", "-name", pattern])
        
        debug_log(f"Running find command: {' '.join(find_cmd)}")
        
        # Execute find command
        result = subprocess.run(
            find_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_root
        )
        
        if result.returncode != 0:
            log_error(Exception(f"Find command failed: {result.stderr}"), "filter_files")
            return []
        
        # Process results
        files = []
        for line in result.stdout.strip().split('\n'):
            if line and line != str(project_root):
                # Convert to relative path
                try:
                    rel_path = str(Path(line).relative_to(project_root))
                    files.append(rel_path)
                    
                    if len(files) >= max_files:
                        debug_log(f"Reached max files limit: {max_files}")
                        break
                except ValueError:
                    # Skip files outside project root
                    continue
        
        debug_log(f"Found {len(files)} files after filtering")
        return files
        
    except subprocess.TimeoutExpired:
        log_error(Exception("Find command timed out"), "filter_files")
        return []
    except Exception as e:
        log_error(e, "filter_files")
        return []


def is_gitignored(file_path: str, project_root: Path) -> bool:
    """Check if a file is gitignored using git check-ignore."""
    try:
        result = subprocess.run(
            ["git", "check-ignore", file_path],
            cwd=project_root,
            capture_output=True,
            timeout=5
        )
        # git check-ignore returns 0 if file is ignored
        return result.returncode == 0
    except Exception:
        return False


def get_gitignore_patterns(project_root: Path) -> Set[str]:
    """Get patterns from .gitignore file."""
    gitignore_file = project_root / ".gitignore"
    patterns = set()
    
    if gitignore_file.exists():
        try:
            with open(gitignore_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.add(line)
        except Exception as e:
            log_error(e, "reading .gitignore")
    
    return patterns
