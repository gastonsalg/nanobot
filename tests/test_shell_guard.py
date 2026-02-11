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
