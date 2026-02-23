"""Directory walker that respects .gitignore and collects code files."""

import os
from pathlib import Path
from typing import Iterator
import pathspec


# Common code file extensions
DEFAULT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".kt", ".scala",
    ".c", ".cpp", ".h", ".hpp", ".cc",
    ".go", ".rs", ".rb", ".php",
    ".swift", ".m", ".mm",
    ".cs", ".fs",
    ".html", ".css", ".scss", ".less",
    ".json", ".yaml", ".yml", ".toml",
    ".md", ".txt",
    ".sh", ".bash", ".zsh",
    ".sql", ".graphql",
    ".vue", ".svelte",
}

# Directories to always skip
SKIP_DIRS = {
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__", ".pytest_cache",
    "venv", ".venv", "env", ".env",
    "dist", "build", "target", "out",
    ".idea", ".vscode",
    "vendor", "bower_components",
}


def load_gitignore(root: Path) -> pathspec.PathSpec | None:
    """Load .gitignore patterns from the root directory."""
    gitignore_path = root / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            patterns = f.read().splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    return None


def walk_codebase(
    root: str,
    extensions: set[str] | None = None,
    max_files: int = 100,
    max_lines: int = 200,
) -> Iterator[dict]:
    """
    Walk a codebase and yield file info dictionaries.

    Args:
        root: Root directory path
        extensions: Set of file extensions to include (with dots)
        max_files: Maximum number of files to process
        max_lines: Maximum lines to read per file

    Yields:
        Dict with keys: path, relative_path, directory, filename, content, loc, extension
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ValueError(f"Not a directory: {root}")

    extensions = extensions or DEFAULT_EXTENSIONS
    gitignore = load_gitignore(root_path)

    file_count = 0

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter out skip directories in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        current_dir = Path(dirpath)
        rel_dir = current_dir.relative_to(root_path)

        # Check gitignore for directories
        if gitignore:
            dirnames[:] = [
                d for d in dirnames
                if not gitignore.match_file(str(rel_dir / d) + "/")
            ]

        for filename in sorted(filenames):
            if file_count >= max_files:
                return

            filepath = current_dir / filename
            rel_path = filepath.relative_to(root_path)

            # Check extension
            ext = filepath.suffix.lower()
            if ext not in extensions:
                continue

            # Check gitignore
            if gitignore and gitignore.match_file(str(rel_path)):
                continue

            # Read file content
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except (IOError, OSError):
                continue

            # Truncate to max lines
            if len(lines) > max_lines:
                lines = lines[:max_lines]
                lines.append(f"\n... ({len(lines)} more lines truncated)")

            content = "".join(lines)

            yield {
                "path": str(filepath),
                "relative_path": str(rel_path),
                "directory": str(rel_path.parent) if rel_path.parent != Path(".") else "",
                "filename": filename,
                "content": content,
                "loc": len(lines),
                "extension": ext,
            }

            file_count += 1
