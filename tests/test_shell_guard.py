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


def test_workspace_guard_blocks_default_value_parameter_expansion_path(
    tmp_path, monkeypatch
) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    err = tool._guard_command('cat "${HOME:-/tmp}/.ssh/id_rsa"', str(tmp_path))

    assert err is not None
    assert "unresolved path expansion" in err


def test_workspace_guard_blocks_unset_default_parameter_expansion_path(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("cat ${UNSET:-/etc}/passwd", str(tmp_path))

    assert err is not None
    assert "unresolved path expansion" in err


def test_workspace_guard_blocks_error_parameter_expansion_path(tmp_path, monkeypatch) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    err = tool._guard_command("cat ${HOME:?err}/.ssh/id_rsa", str(tmp_path))

    assert err is not None
    assert "unresolved path expansion" in err


def test_workspace_guard_allows_braced_var_path_inside_workspace(tmp_path, monkeypatch) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("NB_WORK", str(tmp_path))

    err = tool._guard_command("cat ${NB_WORK}/notes.txt", str(tmp_path))

    assert err is None


def test_workspace_guard_blocks_bare_home_var_token_outside_workspace(tmp_path, monkeypatch) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    err = tool._guard_command("ls $HOME", str(tmp_path))

    assert err is not None
    assert "path outside working dir" in err


def test_workspace_guard_blocks_bare_quoted_braced_home_var_token_outside_workspace(
    tmp_path, monkeypatch
) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    err = tool._guard_command('ls "${HOME}"', str(tmp_path))

    assert err is not None
    assert "path outside working dir" in err


def test_workspace_guard_blocks_cd_then_relative_access_outside_workspace(
    tmp_path, monkeypatch
) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    err = tool._guard_command("cd $HOME && cat .ssh/id_rsa", str(tmp_path))

    assert err is not None
    assert "path outside working dir" in err


def test_workspace_guard_allows_bare_var_token_inside_workspace(tmp_path, monkeypatch) -> None:
    tool = ExecTool(restrict_to_workspace=True)
    monkeypatch.setenv("NB_WORK", str(tmp_path))

    err = tool._guard_command("ls $NB_WORK", str(tmp_path))

    assert err is None


def test_workspace_guard_blocks_assignment_driven_pwd_override(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("PWD=/etc; cd $PWD && cat passwd", str(tmp_path))

    assert err is not None
    assert "env assignments not allowed" in err


def test_workspace_guard_blocks_env_assignment_prefix(tmp_path) -> None:
    tool = ExecTool(restrict_to_workspace=True)

    err = tool._guard_command("HOME=/etc ls $HOME", str(tmp_path))

    assert err is not None
    assert "env assignments not allowed" in err
