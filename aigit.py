#!/usr/bin/env python3

"""
AI-Driven Git Tool - A Python-based tool for managing AI-driven git changes.
Graham Greenfield, 2025
https://github.com/grahamg/ai-git
"""

import os
import subprocess
import sys
import json
import logging
import pickle
from requests.exceptions import RequestException, HTTPError
import tempfile
import shutil
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from pathlib import Path
from datetime import datetime
import requests
import git
from git import Repo
import click

@dataclass
class Session:
    """Represents a modification session"""
    branch: str
    context_files: Set[str]
    changes_history: List[Dict]
    created_at: str

    def to_dict(self) -> Dict:
        return {
            'branch': self.branch,
            'context_files': list(self.context_files),
            'changes_history': self.changes_history,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Session':
        return cls(
            branch=data['branch'],
            context_files=set(data['context_files']),
            changes_history=data['changes_history'],
            created_at=data['created_at']
        )

class GitToolConfig:
    """Configuration management for the tool"""
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.config_path = repo_path / '.git' / 'ai-tool-config.json'
        self.structural_patterns = self._load_config().get('structural_patterns', [
            "package.json",
            "requirements.txt",
            "go.mod",
            "Cargo.toml",
            "setup.py"
        ])

    def _load_config(self) -> Dict:
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)
        return {}

    def save_config(self):
        config = {'structural_patterns': self.structural_patterns}
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def update_structural_patterns(self, patterns: List[str]):
        self.structural_patterns = patterns
        self.save_config()

class AIGitTool:
    def __init__(self, repo_path: str, ollama_host: str = "http://localhost:11434"):
        self.repo_path = Path(repo_path)
        self.ollama_host = ollama_host
        self.repo = Repo(self.repo_path)
        self.docs_dir = self.repo_path / "ai-tool-docs"
        self.docs_dir.mkdir(exist_ok=True)
        self.session_file = self.repo_path / '.git' / 'ai-tool-session.pickle'
        self.config = GitToolConfig(self.repo_path)

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("ai-git-tool")

        self.session = self._load_session()

    def _load_session(self) -> Optional[Session]:
        """Load existing session if available"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load session: {e}")
        return None

    def _save_session(self):
        """Save current session"""
        if self.session:
            with open(self.session_file, 'wb') as f:
                pickle.dump(self.session, f)

    def clear_session(self):
        """Clear the current session and cleanup temporary files"""
        if self.session_file.exists():
            self.session_file.unlink()

        # Cleanup any temporary files
        temp_dir = Path(tempfile.gettempdir()) / "aigit"
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.session = None

    def create_branch(self, branch_name: str) -> bool:
        """Create and switch to a new branch"""
        try:
            if branch_name in self.repo.heads:
                self.logger.error(f"Branch {branch_name} already exists")
                return False

            current = self.repo.active_branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()

            # Initialize new session
            self.session = Session(
                branch=branch_name,
                context_files=set(),
                changes_history=[],
                created_at=str(datetime.now())
            )
            self._save_session()
            self._init_documentation(branch_name)
            return True

        except Exception as e:
            self.logger.error(f"Failed to create branch: {e}")
            return False

    def _init_documentation(self, branch_name: str):
        """Initialize documentation for new branch"""
        doc_path = self.docs_dir / f"{branch_name}.md"
        with open(doc_path, 'w') as f:
            f.write(f"# AI-Assisted Changes: {branch_name}\n\n")
            f.write("## Change History\n\n")
            f.write("| Timestamp | Prompt | Changes | Commit |\n")
            f.write("|-----------|---------|----------|--------|\n")

    def update_documentation(self, prompt: str, changes: Dict[str, str], commit_hash: str):
        """Update documentation with new changes"""
        if not self.session:
            self.logger.warning("No active session, skipping documentation update")
            return

        try:
            doc_path = self.docs_dir / f"{self.session.branch}.md"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Create a more detailed change summary
            changes_summary = []
            for file_path in changes.keys():
                summary = f"{file_path} (modified)"
                changes_summary.append(summary)

            changes_text = "\n".join(changes_summary)

            with open(doc_path, 'a') as f:
                f.write(f"| {timestamp} | {prompt} | {changes_text} | {commit_hash} |\n")

            # Update session history
            self.session.changes_history.append({
                'timestamp': timestamp,
                'prompt': prompt,
                'changes': changes_summary,
                'commit': commit_hash
            })
            self._save_session()

        except Exception as e:
            self.logger.error(f"Failed to update documentation: {e}")
            # Don't raise the error - documentation failure shouldn't break the workflow

    def get_structural_files(self) -> Dict[str, str]:
        """Get content of structural project files"""
        files_content = {}
        for pattern in self.config.structural_patterns:
            for path in self.repo_path.rglob(pattern):
                if path.is_file():
                    with open(path) as f:
                        files_content[str(path.relative_to(self.repo_path))] = f.read()
        return files_content

    def make_ollama_request(self, prompt: str) -> dict:
        """Make request to Ollama API with current context"""
        if not self.session:
            raise ValueError("No active session")

        try:
            context = self._build_context()
        except Exception as e:
            raise ValueError(f"Failed to build context: {str(e)}")

        structured_prompt = f"""
Based on the following context and request, provide code changes in a structured format.
Each change should be in the format:
FILE: <filepath>
```
<entire file content with changes>
```

Context files:
{context}

User request: {prompt}

Respond only with the file changes, using the format specified above.
"""

        payload = {
            "model": "llama3",
            "prompt": structured_prompt,
            "stream": False,
            "temperature": 0.7
        }

        try:
            response = requests.post(f"{self.ollama_host}/api/generate", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Ollama API request failed: {e}")
            raise

    def _build_context(self) -> str:
        """Build context string from current session files"""
        context_parts = []

        # Add structural files
        structural_files = self.get_structural_files()
        for file_path, content in structural_files.items():
            context_parts.append(f"File: {file_path}\n{content}\n")

        # Add session context files
        for file_path in self.session.context_files:
            full_path = self.repo_path / file_path
            if full_path.exists():
                with open(full_path) as f:
                    context_parts.append(f"File: {file_path}\n{f.read()}\n")

        return "\n".join(context_parts)

    def apply_changes(self, changes: Dict[str, str]) -> bool:
        """Apply proposed changes to files"""
        try:
            for file_path, content in changes.items():
                full_path = self.repo_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)
            return True
        except Exception as e:
            self.logger.error(f"Failed to apply changes: {e}")
            return False

    def commit_changes(self, message: str) -> Optional[str]:
        """Commit current changes"""
        try:
            self.repo.index.add('*')
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except Exception as e:
            self.logger.error(f"Failed to commit changes: {e}")
            return None

    def rollback(self) -> bool:
        """Rollback last commit"""
        try:
            self.repo.git.reset('--hard', 'HEAD^')
            return True
        except Exception as e:
            self.logger.error(f"Failed to rollback: {e}")
            return False

    def merge_to_main(self) -> bool:
        """Merge current branch to main after review"""
        try:
            # Check if main branch exists
            if 'main' not in self.repo.heads:
                self.logger.error("Main branch does not exist")
                return False

            # Store current branch for recovery
            current = self.repo.active_branch
            main = self.repo.heads.main

            # Check for uncommitted changes
            if self.repo.is_dirty():
                self.logger.error("Working directory is not clean. Commit or stash changes first.")
                return False

            try:
                main.checkout()
                self.repo.git.merge(self.session.branch)
                return True
            except git.GitCommandError as e:
                if "CONFLICT" in str(e):
                    self.logger.error("Merge conflict detected. Please resolve conflicts manually.")
                    # Provide guidance
                    print("To resolve conflicts:")
                    print("1. Check status with 'git status'")
                    print("2. Resolve conflicts in the marked files")
                    print("3. Add resolved files with 'git add'")
                    print("4. Complete merge with 'git commit'")
                else:
                    self.logger.error(f"Merge failed: {e}")
                self.repo.git.merge('--abort')
                current.checkout()
                return False

        except Exception as e:
            self.logger.error(f"Failed to merge to main: {e}")
            self.repo.git.merge('--abort')
            return False

class AIGitREPL:
    """Interactive REPL for AI-driven git operations"""
    def __init__(self, repo_path: str):
        self.tool = AIGitTool(repo_path)

    def start(self):
        """Start the REPL interface"""
        print("Welcome to AI Git Tool")
        self.show_help()

        while True:
            try:
                command = input("\nai-git> ").strip()
                if not command:
                    continue

                parts = command.split(maxsplit=1)
                cmd = parts[0]
                args = parts[1] if len(parts) > 1 else ""

                if cmd == "exit":
                    break
                elif cmd == "quit":
                    break
                elif cmd == "help":
                    self.show_help()
                elif cmd == "new-branch":
                    self.cmd_new_branch(args)
                elif cmd == "prompt":
                    self.cmd_prompt(args)
                elif cmd == "review":
                    self.cmd_review_changes()
                elif cmd == "commit":
                    self.cmd_commit(args)
                elif cmd == "rollback":
                    self.cmd_rollback()
                elif cmd == "merge":
                    self.cmd_merge()
                elif cmd == "add-context":
                    self.cmd_add_context(args)
                elif cmd == "rm-context":
                    self.cmd_rm_context(args)
                elif cmd == "clear-context":
                    self.cmd_clear_context()
                elif cmd == "show-context":
                    self.cmd_show_context()
                elif cmd == "shell":
                    self.cmd_shell()
                else:
                    print(f"Unknown command: {cmd}")

            except KeyboardInterrupt:
                print("\nUse 'exit' to exit")
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")

    def show_help(self):
        """Show available commands"""
        print("""
Commands:
  new-branch <name>  - Create new feature branch
  prompt <text>      - Submit prompt for code changes
  review             - Review pending changes
  commit <msg>       - Commit current changes
  rollback           - Rollback last commit
  merge              - Merge current branch to main
  add-context <file> - Add file to context
  rm-context <file>  - Remove file to context
  clear-context      - Clear current context
  show-context       - Show current context files
  shell              - Open OS shell in repository
  exit | quit        - Exit REPL
  help               - Show this message
        """.strip())

    def cmd_new_branch(self, args):
        """Handle branch creation"""
        if not args:
            print("Error: Branch name required")
            return
        if self.tool.create_branch(args):
            print(f"Created and switched to branch: {args}")
        else:
            print("Failed to create branch")

    def cmd_prompt(self, args):
        """Handle code generation prompt"""
        if not self.tool.session:
            print("Error: No active session. Use 'new-branch' first")
            return
        if not args:
            print("Error: Prompt required")
            return

        try:
            response = self.tool.make_ollama_request(args)
            parts = response['response'].split('FILE:', 1)
            if len(parts) > 1:
                explanation = parts[0].strip()
                if explanation:
                    print(f"\n{explanation}\n")

            changes = self._parse_ollama_response(response)
            if self.tool.apply_changes(changes):
                print("Changes applied. Use 'review' to inspect changes.")
        except Exception as e:
            print(f"Error processing prompt: {e}")

    def _parse_ollama_response(self, response: dict) -> Dict[str, str]:
        """Parse Ollama response into file changes"""
        if not response or 'response' not in response:
            raise ValueError("Invalid response from Ollama")

        content = response['response']
        changes = {}

        # Split into file sections
        sections = content.split('FILE: ')
        for section in sections[1:]:
            try:
                lines = section.split('\n', 1)
                filename = lines[0].strip()

                # Extract code block
                content_start = section.find('```') + 3
                content_end = section.rfind('```')

                if content_start > 2 and content_end > content_start:
                    file_content = section[content_start:content_end].strip()
                    changes[filename] = file_content

            except Exception as e:
                print(f"Warning: Failed to parse section: {e}")
                continue

        if not changes:
            raise ValueError("No valid changes found in response")

        return changes

    def cmd_review_changes(self):
        """Show pending changes for review"""
        if not self.tool.session:
            print("No active session")
            return

        try:
            diff = self.tool.repo.git.diff()
            if not diff:
                print("No changes to review")
                return

            print("\nPending changes:")
            print(diff)
            print("\nUse 'commit' to save changes or 'rollback' to discard")
        except Exception as e:
            print(f"Error showing changes: {e}")

    def cmd_commit(self, args):
        """Handle commit command"""
        if not self.tool.session:
            print("Error: No active session")
            return

        if not args:
            print("Error: Commit message required")
            return

        # Check if there are any changes to commit
        if not any(self.tool.repo.index.diff(None)) and not self.tool.repo.untracked_files:
            print("No changes to commit")
            return

        try:
            commit_hash = self.tool.commit_changes(args)
            if commit_hash:
                print(f"Changes committed: {commit_hash}")
                print("Use 'review' to verify the commit or 'rollback' to undo")
            else:
                print("Failed to commit changes")
        except Exception as e:
            print(f"Error during commit: {e}")

    def cmd_rollback(self):
        """Handle rollback command"""
        if self.tool.rollback():
            print("Last commit rolled back")
        else:
            print("Failed to rollback changes")

    def cmd_merge(self):
        """Handle merge to main command"""
        if not self.tool.session:
            print("No active session")
            return
            
        print("\nWARNING: This will merge current branch to main.")
        confirm = input("Are you sure? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("Merge cancelled")
            return
            
        if self.tool.merge_to_main():
            print(f"Branch {self.tool.session.branch} merged to main")
        else:
            print("Failed to merge to main")

    def cmd_add_context(self, args):
        """Add file to context"""
        if not self.tool.session:
            print("No active session")
            return

        if not args:
            print("Error: File path required")
            return

        file_path = Path(args)
        full_path = self.tool.repo_path / file_path

        if not full_path.exists():
            print(f"File not found: {args}")
            return

        self.tool.session.context_files.add(str(file_path))
        self.tool._save_session()
        print(f"Added to context: {args}")

    def cmd_rm_context(self, args):
        """Remove file from context"""
        if not self.tool.session:
            print("No active session")
            return

        if not args:
            print("Error: File path required")
            return

        if args in self.tool.session.context_files:
            self.tool.session.context_files.remove(args)
            self.tool._save_session()
            print(f"Removed from context: {args}")
        else:
            print("File is not in context")
            print("Use 'show-context' to see current context files")

    def cmd_clear_context(self):
        """Clear current context"""
        if not self.tool.session:
            print("No active session")
            return

        self.tool.session.context_files.clear()
        self.tool._save_session()
        print("Context cleared")

    def cmd_show_context(self):
        """Show current context files"""
        if not self.tool.session:
            print("No active session")
            return

        print("\nStructural files:")
        for pattern in self.tool.config.structural_patterns:
            print(f"  - {pattern}")

        print("\nContext files:")
        if self.tool.session.context_files:
            for file in sorted(self.tool.session.context_files):
                print(f"  - {file}")
        else:
            print("  (none)")

    def cmd_shell(self):
        """Open an OS shell in the repository directory"""
        if not self.tool.session:
            print("No active session")
            return

        print("\nEntering shell... (exit or Ctrl-D to return to ai-git)")
        print(f"Current branch: {self.tool.session.branch}")

        # Determine shell command based on OS
        shell = os.environ.get('SHELL', 'bash')
        if os.name == 'nt':
            shell = os.environ.get('COMSPEC', 'cmd.exe')

        try:
            subprocess.run([shell], cwd=str(self.tool.repo_path))
            print("\nReturning to ai-git...")
        except Exception as e:
            print(f"Error running shell: {e}")


def cleanup_handler(signum, frame):
    """Handle cleanup on signal"""
    print("\nCleaning up...")
    sys.exit(0)

@click.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.option('--ollama-host', default="http://localhost:11434", help="Ollama API host")
@click.option('--debug', is_flag=True, help="Enable debug logging")
def main(repo_path: str, ollama_host: str, debug: bool):
    """Start the AI-driven Git Tool for the specified repository"""
    try:
        # Set up signal handlers
        import signal
        signal.signal(signal.SIGINT, cleanup_handler)
        signal.signal(signal.SIGTERM, cleanup_handler)

        # Configure logging
        log_level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=log_level)

        # Initialize and start REPL
        repl = AIGitREPL(repo_path)
        print(f"Repository: {repo_path}")
        print(f"Ollama host: {ollama_host}")
        if debug:
            print("Debug mode enabled")
        repl.start()

    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=debug)
        sys.exit(1)
    finally:
        # Ensure cleanup
        if 'repl' in locals():
            repl.tool.clear_session()

if __name__ == '__main__':
    main()
