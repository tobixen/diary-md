"""Git operations for diary-md."""

import subprocess
from pathlib import Path


def find_git_root(filepath: Path) -> Path | None:
    """Find the git repository root for a file.

    Args:
        filepath: Path to a file or directory

    Returns:
        Path to git root, or None if not in a git repo
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=filepath if filepath.is_dir() else filepath.parent,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def git_commit(
    repo_dir: Path,
    files: list[Path | str],
    message: str,
    co_author: bool = True
) -> bool:
    """Commit changes to git.

    Args:
        repo_dir: Path to git repository root
        files: List of files to add and commit
        message: Commit message
        co_author: Whether to add AI co-author tag

    Returns:
        True if commit succeeded, False otherwise
    """
    try:
        # Convert to relative paths
        rel_files = []
        for f in files:
            f = Path(f)
            try:
                rel_files.append(str(f.relative_to(repo_dir)))
            except ValueError:
                rel_files.append(str(f))

        # Stage files
        result = subprocess.run(
            ['git', 'add'] + rel_files,
            cwd=repo_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Error adding files: {result.stderr}")
            return False

        # Check if there are changes to commit
        status = subprocess.run(
            ['git', 'diff', '--cached', '--quiet'],
            cwd=repo_dir
        )
        if status.returncode == 0:
            print("Nothing to commit (no changes)")
            return True

        # Build commit message
        if co_author:
            full_message = f"{message}\n\nCo-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
        else:
            full_message = message

        # Commit
        result = subprocess.run(
            ['git', 'commit', '-m', full_message],
            cwd=repo_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                print("Nothing to commit (no changes)")
                return True
            print(f"Error committing: {result.stderr}")
            return False

        print(f"Committed: {message}")
        return True

    except (subprocess.SubprocessError, OSError) as e:
        print(f"Git error: {e}")
        return False


def git_push(repo_dir: Path) -> bool:
    """Push changes to remote.

    Args:
        repo_dir: Path to git repository root

    Returns:
        True if push succeeded, False otherwise
    """
    try:
        result = subprocess.run(
            ['git', 'push'],
            cwd=repo_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"Error pushing: {result.stderr}")
            return False

        print("Pushed to remote")
        return True

    except (subprocess.SubprocessError, OSError) as e:
        print(f"Git error: {e}")
        return False


def git_commit_multiple_repos(
    modified_files: list[Path],
    message: str,
    co_author: bool = True
) -> dict[Path, bool]:
    """Commit changes to multiple git repositories.

    Groups files by their git repository root and commits each.

    Args:
        modified_files: List of modified file paths
        message: Commit message
        co_author: Whether to add AI co-author tag

    Returns:
        Dict mapping repo root to success status
    """
    # Group files by git repo
    repos: dict[Path, list[Path]] = {}
    for filepath in modified_files:
        filepath = Path(filepath)
        if not filepath.exists():
            continue

        repo_root = find_git_root(filepath)
        if repo_root:
            repos.setdefault(repo_root, []).append(filepath)

    # Commit each repo
    results = {}
    for repo_root, files in repos.items():
        results[repo_root] = git_commit(repo_root, files, message, co_author)

    return results
