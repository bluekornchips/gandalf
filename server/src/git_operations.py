"""Git operations for the MCP server."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils import log_error, debug_log


def get_git_status(project_root: Path, include_untracked: bool = True, verbose: bool = False) -> Dict[str, Any]:
    """Get git status information."""
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {"error": "Not a git repository"}
        
        # Get current branch
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
        
        # Get status
        status_cmd = ["git", "status", "--porcelain"]
        if include_untracked:
            status_cmd.append("--untracked-files=normal")
        else:
            status_cmd.append("--untracked-files=no")
            
        status_result = subprocess.run(
            status_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if status_result.returncode != 0:
            return {"error": f"Git status failed: {status_result.stderr}"}
        
        # Parse status output
        status_lines = status_result.stdout.strip().split('\n') if status_result.stdout.strip() else []
        
        modified_files = []
        staged_files = []
        untracked_files = []
        
        for line in status_lines:
            if len(line) < 3:
                continue
                
            status_code = line[:2]
            filename = line[3:]
            
            if status_code[0] in ['M', 'A', 'D', 'R', 'C']:
                staged_files.append({"file": filename, "status": status_code[0]})
            if status_code[1] in ['M', 'D']:
                modified_files.append({"file": filename, "status": status_code[1]})
            if status_code == "??":
                untracked_files.append(filename)
        
        # Get commit info
        commit_result = subprocess.run(
            ["git", "log", "-1", "--format=%H|%s|%an|%ad", "--date=iso"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        last_commit = None
        if commit_result.returncode == 0 and commit_result.stdout.strip():
            parts = commit_result.stdout.strip().split('|', 3)
            if len(parts) == 4:
                last_commit = {
                    "hash": parts[0][:8],
                    "message": parts[1],
                    "author": parts[2],
                    "date": parts[3]
                }
        
        return {
            "current_branch": current_branch,
            "staged_files": staged_files,
            "modified_files": modified_files,
            "untracked_files": untracked_files,
            "is_clean": len(staged_files) == 0 and len(modified_files) == 0 and len(untracked_files) == 0,
            "last_commit": last_commit
        }
        
    except subprocess.TimeoutExpired:
        return {"error": "Git command timed out"}
    except Exception as e:
        log_error(e, "getting git status")
        return {"error": str(e)}


def get_git_commit_history(project_root: Path, limit: int = 20, since: Optional[str] = None, 
                          author: Optional[str] = None, branch: Optional[str] = None, 
                          timeout: int = 15) -> List[Dict[str, Any]]:
    """Get git commit history."""
    try:
        cmd = ["git", "log", f"--max-count={limit}", "--format=%H|%s|%an|%ae|%ad|%ar", "--date=iso"]
        
        if since:
            cmd.append(f"--since={since}")
        if author:
            cmd.append(f"--author={author}")
        if branch:
            cmd.append(branch)
            
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            return []
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
                
            parts = line.split('|', 5)
            if len(parts) == 6:
                commits.append({
                    "hash": parts[0][:8],
                    "message": parts[1],
                    "author_name": parts[2],
                    "author_email": parts[3],
                    "date": parts[4],
                    "relative_date": parts[5]
                })
        
        return commits
        
    except subprocess.TimeoutExpired:
        log_error(Exception("Git commit history timed out"), "git commit history")
        return []
    except Exception as e:
        log_error(e, "getting git commit history")
        return []


def get_git_branches(project_root: Path, include_remote: bool = True, 
                    include_merged: bool = True, timeout: int = 10) -> Dict[str, Any]:
    """Get git branch information."""
    try:
        # Get local branches
        local_cmd = ["git", "branch", "-v"]
        if not include_merged:
            local_cmd.append("--no-merged")
            
        local_result = subprocess.run(
            local_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        local_branches = []
        current_branch = None
        
        if local_result.returncode == 0:
            for line in local_result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                is_current = line.startswith('*')
                branch_info = line[2:].strip() if is_current else line.strip()
                
                parts = branch_info.split(None, 2)
                if len(parts) >= 2:
                    branch_name = parts[0]
                    commit_hash = parts[1][:8] if len(parts[1]) > 8 else parts[1]
                    message = parts[2] if len(parts) > 2 else ""
                    
                    branch_data = {
                        "name": branch_name,
                        "commit": commit_hash,
                        "message": message,
                        "is_current": is_current
                    }
                    
                    local_branches.append(branch_data)
                    if is_current:
                        current_branch = branch_name
        
        remote_branches = []
        if include_remote:
            remote_cmd = ["git", "branch", "-r", "-v"]
            if not include_merged:
                remote_cmd.append("--no-merged")
                
            remote_result = subprocess.run(
                remote_cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if remote_result.returncode == 0:
                for line in remote_result.stdout.strip().split('\n'):
                    if not line or '->' in line:  # Skip HEAD references
                        continue
                        
                    parts = line.strip().split(None, 2)
                    if len(parts) >= 2:
                        branch_name = parts[0]
                        commit_hash = parts[1][:8] if len(parts[1]) > 8 else parts[1]
                        message = parts[2] if len(parts) > 2 else ""
                        
                        remote_branches.append({
                            "name": branch_name,
                            "commit": commit_hash,
                            "message": message
                        })
        
        return {
            "current_branch": current_branch,
            "local_branches": local_branches,
            "remote_branches": remote_branches,
            "total_local": len(local_branches),
            "total_remote": len(remote_branches)
        }
        
    except subprocess.TimeoutExpired:
        log_error(Exception("Git branches command timed out"), "git branches")
        return {"error": "Command timed out"}
    except Exception as e:
        log_error(e, "getting git branches")
        return {"error": str(e)}


def get_project_info(project_root: Path) -> Dict[str, Any]:
    """Get comprehensive project information."""
    try:
        project_info = {
            "project_root": str(project_root),
            "project_name": project_root.name,
        }
        
        # Get git information
        git_status = get_git_status(project_root)
        if "error" not in git_status:
            project_info["git"] = git_status
        
        return project_info
        
    except Exception as e:
        log_error(e, "getting project info")
        return {"error": str(e)}


def get_git_diff(project_root: Path, commit_hash: Optional[str] = None, 
                file_path: Optional[str] = None, staged: bool = False,
                timeout: int = 15) -> Dict[str, Any]:
    """Get git diff information."""
    try:
        cmd = ["git", "diff"]
        
        if staged:
            cmd.append("--staged")
        elif commit_hash:
            if commit_hash.lower() == "head":
                cmd.append("HEAD~1..HEAD")
            else:
                # Show diff for specific commit
                cmd.extend([f"{commit_hash}~1", commit_hash])
        
        if file_path:
            cmd.append(file_path)
            
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            return {"error": f"Git diff failed: {result.stderr}"}
        
        diff_output = result.stdout
        
        # Parse diff to extract file changes
        files_changed = []
        current_file = None
        
        for line in diff_output.split('\n'):
            if line.startswith('diff --git'):
                # Extract file path from "diff --git a/file b/file"
                parts = line.split(' ')
                if len(parts) >= 4:
                    file_a = parts[2][2:]  # Remove "a/" prefix
                    file_b = parts[3][2:]  # Remove "b/" prefix
                    current_file = file_b if file_b else file_a
                    files_changed.append(current_file)
        
        # Get stats
        stats_result = subprocess.run(
            cmd + ["--stat"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        stats = stats_result.stdout if stats_result.returncode == 0 else ""
        
        return {
            "diff_output": diff_output,
            "files_changed": files_changed,
            "stats": stats,
            "commit_hash": commit_hash,
            "file_path": file_path,
            "staged": staged
        }
        
    except subprocess.TimeoutExpired:
        log_error(Exception("Git diff timed out"), "git diff")
        return {"error": "Git diff operation timed out"}
    except Exception as e:
        log_error(e, "getting git diff")
        return {"error": str(e)}
