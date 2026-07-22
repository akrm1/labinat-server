"""Tests for PipelineExecuter: optional empty pipelines and action execution."""

from unittest.mock import patch

from base.PipelineExecuter import PipelineExecuter


def test_empty_actions_is_noop_and_does_not_call_shell():
    with patch("utils.os.execute") as execute:
        PipelineExecuter(name="backend.init", actions=[])()
        execute.assert_not_called()


def test_missing_name_or_cmd_actions_are_filtered_out():
    with patch("utils.os.execute") as execute:
        PipelineExecuter(
            name="backend.build",
            actions=[
                {"name": "ok", "cmd": "echo hi"},
                {"name": "no-cmd"},
                {"cmd": "echo orphan"},
            ],
        )()
        execute.assert_called_once()
        assert execute.call_args.args[0] == "echo hi"


def test_runs_actions_in_order_and_stops_on_failure():
    calls = []

    def fake_execute(cmd, inputs=None, cwd=None):
        calls.append(cmd)
        return 1 if cmd == "fail" else 0

    with patch("utils.os.execute", side_effect=fake_execute):
        PipelineExecuter(
            name="backend.build",
            actions=[
                {"name": "one", "cmd": "ok"},
                {"name": "two", "cmd": "fail"},
                {"name": "three", "cmd": "never"},
            ],
        )()

    assert calls == ["ok", "fail"]


def test_passes_cwd_and_jinja_context_to_execute():
    with patch("utils.os.execute", return_value=0) as execute:
        PipelineExecuter(
            name="backend.run",
            actions=[{"name": "serve", "cmd": "uvicorn {{ app.name }}:app"}],
        )(cwd="/tmp/src", app={"name": "Demo"})

        execute.assert_called_once_with(
            "uvicorn {{ app.name }}:app",
            {"app": {"name": "Demo"}},
            cwd="/tmp/src",
        )
