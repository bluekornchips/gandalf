# Spell Schema Documentation

## Overview

Spells allow users to register external API tools and scripts that can be executed through the Gandalf MCP server. Spells are stored in the registry.json file under the `spells` key.

## Schema Definition

### Spell Configuration

Each spell is a JSON object with the following structure:

```json
{
  "spells": {
    "spell_name": {
      "name": "spell_name",
      "description": "Human-readable description of what the spell does",
      "command": "command to execute",
      "path": "/optional/working/directory",
      "allowed_paths": ["/path1", "/path2"],
      "allowed_commands": ["curl", "python3"],
      "timeout": 30
    }
  }
}
```

### Required Fields

- **name** (string): Unique identifier for the spell. Must match the key in the spells object.
- **description** (string): Human-readable description of the spell's purpose.
- **command** (string): Command to execute. Can include arguments and flags.

### Optional Fields

- **path** (string): Working directory for command execution. If specified, must be in `allowed_paths`.
- **allowed_paths** (array of strings): List of permitted paths for the spell. If `path` is specified, it must be in this list. Empty by default (no paths allowed).
- **allowed_commands** (array of strings): List of permitted base commands. The command's base (first word) must match one of these. Empty by default (no commands allowed).
- **timeout** (integer): Execution timeout in seconds. Default: 30, Maximum: 300.

## Security Model

### Path Validation

If a spell specifies a `path`, it must be included in the `allowed_paths` list. Paths are resolved to absolute paths before comparison.

### Command Validation

If `allowed_commands` is specified, the base command (first word) must match one of the allowed commands.

### Execution Environment

Spell arguments are passed as environment variables prefixed with `SPELL_ARG_`:

- Simple values: `SPELL_ARG_KEY=value`
- Complex values (objects/arrays): `SPELL_ARG_KEY={"json":"encoded"}`

## Usage Examples

### Example 1: Simple API Call

```bash
cli/lib/spells.sh add weather-api "Get weather data" \
  "curl -X GET https://api.weather.com/v1/current" \
  --allowed-commands "curl"
```

### Example 2: Script Execution

```bash
cli/lib/spells.sh add my-script "Run custom script" \
  "./scripts/my-tool.sh" \
  --path "/home/user/scripts" \
  --allowed-paths "/home/user/scripts" \
  --allowed-commands "bash,sh" \
  --timeout 60
```

### Example 3: Python Script

```bash
cli/lib/spells.sh add data-processor "Process data files" \
  "python3 /home/user/tools/process.py" \
  --path "/home/user/tools" \
  --allowed-paths "/home/user/tools" \
  --allowed-commands "python3" \
  --timeout 120
```

## Registry File Structure

The registry.json file structure:

```json
{
  "cursor": [...],
  "claude": [...],
  "spells": {
    "spell_name": {
      "name": "spell_name",
      "description": "...",
      "command": "...",
      "path": "...",
      "allowed_paths": [...],
      "allowed_commands": [...],
      "timeout": 30
    }
  }
}
```

## CLI Commands

### Add Spell

```bash
cli/lib/spells.sh add <name> <description> <command> [options]
```

Options:

- `--path <path>`: Working directory
- `--allowed-paths <path1,path2,...>`: Comma-separated allowed paths
- `--allowed-commands <cmd1,cmd2,...>`: Comma-separated allowed commands
- `--timeout <seconds>`: Execution timeout

### Remove Spell

```bash
cli/lib/spells.sh remove <name>
```

### List Spells

```bash
cli/lib/spells.sh list
```

### Show Spell Details

```bash
cli/lib/spells.sh show <name>
```

### Validate Spell

```bash
cli/lib/spells.sh validate <name>
```

## MCP Tool Usage

Once registered, spells can be cast via the MCP `cast_spell` tool:

```json
{
  "method": "tools/call",
  "params": {
    "name": "cast_spell",
    "arguments": {
      "spell_name": "weather-api",
      "arguments": {
        "location": "New York",
        "units": "metric"
      }
    }
  }
}
```

Arguments are passed to the spell as environment variables:

- `SPELL_ARG_LOCATION=New York`
- `SPELL_ARG_UNITS=metric`

## Best Practices

1. **Security**: Always specify `allowed_paths` and `allowed_commands` to restrict spell execution.
2. **Timeouts**: Set appropriate timeouts based on expected execution time.
3. **Descriptions**: Provide clear, descriptive spell descriptions.
4. **Validation**: Use `validate` command before relying on a spell.
5. **Testing**: Test spells manually before registering them.

## Error Handling

The spell tool returns structured error messages:

- Spell not registered
- Invalid configuration
- Path/command not permitted
- Execution timeout
- Execution failure

All errors are logged and returned as ToolResult objects.
