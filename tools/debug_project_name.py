#!/usr/bin/env python3

import sys
import os
from pathlib import Path

# Add server path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from src.utils.project import ProjectContext
from src.utils.access_control import AccessValidator

def test_project_name(path_str):
    """Test project name handling for a given path."""
    print(f"Testing project path: {path_str}")
    
    path = Path(path_str)
    print(f"Path object: {path}")
    print(f"Path name: {path.name}")
    
    # Test sanitization directly
    raw_name = path.name
    print(f"Raw name: '{raw_name}'")
    
    sanitized = AccessValidator.sanitize_project_name(raw_name)
    print(f"Sanitized name: '{sanitized}'")
    
    # Test ProjectContext
    try:
        context = ProjectContext.from_path(path)
        print(f"Context raw_name: '{context.raw_name}'")
        print(f"Context sanitized_name: '{context.sanitized_name}'")
        print(f"Context was_sanitized: {context.was_sanitized}")
    except Exception as e:
        print(f"Error creating ProjectContext: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_project_name(sys.argv[1])
    else:
        # Test with default project name
        test_project_name("/tmp/there_and_back_again")
        test_project_name("/private/var/folders/test/there_and_back_again") 