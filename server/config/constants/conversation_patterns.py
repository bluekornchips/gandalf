"""
Contains regex patterns and keywords for analyzing conversation content.
"""

import re

# Architecture Discussion Patterns

# Architecture-related keywords and patterns
ARCHITECTURE_KEYWORDS = [
    "architecture",
    "design",
    "pattern",
    "structure",
    "framework",
    "microservices",
    "monolith",
    "api",
    "database",
    "schema",
    "scalability",
    "performance",
    "optimization",
    "refactor",
    "component",
    "module",
    "interface",
    "abstraction",
    "dependency",
]

ARCHITECTURE_PATTERNS = [
    r"\b(?:system|software|application)\s+(?:design|architecture)\b",
    r"\b(?:design|architectural)\s+(?:pattern|decision)\b",
    r"\b(?:microservice|service-oriented|event-driven)\s+architecture\b",
    r"\b(?:database|data)\s+(?:design|schema|model)\b",
    r"\b(?:api|interface)\s+design\b",
]

# Debugging & Problem-Solving Patterns

# Debugging-related keywords
DEBUG_KEYWORDS = [
    "debug",
    "error",
    "bug",
    "issue",
    "problem",
    "fix",
    "solve",
    "troubleshoot",
    "diagnose",
    "investigate",
    "trace",
    "stack trace",
    "exception",
    "crash",
    "failure",
    "broken",
    "not working",
]

DEBUG_PATTERNS = [
    r"\b(?:debug|debugging|debugger)\b",
    r"\b(?:error|exception|stack\s+trace)\b",
    r"\b(?:bug|issue|problem)\s+(?:fix|solving|resolution)\b",
    r"\b(?:troubleshoot|diagnose|investigate)\b",
    r"\b(?:not\s+working|broken|failing|crash)\b",
]

# Problem-solving keywords
PROBLEM_SOLVING_KEYWORDS = [
    "solve",
    "solution",
    "resolve",
    "fix",
    "workaround",
    "approach",
    "strategy",
    "method",
    "technique",
    "implement",
    "implement",
    "how to",
    "best practice",
    "recommendation",
    "suggestion",
]

PROBLEM_SOLVING_PATTERNS = [
    r"\b(?:how\s+to|how\s+do\s+I|how\s+can\s+I)\b",
    r"\b(?:solution|solve|resolve|fix)\b",
    r"\b(?:best\s+practice|recommendation|approach)\b",
    r"\b(?:workaround|alternative|strategy)\b",
]

# Technical Discussion Patterns

# Technical keywords
TECHNICAL_KEYWORDS = [
    "code",
    "function",
    "method",
    "class",
    "variable",
    "algorithm",
    "implementation",
    "library",
    "framework",
    "tool",
    "technology",
    "programming",
    "development",
    "software",
    "application",
    "system",
]

TECHNICAL_PATTERNS = [
    r"\b(?:code|coding|programming)\b",
    r"\b(?:function|method|class|variable)\b",
    r"\b(?:algorithm|implementation|logic)\b",
    r"\b(?:library|framework|tool|technology)\b",
    r"\b(?:software|application|system)\s+(?:development|engineering)\b",
]

# Code Discussion Patterns

# Code-related keywords
CODE_KEYWORDS = [
    "code",
    "function",
    "method",
    "class",
    "variable",
    "parameter",
    "return",
    "import",
    "export",
    "module",
    "package",
    "library",
    "syntax",
    "logic",
    "algorithm",
    "implementation",
    "refactor",
]

CODE_PATTERNS = [
    r"\b(?:function|method|class)\s+(?:definition|declaration)\b",
    r"\b(?:import|export|require)\s+(?:statement|module)\b",
    r"\b(?:variable|parameter|argument)\s+(?:declaration|assignment)\b",
    r"\b(?:code|logic|algorithm)\s+(?:review|analysis|implementation)\b",
]

# Pattern Compilation

# Compile all patterns for performance
COMPILED_ARCHITECTURE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in ARCHITECTURE_PATTERNS
]
COMPILED_DEBUG_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in DEBUG_PATTERNS
]
COMPILED_PROBLEM_SOLVING_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in PROBLEM_SOLVING_PATTERNS
]
COMPILED_TECHNICAL_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in TECHNICAL_PATTERNS
]
COMPILED_CODE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in CODE_PATTERNS
]

# Pattern Groups for Analysis

# Grouped patterns for conversation analysis
CONVERSATION_PATTERN_GROUPS = {
    "architecture": {
        "keywords": ARCHITECTURE_KEYWORDS,
        "patterns": COMPILED_ARCHITECTURE_PATTERNS,
        "score_weight": 0.2,
    },
    "debugging": {
        "keywords": DEBUG_KEYWORDS,
        "patterns": COMPILED_DEBUG_PATTERNS,
        "score_weight": 0.25,
    },
    "problem_solving": {
        "keywords": PROBLEM_SOLVING_KEYWORDS,
        "patterns": COMPILED_PROBLEM_SOLVING_PATTERNS,
        "score_weight": 0.15,
    },
    "technical": {
        "keywords": TECHNICAL_KEYWORDS,
        "patterns": COMPILED_TECHNICAL_PATTERNS,
        "score_weight": 0.1,
    },
    "code_discussion": {
        "keywords": CODE_KEYWORDS,
        "patterns": COMPILED_CODE_PATTERNS,
        "score_weight": 0.1,
    },
}
