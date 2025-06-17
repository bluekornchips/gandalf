# Live Test Prompts for Conversations and Context Intelligence

This file contains test prompts you can send to verify that the conversation and context intelligence systems are working properly in a live environment. At the end of each test, grade and report the test input, expected behavior, actual behavior, time taken, and pass/fail status from an agent's perspective.

## 🗂️ Conversation System Tests

### Test 1: Basic Conversation Storage

**Prompt to send:**

```
Store this conversation with the title "Live Test Session" and tags "test,manual,verification". Make sure it creates the proper directory structure.
```

**Expected behavior:**

- Should create conversation in directory structure: `~/.gandalf/conversations/{conversation_id}/`
- Should contain `conversation.json` and `messages.json` files
- Should include project_name field
- Should respond with confirmation of storage

### Test 2: Conversation Listing

**Prompt to send:**

```
List all conversations for this project and show me the metadata structure.
```

**Expected behavior:**

- Should show conversations filtered by current project name
- Should display conversation IDs, titles, message counts, creation dates
- Should only show conversations for current project (not other projects)

### Test 3: Project-Specific Conversation Filtering

**Prompt to send:**

```
What project name am I currently in? Show me how conversations are organized by project.
```

**Expected behavior:**

- Should identify current project name from project root
- Should explain project-specific conversation storage
- Should show project_name field usage

### Test 4: Conversation Retrieval

**Prompt to send:**

```
Show me the details of the most recent conversation, including its full metadata and message structure.
```

**Expected behavior:**

- Should retrieve conversation from directory structure
- Should combine metadata from conversation.json and messages from messages.json
- Should display complete conversation data

## 🧠 Context Intelligence Tests

### Test 5: Generic Content Loading - Single File

**Prompt to send:**

```
Load context from a text file. Create a simple test file and show me how the generic content loader handles it.
```

**Expected behavior:**

- Should use `load_flat_context_data` function
- Should detect file type and format appropriately
- Should show context boundaries with "=== Loaded Context: ... ==="

### Test 6: Generic Content Loading - Directory

**Prompt to send:**

```
Load context from a directory containing multiple file types (JSON, text, logs). Show me how it handles different file types and truncation.
```

**Expected behavior:**

- Should recursively scan directory
- Should filter to loadable file types (.json, .txt, .log, .md)
- Should truncate at 5 files if more exist
- Should show file-specific handling for each type

### Test 7: Conversation Format Detection

**Prompt to send:**

```
Create a JSON file that looks like conversation data and load it with the generic content loader. Show me how it detects conversation format.
```

**Expected behavior:**

- Should detect JSON arrays with conversation-like structure
- Should identify when data contains 'messages' fields
- Should format conversation data appropriately
- Should show message counts and titles

### Test 8: History Data Loading

**Prompt to send:**

```
Load some context from the ~/.gandalf/history directory to show how old data can be side-loaded for context.
```

**Expected behavior:**

- Should successfully load data from history directory
- Should handle various file formats in backup
- Should provide useful context formatting
- Should not affect current conversation storage

## 🔧 MCP Server Integration Tests

### Test 9: MCP Tools Availability

**Prompt to send:**

```
What MCP tools do you have available for conversation and context management? List them and their capabilities.
```

**Expected behavior:**

- Should list conversation-related MCP tools
- Should include `store_conversation`, `list_conversations`, `get_conversation_context`
- Should mention project root parameter passing
- Should explain auto-store functionality

### Test 10: Project Context Gathering

**Prompt to send:**

```
Gather context about this project using your MCP tools. Show me project info, git status, and recent conversations.
```

**Expected behavior:**

- Should use `get_project_info` to get project metadata
- Should use `get_git_status` for repository state
- Should use `list_conversations` for recent conversation history
- Should combine information coherently

### Test 11: File System Operations

**Prompt to send:**

```
Show me the current project structure and search for any conversation-related files or directories.
```

**Expected behavior:**

- Should use `list_project_files` or similar tools
- Should identify conversation directories
- Should show proper file organization
- Should find conversation.json and messages.json files

## 📊 Advanced Integration Tests

### Test 12: Cross-Project Conversation Isolation

**Prompt to send:**

```
Explain how conversations are isolated between different projects and demonstrate the project_name filtering.
```

**Expected behavior:**

- Should explain project_name field usage
- Should show how conversations are filtered by project
- Should demonstrate isolation between projects
- Should explain directory structure benefits

### Test 13: Large Content Handling

**Prompt to send:**

```
Create and load a large JSON file to test content truncation and handling of oversized data.
```

**Expected behavior:**

- Should handle large files gracefully
- Should truncate content at appropriate limits (500 chars for JSON)
- Should indicate truncation with "..."
- Should not crash or hang

### Test 14: Error Handling

**Prompt to send:**

```
Test error handling by trying to load non-existent files and malformed JSON data.
```

**Expected behavior:**

- Should handle missing files gracefully
- Should return appropriate error messages
- Should handle malformed JSON without crashing
- Should provide useful debugging information

### Test 15: Unicode and Special Characters

**Prompt to send:**

```
Test Unicode handling by creating and loading files with special characters, emojis, and international text.
```

**Expected behavior:**

- Should handle UTF-8 encoding properly
- Should display special characters correctly
- Should not have encoding errors
- Should preserve character integrity

## 🚀 Performance and Reliability Tests

### Test 16: Conversation Directory Structure Performance

**Prompt to send:**

```
Create multiple conversations and verify the directory structure scales properly and doesn't have naming conflicts.
```

**Expected behavior:**

- Should create unique directories for each conversation
- Should handle concurrent conversation creation
- Should maintain proper metadata separation
- Should not have file conflicts

### Test 17: Memory and Resource Usage

**Prompt to send:**

```
Load a directory with many files and verify memory usage stays reasonable with truncation limits.
```

**Expected behavior:**

- Should respect file limits (5 files max)
- Should not load entire large files into memory
- Should use streaming/chunked reading where appropriate
- Should be responsive with large datasets

### Test 18: Backup and History Integration

**Prompt to send:**

```
Show me how the history/backup system works and verify old conversations are properly archived.
```

**Expected behavior:**

- Should show history directory structure
- Should explain backup retention
- Should demonstrate history loading capability
- Should show separation from active conversations

## 🔍 System Status Verification

### Test 19: Constants and Configuration

**Prompt to send:**

```
Show me the current configuration constants for conversations and verify they're being used properly.
```

**Expected behavior:**

- Should show `CONVERSATION_METADATA_FILE` and `CONVERSATION_MESSAGES_FILE` constants
- Should verify constants are used throughout the system
- Should show other relevant configuration values
- Should explain configuration flexibility

### Test 20: End-to-End Workflow

**Prompt to send:**

```
Perform a complete end-to-end test: store a conversation, list it, retrieve it, load some external context, and show everything working together.
```

**Expected behavior:**

- Should execute full workflow seamlessly
- Should demonstrate all systems working together
- Should show proper data flow between components
- Should confirm system integration

---

## 📝 Usage Instructions

1. **Send these prompts one at a time** to test specific functionality
2. **Verify expected behaviors** match the actual responses
3. **Check file system** manually for proper directory structures
4. **Monitor performance** during large data operations
5. **Report any deviations** from expected behavior

## 🎯 Success Criteria

- ✅ All conversation operations work with new directory structure
- ✅ Generic content loader handles all file types properly
- ✅ Project isolation works correctly
- ✅ MCP server integration is functional
- ✅ Error handling is graceful
- ✅ Performance stays within acceptable limits
- ✅ File system operations are correct
- ✅ Unicode and special characters work properly
