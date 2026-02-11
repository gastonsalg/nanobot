"""Shell execution tool."""

import asyncio
import os
import re
import shlex
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool

DEFAULT_RESTRICTED_COMMAND_SPECS = [
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "grep",
    "rg",
    "find",
    "pwd",
    "echo",
    "stat",
    "git:status",
    "git:diff",
    "git:log",
    "git:show",
    "git:rev-parse",
    "git:branch",
    "git:ls-files",
    "pytest",
]

FORBIDDEN_SHELL_OPERATOR_TOKENS = {
    ";",
    "&&",
    "||",
    "|",
    "&",
    ">",
    ">>",
    "<",
    "<<",
    "(",
    ")",
    "{",
    "}",
}

RESTRICTED_COMMAND_BLOCKED_ARG_TOKENS: dict[str, set[str]] = {
    "find": {"-exec", "-execdir", "-ok", "-okdir", "-delete"},
}


class ExecTool(Tool):
    """Tool to execute shell commands."""

    def __init__(
        self,
        timeout: int = 60,
        working_dir: str | None = None,
        deny_patterns: list[str] | None = None,
        allow_patterns: list[str] | None = None,
        restrict_to_workspace: bool = False,
        allowed_commands: list[str] | None = None,
    ):
        self.timeout = timeout
        self.working_dir = working_dir
        self.deny_patterns = deny_patterns or [
            r"\brm\s+-[rf]{1,2}\b",  # rm -r, rm -rf, rm -fr
            r"\bdel\s+/[fq]\b",  # del /f, del /q
            r"\brmdir\s+/s\b",  # rmdir /s
            r"\b(format|mkfs|diskpart)\b",  # disk operations
            r"\bdd\s+if=",  # dd
            r">\s*/dev/sd",  # write to disk
            r"\b(shutdown|reboot|poweroff)\b",  # system power
            r":\(\)\s*\{.*\};\s*:",  # fork bomb
        ]
        self.allow_patterns = allow_patterns or []
        self.restrict_to_workspace = restrict_to_workspace
        self.allowed_commands = self._parse_allowed_commands(
            allowed_commands or DEFAULT_RESTRICTED_COMMAND_SPECS
        )

    @property
    def name(self) -> str:
        return "exec"

    @property
    def description(self) -> str:
        return "Execute a shell command and return its output. Use with caution."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Optional working directory for the command",
                },
            },
            "required": ["command"],
        }

    async def execute(self, command: str, working_dir: str | None = None, **kwargs: Any) -> str:
        cwd = working_dir or self.working_dir or os.getcwd()
        cwd_path, cwd_error = self._resolve_execution_cwd(cwd)
        if cwd_error:
            return cwd_error

        guard_error = self._guard_command(command, str(cwd_path))
        if guard_error:
            return guard_error

        try:
            if self.restrict_to_workspace:
                argv, parse_error = self._parse_restricted_argv(command, cwd_path)
                if parse_error:
                    return parse_error
                process = await asyncio.create_subprocess_exec(
                    *argv,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(cwd_path),
                )
            else:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(cwd_path),
                )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return f"Error: Command timed out after {self.timeout} seconds"

            output_parts = []

            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))

            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                if stderr_text.strip():
                    output_parts.append(f"STDERR:\n{stderr_text}")

            if process.returncode != 0:
                output_parts.append(f"\nExit code: {process.returncode}")

            result = "\n".join(output_parts) if output_parts else "(no output)"

            # Truncate very long output
            max_len = 10000
            if len(result) > max_len:
                result = result[:max_len] + f"\n... (truncated, {len(result) - max_len} more chars)"

            return result

        except Exception as e:
            return f"Error executing command: {str(e)}"

    def _guard_command(self, command: str, cwd: str) -> str | None:
        """Safety guard for potentially destructive commands."""
        cmd = command.strip()
        lower = cmd.lower()

        for pattern in self.deny_patterns:
            if re.search(pattern, lower):
                return "Error: Command blocked by safety guard (dangerous pattern detected)"

        if self.allow_patterns:
            if not any(re.search(p, lower) for p in self.allow_patterns):
                return "Error: Command blocked by safety guard (not in allowlist)"

        if self.restrict_to_workspace:
            try:
                cwd_path = Path(cwd).expanduser().resolve()
            except Exception:
                return "Error: Command blocked in restricted mode (invalid working directory)"
            _, parse_error = self._parse_restricted_argv(cmd, cwd_path)
            if parse_error:
                return parse_error

        return None

    def _resolve_execution_cwd(self, cwd: str) -> tuple[Path, str | None]:
        """Resolve execution cwd and enforce workspace boundary in restricted mode."""
        try:
            cwd_path = Path(cwd).expanduser().resolve()
        except Exception:
            return Path(cwd), "Error: Command blocked in restricted mode (invalid working directory)"

        if not self.restrict_to_workspace:
            return cwd_path, None

        root = Path(self.working_dir or os.getcwd()).expanduser().resolve()
        if not self._is_path_within(cwd_path, root):
            return cwd_path, (
                "Error: Command blocked in restricted mode "
                "(working directory outside allowed workspace)"
            )
        return cwd_path, None

    def _parse_restricted_argv(
        self,
        command: str,
        cwd_path: Path,
    ) -> tuple[list[str], str | None]:
        """Parse and validate argv for restricted mode (no shell evaluation)."""
        cmd = command.strip()
        if not cmd:
            return [], "Error: Command blocked in restricted mode (empty command)"

        if "\x00" in cmd or "\n" in cmd or "\r" in cmd:
            return [], "Error: Command blocked in restricted mode (invalid control characters)"

        try:
            tokens = self._tokenize_command(cmd)
        except ValueError:
            return [], "Error: Command blocked in restricted mode (unable to parse command)"

        if not tokens:
            return [], "Error: Command blocked in restricted mode (empty command)"

        if any(token in FORBIDDEN_SHELL_OPERATOR_TOKENS for token in tokens):
            return [], "Error: Command blocked in restricted mode (shell operators are not allowed)"

        for token in tokens:
            if token.startswith("$") or token.startswith("~") or "$(" in token or "${" in token or "`" in token:
                return [], "Error: Command blocked in restricted mode (shell expansion is not allowed)"
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=.*$", token):
                return [], "Error: Command blocked in restricted mode (environment assignments are not allowed)"

        command_name = tokens[0]
        if "/" in command_name or "\\" in command_name:
            return [], (
                "Error: Command blocked in restricted mode "
                "(command must be an allowlisted executable name)"
            )
        if not self._is_command_allowlisted(tokens):
            return [], "Error: Command blocked in restricted mode (command not allowlisted)"
        arg_error = self._validate_restricted_command_args(command_name, tokens[1:])
        if arg_error:
            return [], arg_error

        for token in tokens[1:]:
            for candidate in self._extract_path_candidates(token):
                if not self._should_validate_path(candidate, cwd_path):
                    continue
                err = self._validate_path_candidate(candidate, cwd_path)
                if err:
                    return [], err

        return tokens, None

    def _tokenize_command(self, command: str) -> list[str]:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)

    def _parse_allowed_commands(self, specs: list[str]) -> dict[str, set[str] | None]:
        parsed: dict[str, set[str] | None] = {}
        for spec in specs:
            normalized = spec.strip().lower()
            if not normalized:
                continue
            if ":" not in normalized:
                parsed[normalized] = None
                continue

            command, subcommand = normalized.split(":", 1)
            command = command.strip()
            subcommand = subcommand.strip()
            if not command or not subcommand:
                continue

            existing = parsed.get(command)
            if existing is None and command in parsed:
                continue
            if existing is None:
                parsed[command] = {subcommand}
            else:
                existing.add(subcommand)
        return parsed

    def _is_command_allowlisted(self, argv: list[str]) -> bool:
        command = argv[0].lower()
        allowed = self.allowed_commands.get(command)
        if allowed is None:
            return command in self.allowed_commands
        subcommand = self._extract_subcommand(command, argv[1:])
        return bool(subcommand and subcommand.lower() in allowed)

    def _extract_subcommand(self, command: str, args: list[str]) -> str | None:
        if command == "git":
            i = 0
            while i < len(args):
                token = args[i]
                if token in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}:
                    i += 2
                    continue
                if token.startswith("--git-dir=") or token.startswith("--work-tree=") or token.startswith("--namespace="):
                    i += 1
                    continue
                if token.startswith("-"):
                    i += 1
                    continue
                return token
            return None

        for token in args:
            if token.startswith("-"):
                continue
            return token
        return None

    def _validate_restricted_command_args(self, command: str, args: list[str]) -> str | None:
        blocked_args = RESTRICTED_COMMAND_BLOCKED_ARG_TOKENS.get(command.lower())
        if not blocked_args:
            return None
        for token in args:
            if token.lower() in blocked_args:
                return (
                    "Error: Command blocked in restricted mode "
                    f"({command} argument '{token}' is not allowed)"
                )
        return None

    def _extract_path_candidates(self, token: str) -> list[str]:
        if token.startswith("--") and "=" in token:
            _, value = token.split("=", 1)
            return [value] if value else []
        return [token]

    def _looks_like_path(self, value: str) -> bool:
        return (
            value.startswith(("/", ".", "~"))
            or "/" in value
            or "\\" in value
        )

    def _should_validate_path(self, value: str, cwd_path: Path) -> bool:
        if self._looks_like_path(value):
            return True
        if value.startswith("-"):
            return False
        return (cwd_path / value).exists()

    def _validate_path_candidate(self, raw: str, cwd_path: Path) -> str | None:
        value = raw.strip()
        if not value:
            return None
        if value.startswith("~") or value.startswith("$"):
            return "Error: Command blocked in restricted mode (shell expansion is not allowed)"
        if "\x00" in value:
            return "Error: Command blocked in restricted mode (invalid path token)"

        path_value = Path(value) if Path(value).is_absolute() else (cwd_path / value)
        try:
            resolved = path_value.resolve()
        except Exception:
            return "Error: Command blocked in restricted mode (invalid path token)"

        if not self._is_path_within(resolved, cwd_path):
            return "Error: Command blocked in restricted mode (path outside allowed working directory)"
        return None

    def _is_path_within(self, target: Path, root: Path) -> bool:
        return target == root or root in target.parents
