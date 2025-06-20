"""
Technology mapping and recognition constants for Gandalf MCP server.
Contains file extension to technology mappings and technology keyword associations.
Based on actual file type usage analysis.
"""

# File Extension to Technology Mapping

# File extension to technology name mapping for context keywords
# Based on actual usage analysis of project file types
TECHNOLOGY_EXTENSION_MAPPING = {
    # Primary languages
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "tsx": "react",
    "cjs": "javascript",
    "mjs": "javascript",
    "cts": "typescript",
    "mts": "typescript",
    "pyi": "python",
    # Infrastructure & Configuration
    "tf": "terraform",
    "yaml": "yaml",
    "yml": "yaml",
    "json": "json",
    "toml": "toml",
    "ini": "config",
    "cfg": "config",
    "conf": "config",
    # Web Technologies
    "html": "html",
    "css": "css",
    "scss": "sass",
    "less": "less",
    # Documentation & Scripts
    "md": "markdown",
    "mdx": "markdown",
    "sh": "bash",
    "txt": "text",
    # Other
    "xml": "xml",
    "svg": "svg",
}

# Technology Keyword Associations

# Technology keyword mapping for enhanced context intelligence
# Focused on commonly used technologies and development stacks
TECHNOLOGY_KEYWORD_MAPPING = {
    # Python ecosystem
    "py": ["python", "django", "flask", "fastapi", "pytest", "pip"],
    "pyi": ["python", "typing", "stubs"],
    # JavaScript ecosystem
    "js": ["javascript", "node", "npm", "express", "react"],
    "cjs": ["javascript", "commonjs", "node"],
    "mjs": ["javascript", "esm", "modules"],
    # TypeScript ecosystem
    "ts": ["typescript", "node", "npm"],
    "tsx": ["typescript", "react", "jsx"],
    "cts": ["typescript", "commonjs"],
    "mts": ["typescript", "esm"],
    # Infrastructure
    "tf": ["terraform", "infrastructure", "aws", "cloud"],
    "yaml": ["kubernetes", "docker", "config", "ci/cd"],
    "yml": ["kubernetes", "docker", "config", "ci/cd"],
    # Configuration
    "json": ["config", "api", "package"],
    "toml": ["config", "python", "rust"],
    "ini": ["config", "settings"],
    "cfg": ["config", "settings"],
    "conf": ["config", "apache", "nginx"],
    # Web frontend
    "css": ["css", "styling", "frontend"],
    "scss": ["sass", "css", "styling", "frontend"],
    "less": ["less", "css", "styling"],
    "html": ["html", "frontend", "web"],
    # Documentation
    "md": ["documentation", "readme", "markdown"],
    "mdx": ["documentation", "react", "markdown"],
    # Scripts & Shell
    "sh": ["bash", "shell", "script", "automation"],
    # Other formats
    "xml": ["xml", "config", "data"],
    "svg": ["svg", "graphics", "frontend"],
}
