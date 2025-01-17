# ai-git

An interactive command-line tool for AI-assisted code modifications using Git and Ollama.

## Features

### Core Functionality
- **AI-Driven Code Generation**: Leverages Ollama's codellama model for intelligent code modifications
- **Git Integration**: Seamless branch management, commit handling, and merging capabilities
- **Interactive REPL**: User-friendly command-line interface for managing changes
- **Session Management**: Persistent sessions with context tracking
- **Automatic Documentation**: Markdown-based change documentation with commit tracking

### Context Management
- Dynamic file context inclusion/exclusion
- Automatic structural file detection (package.json, requirements.txt, etc.)
- Customizable rules for context inclusion
- Context persistence across sessions

### Git Operations
- Branch creation and management
- Commit tracking and rollback capabilities
- Manual review process for changes
- Safe merge operations with conflict handling

### Documentation
- Automatic markdown generation for all changes
- Timestamp-based change tracking
- Links between prompts, changes, and commits
- Session-based history management

## Installation

### System Requirements
- Operating System: Linux, macOS, or Windows with WSL2
- Memory: Minimum 8GB RAM (16GB recommended for larger codebases)
- Storage: 10GB free space for model and temporary files
- CPU: 4 cores minimum (8 cores recommended)

### Prerequisites
- Python 3.8 or higher
- Git 2.25 or higher
- Ollama 0.1.14 or higher with codellama model installed
- Available port 11434 for Ollama API

### Dependencies
```bash
pip install gitpython requests click
```

### Ollama Setup
1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull the codellama model:
```bash
ollama pull codellama
```

## Usage

### Basic Operation
1. Start the tool:
```bash
python aigit.py /path/to/your/repository
```

2. Optional parameters:
```bash
python aigit.py /path/to/your/repository --ollama-host "http://localhost:11434" --debug
```

### REPL Commands

| Command | Description | Example |
|---------|-------------|---------|
| `new-branch <name>` | Create new feature branch | `new-branch feature/add-login` |
| `prompt <text>` | Submit prompt for code changes | `prompt "Add error handling to user.py"` |
| `review` | Review pending changes | `review` |
| `commit <msg>` | Commit current changes | `commit "Add error handling"` |
| `rollback` | Rollback last commit | `rollback` |
| `merge` | Merge current branch to main | `merge` |
| `add-context <file>` | Add file to context | `add-context src/utils.py` |
| `rm-context <file>` | Remove file from context | `rm-context src/errors.py` |
| `clear-context` | Clear current context | `clear-context` |
| `show-context` | Show current context files | `show-context` |
| `shell` | Open OS shell in repository | `shell` |
| `exit` \| `quit` | Exit REPL | `quit` |
| `help` | Show available commands | `help` |

### Workflow Example

1. Start a new feature branch:
```
ai-git> new-branch feature/error-handling
```

2. Add relevant files to context:
```
ai-git> add-context src/error_handler.py
ai-git> add-context src/utils.py
```

3. Submit a prompt for changes:
```
ai-git> prompt "Add try-except blocks around file operations in error_handler.py"
```

4. Review the generated changes:
```
ai-git> review
```

5. Commit approved changes:
```
ai-git> commit "Add error handling for file operations"
```

6. Merge to main after testing:
```
ai-git> merge
```

## Documentation

### Change Tracking
The tool automatically generates documentation in the `ai-tool-docs` directory:
- One markdown file per branch
- Timestamps for all changes
- Links between prompts and commits
- Detailed change summaries

Example documentation format:
```markdown
# AI-Assisted Changes: feature/error-handling

## Change History
| Timestamp | Prompt | Changes | Commit |
|-----------|---------|----------|--------|
| 2025-01-16 10:30:00 | Add error handling | error_handler.py | a1b2c3d |
```

### Session Management
- Sessions are persisted between runs
- Context is maintained across restarts
- Clear separation between different modification sessions

## Error Handling

### Git Operations
- Safe branch switching with dirty state detection
- Merge conflict detection and guidance
- Automatic rollback on failed operations

### API Communication
- Robust error handling for Ollama API calls
- Connection failure recovery
- Response validation

### File Operations
- Safe file writing with backup
- Directory creation as needed
- Cleanup of temporary files

## Configuration

### Structural Files
Default patterns for structural file detection:
- package.json
- requirements.txt
- go.mod
- Cargo.toml
- setup.py

### Custom Rules
Edit `.git/ai-tool-config.json` to customize:
```json
{
  "structural_patterns": [
    "package.json",
    "requirements.txt",
    "custom.config"
  ]
}
```

## Best Practices

### Code Changes
1. Start with small, focused changes
2. Review changes carefully before committing
3. Keep context files relevant to the current task
4. Use clear, descriptive commit messages
5. Test changes before merging to main

### Effective Prompting
1. Be specific about the desired changes:
   ```
   ✓ "Add error handling to file operations in utils.py using try-except blocks"
   ✗ "Make utils.py better"
   ```

2. Include context information:
   ```
   ✓ "Update the user authentication in auth.py to use the new UserManager class"
   ✗ "Change the authentication system"
   ```

3. Specify constraints:
   ```
   ✓ "Add logging to database.py using the existing logger from utils.py"
   ✗ "Add logging to database.py"
   ```

### Context Management
1. Include only relevant files in context
2. Clear context when switching tasks
3. Use structural files appropriately
4. Monitor context size for optimal performance

### Session Handling
1. One branch per feature/task
2. Clear documentation of changes
3. Regular commits for trackability
4. Clean merges to main

## Troubleshooting

### Common Issues and Solutions

1. Ollama Connection Errors
```
Error: Failed to connect to Ollama API
Solutions:
- Check if Ollama is running: `ps aux | grep ollama`
- Verify API endpoint: curl http://localhost:11434/api/generate
- Check for port conflicts: `netstat -tuln | grep 11434`
- Restart Ollama: `sudo systemctl restart ollama`
```

2. Git Conflicts
```
Error: Merge conflict detected
Solutions:
1. Review conflicts:
   git status
   git diff
2. Resolve each file:
   - Edit files to resolve markers
   - git add <resolved-file>
3. Complete merge:
   git commit -m "Resolve merge conflicts"
```

3. Context Issues
```
Error: Context too large
Solutions:
- Check context size: ai-git> show-context
- Remove unnecessary files: ai-git> clear-context
- Add only relevant files
- Split changes into smaller chunks
```

4. Permission Errors
```
Error: Permission denied
Solutions:
- Check file permissions: ls -la
- Fix ownership: sudo chown -R user:group .
- Fix modes: chmod -R u+w .
```

5. Model Issues
```
Error: Invalid response from Ollama
Solutions:
- Verify model installation: ollama list
- Reinstall model: ollama pull codellama
- Check model logs: ollama logs
```

### Recovery Procedures

1. Session Recovery
```bash
# If session becomes corrupted:
rm .git/ai-tool-session.pickle
python aigit.py /path/to/repo
```

2. Branch Recovery
```bash
# If branch state is corrupted:
git checkout main
git branch -D corrupted-branch
ai-git> new-branch feature/retry
```

3. Context Recovery
```bash
# If context is causing issues:
ai-git> clear-context
ai-git> show-context  # verify empty
ai-git> add-context file1.py  # add files one by one
```

### Debug Mode
Enable debug logging:
```bash
python aigit.py /path/to/repo --debug
```

## Security Considerations

### Repository Security
- Never include sensitive files in context (e.g., .env, credentials)
- Always review generated code for security implications
- Be cautious with generated code that:
  - Makes network connections
  - Handles user input
  - Deals with file operations
  - Manages authentication/authorization

### Data Protection
- Generated code is stored locally only
- No data is sent to external services except Ollama
- Session data is stored in .git directory
- Use .gitignore to prevent committing tool-specific files:
```
ai-tool-docs/
.git/ai-tool-session.pickle
.git/ai-tool-config.json
```

### Backup Recommendations
1. Create repository backup before using the tool
2. Regularly commit to backup branches
3. Use `--backup` flag to enable automatic backups:
```bash
python aigit.py /path/to/repo --backup
```

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Ollama team for the codellama model
- GitPython developers
- Click framework team
