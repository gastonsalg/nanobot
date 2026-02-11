import asyncio

import pytest

from nanobot.agent.tools.shell import ExecTool


def test_restricted_mode_blocks_shell_operator_semicolon(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("cat;/etc/passwd", str(tmp_path))

    assert err is not None
    assert "shell operators are not allowed" in err


def test_restricted_mode_blocks_command_substitution(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command('cat "$(echo /etc/passwd)"', str(tmp_path))

    assert err is not None
    assert "shell expansion is not allowed" in err


def test_restricted_mode_blocks_tilde_expansion(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("cat ~/.ssh/id_rsa", str(tmp_path))

    assert err is not None
    assert "shell expansion is not allowed" in err


def test_restricted_mode_blocks_dollar_expansion(tmp_path, monkeypatch) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    err = tool._guard_command("cat $HOME/.ssh/id_rsa", str(tmp_path))

    assert err is not None
    assert "shell expansion is not allowed" in err


def test_restricted_mode_blocks_braced_dollar_expansion(tmp_path, monkeypatch) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    err = tool._guard_command("cat ${HOME}/.ssh/id_rsa", str(tmp_path))

    assert err is not None
    assert "shell expansion is not allowed" in err


def test_restricted_mode_blocks_parameter_expansion(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("cat ${UNSET:-/etc}/passwd", str(tmp_path))

    assert err is not None
    assert "shell expansion is not allowed" in err


def test_restricted_mode_blocks_env_assignment_prefix(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("HOME=/etc ls $HOME", str(tmp_path))

    assert err is not None
    assert "environment assignments are not allowed" in err


def test_restricted_mode_blocks_non_allowlisted_command(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("uname -a", str(tmp_path))

    assert err is not None
    assert "command not allowlisted" in err


def test_restricted_mode_blocks_executable_path(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("/bin/ls", str(tmp_path))

    assert err is not None
    assert "allowlisted executable name" in err


def test_restricted_mode_blocks_relative_path_escape(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("cat ../secret.txt", str(tmp_path))

    assert err is not None
    assert "path outside allowed working directory" in err


def test_restricted_mode_blocks_absolute_path_escape(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("cat /etc/passwd", str(tmp_path))

    assert err is not None
    assert "path outside allowed working directory" in err


def test_restricted_mode_blocks_symlink_escape(tmp_path) -> None:
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("secret")
    linked = tmp_path / "linked-secret.txt"
    try:
        linked.symlink_to(outside)
    except OSError:
        pytest.skip("Symlinks not supported in this environment")

    tool = ExecTool(restrict_to_workspace=True)
    err = tool._guard_command("cat linked-secret.txt", str(tmp_path))

    assert err is not None
    assert "path outside allowed working directory" in err


def test_restricted_mode_allows_simple_allowlisted_command(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("ls .", str(tmp_path))

    assert err is None


def test_restricted_mode_allows_find_without_exec(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("find . -maxdepth 1", str(tmp_path))

    assert err is None


def test_restricted_mode_blocks_find_exec_predicate(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command(
        'find . -maxdepth 0 -exec sh -c "cat /etc/passwd" sh {} +',
        str(tmp_path),
    )

    assert err is not None
    assert "find argument '-exec' is not allowed" in err


def test_restricted_mode_allows_allowlisted_subcommand(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("git -C . status", str(tmp_path))

    assert err is None


def test_restricted_mode_blocks_non_allowlisted_subcommand(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("git config --global user.name test", str(tmp_path))

    assert err is not None
    assert "command not allowlisted" in err


def test_restricted_mode_blocks_working_dir_outside_workspace(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path.parent
    tool = ExecTool(restrict_to_workspace=True, working_dir=str(workspace))

    result = asyncio.run(tool.execute("pwd", working_dir=str(outside)))

    assert "working directory outside allowed workspace" in result


def test_restricted_mode_executes_structured_command(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True, working_dir=str(tmp_path))

    result = asyncio.run(tool.execute("echo hello"))

    assert "hello" in result
