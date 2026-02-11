from nanobot.agent.tools.shell import ExecTool


def test_workspace_guard_blocks_absolute_path_after_semicolon(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("cat;/etc/passwd", str(tmp_path))

    assert err is not None
    assert "path outside working dir" in err


def test_workspace_guard_keeps_relative_path_untouched(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command(".venv/bin/python -V", str(tmp_path))

    assert err is None


def test_workspace_guard_blocks_tilde_path_outside_workspace(tmp_path, monkeypatch) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    err = tool._guard_command("cat ~/.ssh/id_rsa", str(tmp_path))

    assert err is not None
    assert "path outside working dir" in err


def test_workspace_guard_blocks_home_var_path_outside_workspace(tmp_path, monkeypatch) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    err = tool._guard_command("cat $HOME/.ssh/id_rsa", str(tmp_path))

    assert err is not None
    assert "path outside working dir" in err


def test_workspace_guard_blocks_braced_home_var_path_outside_workspace(tmp_path, monkeypatch) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    err = tool._guard_command("cat ${HOME}/.ssh/id_rsa", str(tmp_path))

    assert err is not None
    assert "path outside working dir" in err


def test_workspace_guard_allows_expanded_var_path_inside_workspace(tmp_path, monkeypatch) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("NB_WORK", str(tmp_path))

    err = tool._guard_command("cat $NB_WORK/notes.txt", str(tmp_path))

    assert err is None


def test_workspace_guard_blocks_quoted_home_var_path_outside_workspace(tmp_path, monkeypatch) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    err = tool._guard_command('cat "$HOME/.ssh/id_rsa"', str(tmp_path))

    assert err is not None
    assert "path outside working dir" in err


def test_workspace_guard_blocks_quoted_braced_home_var_path_outside_workspace(
    tmp_path, monkeypatch
) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    err = tool._guard_command('cat "${HOME}/.ssh/id_rsa"', str(tmp_path))

    assert err is not None
    assert "path outside working dir" in err


def test_workspace_guard_blocks_command_substitution_in_restricted_mode(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command('cat "$(echo /etc/passwd)"', str(tmp_path))

    assert err is not None
    assert "command substitution not allowed" in err
