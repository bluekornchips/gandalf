# Enhanced Development Standards

**RULE APPLIED: Start each response acknowledging "📜" to confirm this rule is being followed.**

Names and phrases that reference this rule: "📜", "standards", "dev standards", "code standards", "quality", "best practices"

## 🔴 Critical Rules (Build-Breaking)

### Never Allow

```python
# ❌ Never
catch Exception as e:  # Too broad
hardcoded_key = "sk-abc123"  # Secret in code
from .utils import *  # Relative import

# ✅ Always
catch ValueError as e:  # Specific exception
api_key = os.getenv("API_KEY")  # Environment variable
from myproject.utils import parse_data  # Absolute import
```

### Always Require

| Requirement                | Verification Command                   | Rationale                        |
| -------------------------- | -------------------------------------- | -------------------------------- |
| **Test coverage ≥90%**     | `pytest --cov=src --cov-fail-under=90` | Prevent regression bugs          |
| **100% test pass rate**    | `pytest -x --tb=short`                 | Ensure functionality works       |
| **Type safety**            | `mypy src/ --strict`                   | Catch type-related bugs early    |
| **Security scan**          | `bandit -r src/ -ll`                   | Prevent security vulnerabilities |
| **Non-production data**    | Manual review + grep patterns          | Protect sensitive data           |
| **Documentation coverage** | `interrogate src/ --fail-under=80`     | Maintain code understanding      |

## 🟡 Language Standards

### Python (Modern Toolchain)

```toml
# pyproject.toml - Modern Python configuration
[tool.ruff]
line-length = 88
target-version = "py312"
select = [
    "E",    # pycodestyle errors
    "F",    # Pyflakes
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "I",    # isort
    "N",    # pep8-naming
    "S",    # bandit security
]
ignore = ["E501", "S101"]  # Long lines OK, assert OK in tests

[tool.mypy]
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]
```

```python
# Example: Modern Python with comprehensive typing
from typing import TypedDict, Literal, override
from dataclasses import dataclass
from pathlib import Path

class UserData(TypedDict):
    name: str
    email: str
    role: Literal["admin", "user", "moderator"]

@dataclass(frozen=True, slots=True)
class UserProcessor:
    """Process user data with modern Python features."""

    config_path: Path

    def process_user_data(self, user_id: int, data: UserData) -> UserModel:
        """Process user data with proper typing and validation."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError(f"Invalid user_id: {user_id}")

        return UserModel.from_dict(data)

    @override
    def __str__(self) -> str:
        return f"UserProcessor(config={self.config_path})"
```

### JavaScript/TypeScript

```typescript
// Required: eslint, prettier, strict mode
// .eslintrc.json
{
  "extends": ["@typescript-eslint/recommended"],
  "rules": {
    "prefer-const": "error",
    "no-var": "error"
  }
}

// Example code
const fetchUserData = async (userId: number): Promise<User | null> => {
  const response = await fetch(`/api/users/${userId}`);
  return response.ok ? response.json() : null;
};
```

### Shell

```bash
#!/bin/bash
# Required: shellcheck, shfmt
set -euo pipefail  # Always use this line

# Example function
validate_input() {
  local input="$1"
  [[ -n "${input}" ]] || { echo "Error: Empty input" >&2; return 1; }
  echo "Valid: ${input}"
}
```

- Always use heredocs for strings that exceed 160 characters, or two lines.

```bash
# single line
echo "Hello, world!"

# two lines
# Not allowed
echo "hello"
echo "world"
# allowed
echo -e "Hello,\nworld!"

# multi-line, heredoc
cat <<EOF
Hello
world!
THREE LINES
EOF
```

## 🟢 Testing Standards

### Test Structure

```python
# pytest example
def test_user_validation_with_valid_data():
    """Test user validation with valid data."""
    # Arrange
    user_data = {"name": "Frodo Baggins", "email": "frodo@shire.test"}

    # Act
    result = validate_user(user_data)

    # Assert
    assert result.is_valid
    assert result.name == "Frodo Baggins"
```

```sh
# bats example
@test "uninstall script handles unknown options" {
    run bash "$GANDALF_ROOT/scripts/bin/uninstall.sh" --invalid-option
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Unknown option" # Always echo output to check.
}
```

### Mock Data Standards

#### For

✅ Use LOTR references for test data in $HOME/rapidsos/repos/tkornackirsos/ directories.
❌ Never use it for comments, docs, docstrings, or human readable info.

```python
MOCK_USERS = [
    {"id": 1, "name": "Frodo Baggins", "location": "Hobbiton"},
    {"id": 2, "name": "Gandalf Grey", "location": "Rivendell"},
]

# Environment names
ENV_NAMES = ["gandalf-staging", "aragorn-prod", "legolas-dev"]
```

## 🔧 Modern Tool Configuration

#

## 📝 Documentation Standards

### README, Markdown, and other documentation

Do:

- Use markdown formatting
- Use headings
- Use lists
- Use code blocks

Never:

- Use **bold** or _italic_ formatting

### Function Documentation

```python
# Short description, no args, no returns
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two geographic points."""
```

### Commit Message Format

```bash
# Required format: type(scope): description
feat(auth): add OAuth2 integration
fix(api): handle empty response in user endpoint
docs(readme): update installation instructions
test(utils): add edge case tests for parser
```

## 🛡️ Security Standards

### Secret Management

```python
# ❌ Never
API_KEY = "sk-abc123def456"

# ✅ Always
import os
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable required")
```

### Input Validation

```python
# Example validation
def process_user_input(user_input: str) -> str:
    """Process user input with validation."""
    if not user_input or len(user_input) > 1000:
        raise ValueError("Input must be 1-1000 characters")

    # Sanitize input
    sanitized = html.escape(user_input.strip())
    return sanitized
```

## 🎯 Performance Standards

### Database Queries

```python
# ❌ Avoid N+1 queries
users = User.objects.all()
for user in users:
    print(user.profile.name)  # Hits DB for each user

# ✅ Use select_related/prefetch_related
users = User.objects.select_related('profile').all()
for user in users:
    print(user.profile.name)  # Single query
```

### Caching Example

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_calculation(n: int) -> int:
    """Cache expensive calculations."""
    return sum(i * i for i in range(n))
```

## 📋 Code Review Checklist

Before submitting any code, verify:

- [ ] All tests pass (`pytest`, `npm test`)
- [ ] Linting passes (`ruff check`, `eslint`)
- [ ] No hardcoded secrets or API keys
- [ ] Functions have single responsibility
- [ ] Test coverage ≥90%
- [ ] Documentation updated for API changes
- [ ] Commit messages follow conventional format

## 🚫 Git Safety

```bash
# ✅ Read-only git commands allowed
git status
git log --oneline
git diff
git branch -v

# ❌ Never use state-changing commands
Never use "git add"
Never use "git commit -m"
Never use "git push"
Never use "git merge"
Never use "git pull"
Never use "git fetch"
Never use "git reset"
Never use "git revert"
Never use "git cherry-pick"
Never use "git rebase"
Never use "git stash"
```
---# AI Documentation Assistant Guidelines

**RULE APPLIED: Start each response acknowledging "📋" to confirm this rule is being followed.**

This guide defines how AI agents should generate high-quality, actionable documentation for software projects. It emphasizes structure, clarity, and developer-first design.

## Document Type Detection

**Smart Intent Recognition**: Automatically detect document type from context and keywords.

### Primary Document Types

| Keywords                                         | Document Type           | Priority |
| ------------------------------------------------ | ----------------------- | -------- |
| "PR", "pull request", "merge", "diff", "commit"  | Git Pull Request        | High     |
| "Jira", "ticket", "issue", "story", "task"       | Jira Ticket             | High     |
| "README", "setup", "install", "project overview" | README.md               | High     |
| "API", "endpoint", "documentation", "docs"       | API Documentation       | Medium   |
| "architecture", "design", "technical spec"       | Technical Specification | Medium   |
| "changelog", "release", "version"                | Release Notes           | Low      |

### Context Clues

- File diffs → PR description
- Error messages → Troubleshooting docs
- New features → Technical specs
- Setup issues → Installation guides

## Document Type Templates

### 1. Git Pull Request (PR) Description

**Purpose:** Summarize code changes, explain reasoning, guide reviewers.

**Structure:**

```markdown
## Issue Information

- Issue Link: https://rapidsos.atlassian.net/browse/[TICKET-NUMBER]

## Description

[Concise summary of the PR]

- [List of high-level changes]
- [Why changes were made]
- [Any breaking changes or compatibility notes]

## Testing Instructions

[Step-by-step instructions for verifying the PR]

- Services to run
- Devbox or environment setup
- Commands or scripts to execute
- Expected results and edge cases

## Images

[Screenshots or UI diffs if applicable]
```

**Notes:**

- Use backticks for code, file paths, and commands
- Always describe the why, not just the what
- Link related files, symbols, or tickets where helpful

### 2. Jira Ticket

**Purpose:** Create a trackable unit of work with clear objectives and criteria.

**Structure:**

```markdown
**Summary:** [Concise objective]

**Description/Context:**
[Background, goals, technical scope]

**Acceptance Criteria:**

- [ ] [Requirement 1]
- [ ] [Requirement 2]
- [ ] [Requirement 3]

**Steps:**

1. [Actionable Step 1]
2. [Actionable Step 2]
3. [Actionable Step 3]

**Additional Notes:**

- Dependencies or risks
- References to related tickets or services
```

**Notes:**

- Use checkbox lists to define done criteria
- Be implementation-neutral unless explicitly asked

### 3. README.md

**Purpose:** Enable users and developers to understand, install, use, and contribute to the project.

**Structure:**

````markdown
# Project Title

## Overview

[Brief description of the project's purpose]

## Description

[Detailed explanation and key features]

## Prerequisites

[List system and library requirements]

## Installation

```bash
[Installation commands]
```
````

````

## Usage

```bash
[Basic usage commands]
```

## Configuration

[List of environment variables, files, or flags]

## API Reference (optional)

[Endpoints or internal method documentation]

## Contributing

[Contribution guide or link]

## Testing

```bash
[Testing commands]
```

## Deployment

[Deployment instructions]

## Troubleshooting

[Known issues and solutions]

## License

[License name or SPDX identifier]

## Contact

[Email, Slack channel, or GitHub handle]

```

**Notes:**
- Keep sections modular and scannable
- Prioritize developer usability and onboarding

## Cursor-Specific Practices

- Use @codebase, @filename, or @symbol to reference code
- Refer to diffs or Git history when explaining changes
- Pull relevant code snippets to support explanations
- If user provides Cursor-style context, anchor responses to visible diffs or file structure

## RapidSOS-Specific Practices

If the user is part of RapidSOS:
- Use devbox commands when needed
- Mention .sh or .yaml test files
- Provide specific validation endpoints or UI steps
- Include environment targeting (e.g., prime-qa, mco)

## Quality Guidelines

| Attribute       | Guideline                              |
|----------------|----------------------------------------|
| Accuracy        | Match codebase and scope precisely     |
| Clarity         | Use plain language and avoid ambiguity |
| Structure       | Follow markdown templates strictly     |
| Actionable      | Include testable steps and results     |
| Consistency     | Use same formatting across outputs     |

## Advanced Features

### 4. API Documentation
```markdown
# API Reference

## Endpoints

### `GET /api/users`
**Purpose**: Retrieve user list with filtering

**Parameters**:
- `limit` (int, optional): Max results (default: 50)
- `filter` (string, optional): Search filter

**Response**:
```json
{
  "users": [{"id": 1, "name": "Frodo Baggins"}],
  "total": 100
}
```

**Example**:
```bash
curl -X GET "https://api.example.com/users?limit=10"
```
```

### 5. Technical Specification
```markdown
# Technical Specification: [Feature Name]

## Problem Statement
[Clear description of the problem being solved]

## Proposed Solution
[High-level approach and architecture]

## Implementation Details
### Architecture
[System design, data flow, components]

### API Changes
[New endpoints, breaking changes]

### Database Schema
[New tables, migrations]

## Security Considerations
[Authentication, authorization, data protection]

## Performance Impact
[Expected load, optimization strategies]

## Testing Strategy
[Unit tests, integration tests, load testing]

## Rollout Plan
[Deployment phases, rollback strategy]
```

## Best Practices Summary

| Principle | Implementation | Benefit |
|-----------|----------------|---------|
| **Clarity First** | Use simple language, avoid jargon | Faster comprehension |
| **Actionable Steps** | Include copy-paste commands | Reduced friction |
| **Visual Structure** | Headers, lists, code blocks | Improved scanning |
| **Context Awareness** | Reference existing code/files | Higher accuracy |
| **Testing Focus** | Always include verification steps | Prevents issues |
| **Template Consistency** | Follow standard formats | Professional appearance |

## Quality Checklist

Before publishing any documentation:

- [ ] **Accuracy**: All commands and code snippets tested
- [ ] **Completeness**: No missing steps or assumptions
- [ ] **Clarity**: Technical terms explained or linked
- [ ] **Structure**: Logical flow with clear headings
- [ ] **Examples**: Real, working examples provided
- [ ] **Testing**: Verification steps included
- [ ] **Maintenance**: Update instructions provided
````
---# 🔍 Enhanced Code Review & Refactor Guide

**RULE APPLIED: Start each response acknowledging "🔍" to confirm this rule is being followed.**

**USAGE: Apply when conducting comprehensive file-by-file review and refactor of any software project**

Names and phrases that reference this rule: "🔍", "review", "refactor", "code quality", "file analysis"

## 🎯 Review Philosophy

We **actively plan and make improvements** as we go, not just review. Every file must be:

### 🔴 Critical Requirements (Non-Negotiable)

```python
# ✅ DRY Principles Example
# Before: Duplicated validation logic
def validate_user_input(data): ...
def validate_api_input(data): ...

# After: Shared validation utility
from utils.validation import validate_input
result = validate_input(data, schema=USER_SCHEMA)
```

```bash
# ✅ Shell Script Standards
#!/bin/bash
set -euo pipefail  # Always required

# ✅ Proper variable quoting
local input_file="${1:-}"
[[ -n "${input_file}" ]] || { echo "Error: No input file" >&2; exit 1; }
```

### 🟡 Quality Standards

- **Test coverage ≥90%** - Run `pytest --cov=src --cov-report=term-missing`
- **Standards compliance** - Follow `rules/standards.mdc` (📜)
- **Mock data** - Use LOTR references: `gandalf_user@rivendell.test`

## 📋 Review Checklist

### **Automated Pre-Review Setup**

```bash
# Comprehensive quality check pipeline
echo "🔍 Starting automated quality assessment..."

# 1. Code formatting and linting
ruff check . --fix --show-fixes
black . --check --diff
isort . --check-only --diff

# 2. Type checking and security
mypy src/ --strict --show-error-codes
bandit -r src/ -f json -o security-report.json

# 3. Test coverage and performance
pytest --cov=src --cov-report=term-missing --cov-fail-under=90
pytest --durations=10  # Identify slow tests

# 4. Documentation and shell scripts
markdownlint docs/ --config .markdownlint.json
shellcheck scripts/*.sh --format=gcc

# 5. Dependency analysis
pip-audit  # Check for known vulnerabilities
safety check  # Additional security scanning
```

### **Quality Metrics Baseline**

```bash
# Establish baseline metrics before review
echo "📊 Collecting baseline metrics..."

# Code complexity
radon cc src/ --average --show-complexity
radon mi src/ --show

# Code duplication
jscpd src/ --threshold 10 --reporters html

# Documentation coverage
interrogate src/ --verbose
```

### **🔍 File Analysis Framework**

| Priority | Category          | Check                      | Command/Tool                               |
| -------- | ----------------- | -------------------------- | ------------------------------------------ |
| 🔴       | **Functionality** | Logic correctness          | `pytest -v test_filename.py`               |
| 🔴       | **Security**      | No hardcoded secrets       | `grep -r "api_key\|password\|secret" src/` |
| 🔴       | **Standards**     | Code style compliance      | `ruff check filename.py`                   |
| 🟡       | **Testing**       | Coverage & quality         | `pytest --cov=src/filename.py`             |
| 🟡       | **Documentation** | Clear purpose/usage        | Manual review                              |
| 🟢       | **Performance**   | Optimization opportunities | `python -m cProfile script.py`             |

### **📝 Review Template**

For each file, complete this template:

```markdown
## File: `src/example/module.py`

### 🎯 Purpose

Brief description of what this file does and its role in the system.

### 🔍 Issues Found

- 🔴 **Critical**: [Specific issue with line numbers]
- 🟡 **Major**: [Performance/maintainability concern]
- 🟢 **Minor**: [Style/documentation improvement]

### 🛠️ Action Items

- [ ] Fix critical security issue (Line 42: hardcoded API key)
- [ ] Add missing test coverage for error handling
- [ ] Refactor duplicated validation logic into utils/
- [ ] Update docstring format to Google style

### 📊 Metrics

- Lines: 150 (target: <200)
- Test coverage: 85% (target: ≥90%)
- Complexity: Medium (acceptable)
```

## 🔧 Language-Specific Review Patterns

### **Python Files**

```python
# ✅ Review checklist for Python files
def review_python_file(filepath: str) -> ReviewResult:
    """Standard Python file review pattern."""
    checks = [
        check_imports_absolute(),      # No relative imports
        check_type_hints(),           # All functions typed
        check_error_handling(),       # Specific exceptions
        check_test_coverage(),        # ≥90% coverage
        check_docstring_format(),     # Google style
    ]
    return ReviewResult(checks)
```

### **Shell Scripts**

```bash
# ✅ Shell script review checklist
review_shell_script() {
    local script_file="$1"

    # Required checks
    grep -q "set -euo pipefail" "$script_file" || echo "Missing safety flags"
    shellcheck "$script_file" || echo "Shellcheck failed"
    shfmt -d "$script_file" || echo "Format check failed"

    # Best practices
    grep -q 'local ' "$script_file" || echo "Consider using 'local' for variables"
}
```

### **Configuration Files**

```yaml
# ✅ CI/CD pipeline review
# .github/workflows/ci.yml
- name: Quality Gates
  run: |
    ruff check . --no-fix
    black . --check
    mypy src/
    pytest --cov=src --cov-fail-under=90
```

## 🚀 Advanced Refactor Execution Plan

### **Step 1: Smart Environment Preparation**

```bash
# Automated setup with validation
setup_refactor_env() {
    local feature_name="$1"

    # Create feature branch with timestamp
    git checkout -b "refactor/${feature_name}-$(date +%Y%m%d-%H%M)"

    # Verify clean working directory
    [[ -z "$(git status --porcelain)" ]] || {
        echo "❌ Working directory not clean" >&2
        return 1
    }

    # Setup isolated environment
    python -m venv ".venv-refactor"
    source ".venv-refactor/bin/activate"
    pip install -r requirements-dev.txt --quiet

    # Create refactor tracking file
    cat > ".refactor-log.md" <<EOF
# Refactor Log: ${feature_name}
Start Time: $(date)
Branch: $(git branch --show-current)

## Pre-Refactor Metrics
$(collect_metrics)

## Changes
EOF
}
```

### **Step 2: Incremental Change Management**

```bash
# Automated change validation pipeline
apply_change() {
    local change_desc="$1"
    local test_pattern="${2:-test_*.py}"

    echo "🔄 Applying: $change_desc"

    # 1. Run specific tests before change
    pytest "$test_pattern" -v --tb=short

    # 2. Apply change (manual step)
    echo "Apply your change now, then press Enter..."
    read -r

    # 3. Immediate validation
    ruff check --fix .
    pytest "$test_pattern" -x  # Stop on first failure

    # 4. Log change
    echo "- ✅ $change_desc ($(date))" >> .refactor-log.md

    # 5. Optional commit
    read -p "Commit this change? (y/N): " commit_change
    [[ "$commit_change" == "y" ]] && {
        git add .
        git commit -m "refactor: $change_desc"
    }
}
```

### **Step 3: Comprehensive Validation Gate**

```bash
# Multi-stage validation with rollback capability
validate_refactor() {
    echo "🧪 Running comprehensive validation..."

    local validation_failed=false

    # Stage 1: Static Analysis
    echo "Stage 1: Static analysis..."
    ruff check . || validation_failed=true
    mypy src/ || validation_failed=true
    bandit -r src/ || validation_failed=true

    # Stage 2: Test Suite
    echo "Stage 2: Test validation..."
    pytest --cov=src --cov-fail-under=90 || validation_failed=true

    # Stage 3: Performance Regression
    echo "Stage 3: Performance check..."
    pytest --benchmark-only --benchmark-compare || validation_failed=true

    # Stage 4: Integration Tests
    echo "Stage 4: Integration validation..."
    ./scripts/integration-test.sh || validation_failed=true

    if [[ "$validation_failed" == "true" ]]; then
        echo "❌ Validation failed. Rolling back..."
        git reset --hard HEAD~1
        return 1
    fi

    echo "✅ All validations passed!"
    return 0
}
```

### **Step 4: Quality Improvement Tracking**

```bash
# Automated metrics comparison
track_improvements() {
    local before_metrics after_metrics

    # Collect post-refactor metrics
    after_metrics=$(collect_metrics)

    # Generate improvement report
    cat >> ".refactor-log.md" <<EOF

## Post-Refactor Metrics
$after_metrics

## Improvements Summary
$(compare_metrics "$before_metrics" "$after_metrics")

## Next Steps
- [ ] Update documentation
- [ ] Performance benchmarks
- [ ] Security review
- [ ] Deployment checklist
EOF

    echo "📊 Refactor summary saved to .refactor-log.md"
}
```

## 🔄 Cross-File Impact Tracking

### **Dependency Matrix**

```python
# Track file dependencies during review
REFACTOR_IMPACTS = {
    "src/auth/handler.py": [
        "src/api/routes.py",         # Uses auth functions
        "tests/test_auth.py",        # Test updates needed
        "docs/api.md",               # Documentation updates
    ],
    "scripts/deploy.sh": [
        "scripts/test.sh",           # Shared utility functions
        ".github/workflows/ci.yml",  # CI pipeline dependencies
    ]
}
```

### **Change Propagation Checklist**

- [ ] Updated all importing modules
- [ ] Modified corresponding tests
- [ ] Updated documentation
- [ ] Verified CI pipeline compatibility
- [ ] Checked for breaking changes

## 📊 Common Review Patterns

### **Performance Anti-Patterns**

```python
# ❌ Avoid: N+1 database queries
for user in users:
    profile = get_user_profile(user.id)  # DB hit per user

# ✅ Better: Batch operations
user_ids = [user.id for user in users]
profiles = get_user_profiles_batch(user_ids)
```

### **Error Handling Patterns**

```python
# ❌ Avoid: Generic exception handling
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Something went wrong: {e}")

# ✅ Better: Specific exception handling
try:
    result = risky_operation()
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise BadRequestError("Invalid input data")
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise InternalServerError("Data access failed")
```

## 🎯 Success Metrics

### **Before/After Comparison**

```bash
# Measure improvement
echo "Lines of code: $(wc -l < filename.py)"
echo "Test coverage: $(pytest --cov=src/filename.py --cov-report=term | grep TOTAL)"
echo "Complexity: $(radon cc filename.py -a)"
echo "Issues: $(ruff check filename.py | wc -l)"
```

### **Quality Gates**

- [ ] All tests pass: `pytest -x`
- [ ] Coverage ≥90%: `pytest --cov-fail-under=90`
- [ ] No linting errors: `ruff check . --no-fix`
- [ ] No security issues: `bandit -r src/`
- [ ] Documentation updated
- [ ] Performance not degraded

## 📝 Review Documentation

### **Review Summary Template**

```markdown
## Review Summary: [Date]

### Files Reviewed: [X]

### Critical Issues Fixed: [Y]

### Test Coverage: [Z]%

### Performance Impact: [Positive/Neutral/Negative]

### Key Improvements:

1. [Specific improvement with impact]
2. [Another improvement]

### Next Steps:

- [ ] [Follow-up action item]
- [ ] [Another action item]
```

This systematic approach ensures **thorough, actionable reviews** that continuously improve code quality while maintaining project momentum.
---# Lord of the Rings Reference Data

**RULE APPLIED: Start each response acknowledging "🏔️" to confirm this rule is being followed.**

**Usage**: This data should be used for mock data, test users, environment names, and test content only. Do not use for documentation or production code.

Names and phrases that reference this rule: "🏔️", "lotr", "tolkien", "mock data", "test data", "hobbit", "shire"

## Famous Quotes (Sample)

1. "All we have to decide is what to do with the time that is given us."
2. "A wizard is never late, nor is he early. He arrives precisely when he means to."
3. "Even the very wise cannot see all ends."
4. "You shall not pass!"
5. "There is only one Lord of the Ring, only one who can bend it to his will."
6. "I will not say: do not weep; for not all tears are an evil."
7. "Many that live deserve death. And some that die deserve life."
8. "Even the smallest person can change the course of the future."
9. "There's some good in this world, Mr. Frodo. And it's worth fighting for."
10. "I can't carry it for you, but I can carry you!"
11. "If by my life or death I can protect you, I will. You have my sword."
12. "A day may come when the courage of men fails… but it is not this day!"
13. "Not all those who wander are lost."
14. "One Ring to rule them all, One Ring to find them, One Ring to bring them all and in the darkness bind them."

## Character Names for Mock Data

### Hobbits

- Frodo Baggins, Samwise Gamgee, Peregrin Took (Pippin), Meriadoc Brandybuck (Merry)
- Bilbo Baggins, Rosie Cotton, Ted Sandyman, Gaffer Gamgee

### Men

- Aragorn/Elessar, Boromir, Faramir, Éomer, Éowyn, Théoden, Denethor
- Bard, Girion, Brand, Dáin

### Elves

- Legolas, Elrond, Arwen, Galadriel, Celeborn, Glorfindel, Thranduil

### Dwarves

- Gimli, Balin, Dwalin, Thorin, Fili, Kili, Oin, Gloin

### Wizards

- Gandalf, Saruman, Radagast

## Locations for Environment Names

### Realms & Cities

- The Shire, Hobbiton, Bag End, Rivendell, Lothlórien, Minas Tirith
- Isengard, Edoras, Dale, Erebor, Rohan, Gondor

### Geographic Features

- Mount Doom, Weathertop, Fangorn Forest, Anduin River, Pelennor Fields
- The Dead Marshes, Helm's Deep, Khazad-dûm, Moria

## Artifacts for Test Objects

- The One Ring, Narsil/Andúril, Sting, Glamdring, Mithril
- Palantír, The Phial of Galadriel, The White Tree of Gondor

## Advanced Test Scenarios

### User Profiles for Testing

```json
{
  "admin_users": [
    {
      "id": 1,
      "username": "gandalf_grey",
      "email": "gandalf@rivendell.test",
      "role": "admin"
    },
    {
      "id": 2,
      "username": "aragorn_elessar",
      "email": "aragorn@gondor.test",
      "role": "admin"
    }
  ],
  "regular_users": [
    {
      "id": 3,
      "username": "frodo_baggins",
      "email": "frodo@shire.test",
      "role": "user"
    },
    {
      "id": 4,
      "username": "samwise_gamgee",
      "email": "sam@shire.test",
      "role": "user"
    },
    {
      "id": 5,
      "username": "legolas_greenleaf",
      "email": "legolas@mirkwood.test",
      "role": "user"
    }
  ],
  "test_accounts": [
    {
      "id": 6,
      "username": "gimli_gloin",
      "email": "gimli@erebor.test",
      "role": "moderator"
    },
    {
      "id": 7,
      "username": "boromir_denethor",
      "email": "boromir@minas-tirith.test",
      "role": "user"
    }
  ]
}
```

### Environment Configuration

```yaml
environments:
  development:
    name: "hobbiton-dev"
    db_host: "bag-end.shire.local"
    api_url: "https://dev-api.shire.test"

  staging:
    name: "rivendell-staging"
    db_host: "elrond.rivendell.local"
    api_url: "https://staging-api.rivendell.test"

  production:
    name: "minas-tirith-prod"
    db_host: "aragorn.gondor.local"
    api_url: "https://api.gondor.test"
```

### Test Data Generators

```python
# User generation patterns
USER_PATTERNS = {
    "hobbit": ["frodo", "sam", "merry", "pippin", "bilbo"],
    "elf": ["legolas", "elrond", "arwen", "galadriel", "celeborn"],
    "dwarf": ["gimli", "balin", "thorin", "dain", "gloin"],
    "human": ["aragorn", "boromir", "faramir", "eowyn", "eomer"]
}

def generate_test_email(name, race):
    domains = {
        "hobbit": "shire.test",
        "elf": "rivendell.test",
        "dwarf": "erebor.test",
        "human": "gondor.test"
    }
    return f"{name}@{domains[race]}"
```

## Usage Examples

### ✅ Appropriate Usage

```python
# Test users and authentication
TEST_USERS = [
    {"username": "frodo_baggins", "email": "frodo@shire.test"},
    {"username": "gandalf_grey", "email": "gandalf@rivendell.test"}
]

# Environment names
ENVIRONMENTS = ["hobbiton-dev", "rivendell-staging", "gondor-prod"]

# Mock API responses
MOCK_RESPONSE = {
    "user": {"name": "Samwise Gamgee", "location": "Hobbiton"},
    "status": "success"
}

# Database test data
INSERT_USERS = [
    ("Legolas", "legolas@mirkwood.test", "elf"),
    ("Gimli", "gimli@erebor.test", "dwarf")
]
```

### ❌ Inappropriate Usage

```python
# Don't use for function names
def gandalfProcessor():  # ❌ Use descriptive names instead
    pass

# Don't use in documentation
"""
This function works like Gandalf's magic...  # ❌ Avoid themed explanations
"""

# Don't use for production values
API_KEY = "one_ring_to_rule_them_all"  # ❌ Use proper secrets management
```

## Context-Specific Applications

### Database Testing

- **User IDs**: Sequential (1=Frodo, 2=Sam, 3=Merry, etc.)
- **Timestamps**: Use significant dates (3018 Third Age = Sept 23)
- **Foreign Keys**: Logical relationships (Sam → Frodo, Legolas → Thranduil)

### API Testing

- **Endpoints**: `/api/users/frodo_baggins`, `/api/locations/shire`
- **Payloads**: Consistent character attributes
- **Error Cases**: Use evil characters (Sauron, Saruman) for failure scenarios

### Performance Testing

- **Load Testing**: Use army sizes (10,000 orcs, 6,000 Rohirrim)
- **Stress Testing**: Use epic battle scenarios
- **Volume Testing**: Population of Middle-earth locations
