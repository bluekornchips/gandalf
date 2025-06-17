"""Generic content loading utilities for side-loading any data into context."""

import json
from pathlib import Path
from typing import List, Optional

from src.utils import log_error, debug_log


class GenericContentLoader:
    """Utility class for loading any flat/unstructured data for context."""
    
    @staticmethod
    def load_flat_context_data(data_path: str, context_name: str = "external_data") -> Optional[str]:
        """Generic method to load any flat/unstructured data for context.
        
        This allows side-loading basically anything into context:
        - Conversations from other projects or models.
        - JSON, text, log, etc files.
        - Structured or unstructured data.
        """
        try:
            path = Path(data_path)
            
            if not path.exists():
                debug_log(f"Context data path does not exist: {data_path}")
                return None
            
            context_parts = [f"=== Loaded Context: {context_name} ==="]
            
            if path.is_file():
                context_parts.extend(GenericContentLoader._load_single_file_context(path))
            elif path.is_dir():
                context_parts.extend(GenericContentLoader._load_directory_context(path))
            else:
                return None
                
            context_parts.append(f"=== End Context: {context_name} ===")
            
            debug_log(f"Loaded flat context data from: {data_path}")
            return "\n".join(context_parts)
            
        except Exception as e:
            log_error(e, f"loading flat context data from {data_path}")
            return None
    
    @staticmethod
    def _load_single_file_context(file_path: Path) -> List[str]:
        """Load context from a single file."""
        context_parts = []
        
        try:
            suffix = file_path.suffix.lower()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if suffix == '.json':
                try:
                    data = json.loads(content)
                    if isinstance(data, list) and len(data) > 0 and 'messages' in str(data[0]):
                        context_parts.append(f"Conversation data with {len(data)} entries:")
                        for i, item in enumerate(data[:5]):  # Show first 5
                            context_parts.append(f"  {i+1}. {item.get('title', 'Untitled')} ({item.get('message_count', 0)} messages)")
                        if len(data) > 5:
                            context_parts.append(f"  ... and {len(data) - 5} more")
                    else:
                        context_parts.append(f"JSON data: {json.dumps(data, indent=2)[:500]}...")
                except json.JSONDecodeError:
                    context_parts.append(f"Raw content: {content[:500]}...")
            else:
                lines = content.split('\n')
                context_parts.append(f"Text file with {len(lines)} lines:")
                context_parts.extend([f"  {line}" for line in lines[:10]])
                if len(lines) > 10:
                    context_parts.append(f"  ... and {len(lines) - 10} more lines")
                    
        except Exception as e:
            context_parts.append(f"Error loading file {file_path}: {e}")
            
        return context_parts
    
    @staticmethod
    def _load_directory_context(dir_path: Path) -> List[str]:
        """Load context from all files in a directory."""
        context_parts = []
        
        try:
            files = list(dir_path.rglob('*'))
            data_files = [f for f in files if f.is_file() and f.suffix.lower() in ['.json', '.txt', '.log', '.md']]
            
            context_parts.append(f"Directory with {len(data_files)} loadable files:")
            
            for file_path in data_files[:5]:  # Load first 5 files
                context_parts.append(f"\n--- {file_path.name} ---")
                context_parts.extend(GenericContentLoader._load_single_file_context(file_path))
                
            if len(data_files) > 5:
                context_parts.append(f"\n... and {len(data_files) - 5} more files")
                
        except Exception as e:
            context_parts.append(f"Error loading directory {dir_path}: {e}")
            
        return context_parts


# Convenience function for easy import
def load_flat_context_data(data_path: str, context_name: str = "external_data") -> Optional[str]:
    """Convenience function to load flat context data."""
    return GenericContentLoader.load_flat_context_data(data_path, context_name) 