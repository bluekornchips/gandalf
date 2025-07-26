"""
Keyword extraction and project analysis utilities.

This module extracts contextual keywords from project files and structures
to improve conversation relevance scoring.
"""

import json
from pathlib import Path
from typing import Any

from src.config.config_data import (
    CONTEXT_SKIP_DIRECTORIES,
    TECHNOLOGY_KEYWORD_MAPPING,
)
from src.config.conversation_config import (
    CONTEXT_KEYWORD_MAX_COUNT,
    CONTEXT_MAX_FILES_TO_CHECK,
    CONTEXT_MIN_EXTENSIONS_BEFORE_DEEP_SCAN,
)
from src.utils.common import log_debug, log_error
from src.utils.memory_cache import get_keyword_cache


def generate_shared_context_keywords(project_root: Path) -> list[str]:
    """Generate context keywords with intelligent caching and weighting."""
    project_root_str = str(project_root)

    # More specific cache key that includes project modification info
    # for better cache hits
    cache_key = f"{project_root_str}"

    # Add project file modification time to cache key for better invalidation
    try:
        common_files = [
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "README.md",
        ]
        latest_mtime = 0.0
        for file_name in common_files:
            file_path = project_root / file_name
            if file_path.exists():
                mtime = file_path.stat().st_mtime
                latest_mtime = max(latest_mtime, mtime)
        if latest_mtime > 0:
            cache_key += f"_{int(latest_mtime)}"
    except (OSError, ValueError):
        pass

    # Check memory cache
    keyword_cache = get_keyword_cache()
    cached_keywords = keyword_cache.get(cache_key)
    if cached_keywords:
        log_debug(f"Using cached context keywords for {project_root.name}")
        return list(cached_keywords)

    # Generate keywords
    log_debug(f"Generating fresh context keywords for {project_root.name}")
    keywords = _extract_project_keywords(project_root)

    # Cache results using memory-aware cache
    keyword_cache.put(cache_key, keywords)

    return keywords


def _extract_project_keywords(project_root: Path) -> list[str]:
    """Extract keywords from project files and structure."""
    keywords = []

    try:
        # Add project name
        project_name = project_root.name.lower()
        keywords.append(project_name)

        # Check for common project files and extract keywords
        common_files = [
            "package.json",
            "pyproject.toml",
            "README.md",
            "CLAUDE.md",
            "requirements.txt",
        ]

        for file_name in common_files:
            file_path = project_root / file_name
            if file_path.exists():
                try:
                    # Use a larger limit for keyword extraction to ensure
                    # we can read small config files
                    content = file_path.read_text(encoding="utf-8")[:2000]
                    keywords.extend(extract_keywords_from_file(file_name, content))
                except (OSError, UnicodeDecodeError):
                    continue

        # Add technology keywords based on file extensions
        keywords.extend(extract_tech_keywords_from_files(project_root))

        # Remove duplicates, filter, and limit
        keywords = list(set(keywords))
        keywords = [k for k in keywords if len(k) > 1]  # Filter out single chars
        keywords = keywords[:CONTEXT_KEYWORD_MAX_COUNT]

        log_debug(f"Generated {len(keywords)} context keywords")
        return keywords

    except (OSError, ValueError, AttributeError, UnicodeDecodeError) as e:
        log_error(e, "extracting project keywords")
        if "project_name" in locals():
            return [project_name]
        else:
            return []


def extract_keywords_from_file(file_name: str, content: str) -> list[str]:
    """Extract keywords from specific file types."""
    keywords = []

    try:
        if file_name == "package.json":
            # Extract npm package keywords
            try:
                data = json.loads(content)
                if "name" in data:
                    keywords.append(data["name"])
                if "keywords" in data:
                    keywords.extend(data["keywords"][:5])
                if "dependencies" in data:
                    # Add major framework names
                    deps = data["dependencies"].keys()
                    for dep in deps:
                        if dep in [
                            "react",
                            "vue",
                            "angular",
                            "express",
                            "next",
                            "nuxt",
                        ]:
                            keywords.append(dep)
            except json.JSONDecodeError:
                pass

        elif file_name in ["README.md", "CLAUDE.md"]:
            # Extract common tech terms from markdown
            content_lower = content.lower()
            # Flatten the technology keyword mapping to get all terms
            all_tech_terms: list[str] = []
            for tech_category, tech_data in TECHNOLOGY_KEYWORD_MAPPING.items():
                tech_data_typed: list[str] | dict[str, Any] = tech_data
                if isinstance(tech_data_typed, dict):
                    # New format: {"keywords": [...], "extensions": [...]}
                    all_tech_terms.extend(tech_data_typed.get("keywords", []))
                elif isinstance(tech_data_typed, list):
                    # Legacy format: direct list of terms
                    all_tech_terms.extend(tech_data_typed)

            for term in all_tech_terms:
                if term.lower() in content_lower:
                    keywords.append(term)

        elif file_name == "pyproject.toml":
            # Extract Python project info
            content_lower = content.lower()
            python_frameworks = {
                "django": "django",
                "flask": "flask",
                "fastapi": "fastapi",
                "pytest": "pytest",
                "poetry": "poetry",
                "setuptools": "setuptools",
            }

            for term, keyword in python_frameworks.items():
                if term in content_lower:
                    keywords.append(keyword)

        elif file_name == "requirements.txt":
            # Extract package names from requirements
            lines = content.split("\n")
            for line in lines[:10]:  # Limit to first 10 packages
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name (everything before ==, >=, etc.)
                    package_name = (
                        line.split("==")[0].split(">=")[0].split("<=")[0].strip()
                    )
                    if package_name:
                        keywords.append(package_name)

    except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
        log_debug(f"Error extracting keywords from {file_name}: {e}")

    return keywords


def extract_tech_keywords_from_files(project_root: Path) -> list[str]:
    """Extract technology keywords based on file extensions in project."""
    keywords = []

    try:
        # Fast sampling approach: only check top-level directories and limit depth
        file_extensions = set()
        files_checked = 0

        # Check top-level files first (most likely to indicate tech stack)
        for file_path in project_root.iterdir():
            if files_checked >= CONTEXT_MAX_FILES_TO_CHECK:
                break
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext:
                    file_extensions.add(ext)
                files_checked += 1

        # If we haven't found enough variety, check one level deeper but with limits
        if (
            len(file_extensions) < CONTEXT_MIN_EXTENSIONS_BEFORE_DEEP_SCAN
            and files_checked < CONTEXT_MAX_FILES_TO_CHECK
        ):
            for subdir in project_root.iterdir():
                if files_checked >= CONTEXT_MAX_FILES_TO_CHECK:
                    break
                if subdir.is_dir() and not subdir.name.startswith("."):
                    # Skip common directories that don't indicate tech stack
                    if subdir.name in CONTEXT_SKIP_DIRECTORIES:
                        continue

                    try:
                        for file_path in subdir.iterdir():
                            if files_checked >= CONTEXT_MAX_FILES_TO_CHECK:
                                break
                            if file_path.is_file():
                                ext = file_path.suffix.lower()
                                if ext:
                                    file_extensions.add(ext)
                                files_checked += 1
                    except (OSError, PermissionError):
                        continue

        # Map extensions to technologies (only supported languages)
        ext_mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "react",
            ".tsx": "react",
            ".vue": "vue",
            ".go": "golang",
            ".rs": "rust",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".php": "php",
            ".rb": "ruby",
            ".swift": "swift",
            ".kt": "kotlin",
            ".dart": "dart",
            ".sh": "bash",
            ".sql": "sql",
            ".html": "html",
            ".css": "css",
            ".scss": "sass",
            ".less": "less",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".md": "markdown",
        }

        for ext in file_extensions:
            if ext in ext_mapping:
                keywords.append(ext_mapping[ext])

        # Add special project indicators
        special_files = {
            "docker": ["Dockerfile", "docker-compose.yml", ".dockerignore"],
            "kubernetes": ["deployment.yaml", "service.yaml", "ingress.yaml"],
            "terraform": [".tf", ".tfvars"],
            "ansible": ["playbook.yml", "ansible.cfg"],
            "makefile": ["Makefile", "makefile"],
            "cmake": ["CMakeLists.txt"],
            "gradle": ["build.gradle", "gradle.properties"],
            "maven": ["pom.xml"],
        }

        for tech, files in special_files.items():
            for special_file in files:
                if (project_root / special_file).exists():
                    keywords.append(tech)
                    break

    except (OSError, PermissionError, ValueError, AttributeError) as e:
        log_debug(f"Error extracting tech keywords: {e}")

    return keywords


def get_project_summary(project_root: Path) -> dict[str, Any]:
    """Get a comprehensive summary of the project's technical characteristics."""
    try:
        keywords = generate_shared_context_keywords(project_root)

        summary: dict[str, Any] = {
            "project_name": project_root.name,
            "total_keywords": len(keywords),
            "keywords": keywords,
            "technologies": [],
            "frameworks": [],
            "languages": [],
        }

        # Categorize keywords
        for keyword in keywords:
            # Check if it's a known technology
            for tech_category, tech_data in TECHNOLOGY_KEYWORD_MAPPING.items():
                tech_data_typed: list[str] | dict[str, Any] = tech_data
                if isinstance(tech_data_typed, dict):
                    if keyword in tech_data_typed.get("keywords", []):
                        summary["technologies"].append(keyword)
                elif isinstance(tech_data_typed, list):
                    if keyword in tech_data_typed:
                        summary["technologies"].append(keyword)

        # Identify programming languages
        languages = [
            "python",
            "javascript",
            "typescript",
            "java",
            "cpp",
            "c",
            "go",
            "rust",
            "php",
            "ruby",
            "swift",
            "kotlin",
            "dart",
        ]
        summary["languages"] = [lang for lang in keywords if lang in languages]

        # Identify frameworks
        frameworks = [
            "react",
            "vue",
            "angular",
            "django",
            "flask",
            "fastapi",
            "express",
            "next",
            "nuxt",
        ]
        summary["frameworks"] = [fw for fw in keywords if fw in frameworks]

        return summary

    except Exception as e:
        log_error(e, "generating project summary")
        return {
            "project_name": project_root.name,
            "total_keywords": 0,
            "keywords": [],
            "technologies": [],
            "frameworks": [],
            "languages": [],
        }
