# Spell Schema Documentation

## Overview

Spells allow users to register external API tools and scripts that can be executed through the Gandalf MCP server. Spells are defined as YAML files in the `spells/` directory at the project root. Simply create a `{spell_name}.yaml` file and the spell will be automatically discovered and available without server restart.

## Schema Definition

### Spell Configuration

Each spell is a YAML file with the following structure:

```yaml
name: spell_name
description: Human-readable description of what the spell does
command: command to execute
flags:
  - flag1
  - flag2
paths:
  - /path1
  - /path2
timeout: 30
```

File Location: `spells/{spell_name}.yaml` (filename must match spell name)

### Required Fields

- name (string): Unique identifier for the spell. Must match the filename (without extension).
- description (string): Human-readable description of the spell's purpose.
- command (string): Base command to execute. Each spell handles one command with strict usage.

### Optional Fields

- flags (array of strings): List of permitted flags and arguments for the command. Empty array means no flags allowed. Each command requires its own handling for strict usage.
- paths (array of strings): List of permitted paths where the command can execute. Empty array means no paths allowed.
- timeout (integer): Execution timeout in seconds. Default: 30, Maximum: 300.

## Security Model

### Path Validation

Commands can only execute within paths specified in the `paths` array. Paths are resolved to absolute paths before comparison. If `paths` is empty, execution is not permitted in any path.

### Flag Validation

Only flags specified in the `flags` array are permitted. Each command requires its own handling for strict usage validation. If `flags` is empty, no flags or arguments are allowed beyond the base command.

### Execution Environment

Spell arguments are passed as environment variables prefixed with `SPELL_ARG_`:

- Simple values: `SPELL_ARG_KEY=value`
- Complex values (objects/arrays): `SPELL_ARG_KEY={"json":"encoded"}`

## Usage Examples

### Example 1: Simple API Call

Create `spells/weather-api.yaml`:

```yaml
name: weather-api
description: Get weather data using curl
command: curl
flags:
  - -X
  - GET
  - -H
paths: []
timeout: 30
```

### Example 2: Script Execution

Create `spells/my-script.yaml`:

```yaml
name: my-script
description: Run custom script
command: bash
flags:
  - -c
paths:
  - /home/user/scripts
timeout: 60
```

### Example 3: Python Script

Create `spells/data-processor.yaml`:

```yaml
name: data-processor
description: Process data files with Python
command: python3
flags:
  - -u
paths:
  - /home/user/tools
timeout: 120
```

### Example 4: OS Command (pwd)

Create `spells/pwd.yaml`:

```yaml
name: pwd
description: Print working directory
command: pwd
flags: []
paths:
  - ${HOME}
timeout: 10
```

This example demonstrates a spell for the `pwd` command restricted to the home directory. Environment variables like `${HOME}` are automatically expanded. Each command requires its own spell definition for strict usage control.

## File Structure

Spells are stored as individual YAML files in the `spells/` directory:

```
project-root/
  spells/
    os-commands.yaml
    weather-api.yaml
    my-script.yaml
```

Each YAML file defines one spell. The filename (without extension) should match the spell name.

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

1. Security: Always specify `paths` and `flags` arrays to restrict spell execution. Each command requires its own spell definition for strict usage.
2. Timeouts: Set appropriate timeouts based on expected execution time.
3. Descriptions: Provide clear, descriptive spell descriptions.
4. One Command Per Spell: Each spell should handle only one command with strict flag and path validation.
5. Testing: Test spells manually before relying on them.

## Error Handling

The spell tool returns structured error messages:

- Spell not registered
- Invalid configuration
- Path or command not permitted
- Execution timeout
- Execution failure

All errors are logged and returned as ToolResult objects.
