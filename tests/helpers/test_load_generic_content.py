#!/usr/bin/env python3
"""
Test helper script for load_generic_content functionality, designed specifically for use in shell and not with pytest.
"""

import sys
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
GANDALF_ROOT = SCRIPT_DIR.parent.parent
SERVER_DIR = GANDALF_ROOT / "server"

sys.path.insert(0, str(SERVER_DIR))

try:
    from src.content.load_generic_content import load_flat_context_data, GenericContentLoader
    IMPORT_SUCCESS = True
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


def validate_data_path(data_path: str) -> bool:
    """Validate that the data path exists and is accessible."""
    try:
        path = Path(data_path)
        return path.exists()
    except (OSError, ValueError):
        return False


def handle_import_check() -> int:
    """Handle --check-import flag."""
    if IMPORT_SUCCESS:
        print("Import successful")
        return 0
    else:
        print(f"Import failed: {IMPORT_ERROR}", file=sys.stderr)
        return 1


def handle_class_check() -> int:
    """Handle --check-class flag."""
    if not IMPORT_SUCCESS:
        print(f"Cannot check class - import failed: {IMPORT_ERROR}", file=sys.stderr)
        return 1
    
    try:
        if hasattr(GenericContentLoader, 'load_flat_context_data'):
            print("Class import successful")
            return 0
        else:
            print("Class exists but missing expected methods", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Class check failed: {e}", file=sys.stderr)
        return 1


def load_content_with_validation(data_path: str, context_name: str) -> int:
    """Load content with proper validation and error handling."""
    if not IMPORT_SUCCESS:
        print(f"Cannot load content - import failed: {IMPORT_ERROR}", file=sys.stderr)
        return 1
    
    if not validate_data_path(data_path):
        print("None")  # Expected output for non-existent paths in tests
        return 1
    
    try:
        result = load_flat_context_data(data_path, context_name)
        
        if result:
            print(result)
            return 0
        else:
            print("None")
            return 1
            
    except Exception as e:
        print(f"Error loading content: {e}", file=sys.stderr)
        return 1


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description='Test helper for load_generic_content functionality',
        epilog="""
Examples:
    %(prog)s --check-import                    # Test module import
    %(prog)s --check-class                     # Test class import
    %(prog)s /path/to/file.txt                 # Load with default context name
    %(prog)s /path/to/file.txt --context-name my_context  # Load with custom name
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'data_path', 
        nargs='?', 
        help='Path to file or directory to load'
    )
    
    parser.add_argument(
        '--context-name', 
        default='external_data',
        metavar='NAME',
        help='Name for the context (default: %(default)s)'
    )
    
    parser.add_argument(
        '--check-import', 
        action='store_true',
        help='Test that the module can be imported successfully'
    )
    
    parser.add_argument(
        '--check-class', 
        action='store_true',
        help='Test that the GenericContentLoader class can be imported and has expected methods'
    )
    
    parser.add_argument(
        '--version', 
        action='version',
        version='%(prog)s 1.0 (Gandalf MCP Test Helper)'
    )
    
    return parser


def main() -> int:
    """Main entry point for the test helper script."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    if args.check_import:
        return handle_import_check()
        
    if args.check_class:
        return handle_class_check()
    
    if not args.data_path:
        parser.error("data_path is required unless using --check-import or --check-class")
    
    return load_content_with_validation(args.data_path, args.context_name)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1) 