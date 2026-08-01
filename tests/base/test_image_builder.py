"""Tests for ImageBuilder: command assembly, exit codes, and missing tooling."""

from unittest.mock import MagicMock, patch

import pytest

from app.base.ImageBuilder import ImageBuilder, ImageBuildError


def _fake_proc(returncode=0, lines=()):
    """A stand-in for subprocess.Popen whose stdout drains then ends."""
    proc = MagicMock()
    proc.stdout.readline.side_effect = list(lines) + [""]
    proc.wait.return_value = None
    proc.returncode = returncode
    return proc


def test_build_invokes_tool_with_tag_context_and_dockerfile(tmp_path):
    with patch("app.base.ImageBuilder.subprocess.Popen", return_value=_fake_proc(0)) as popen:
        rc = ImageBuilder().build(context_dir=tmp_path, tag="demo-backend:abc123")

    assert rc == 0
    assert popen.call_args.args[0] == [
        "docker", "build",
        "-t", "demo-backend:abc123",
        "-f", str(tmp_path / "Dockerfile"),
        str(tmp_path),
    ]


def test_build_returns_the_tools_nonzero_exit_code(tmp_path):
    with patch("app.base.ImageBuilder.subprocess.Popen", return_value=_fake_proc(7)):
        assert ImageBuilder().build(context_dir=tmp_path, tag="t") == 7


def test_build_uses_the_configured_tool(tmp_path):
    with patch("app.base.ImageBuilder.subprocess.Popen", return_value=_fake_proc(0)) as popen:
        ImageBuilder(tool="podman").build(context_dir=tmp_path, tag="t")

    assert popen.call_args.args[0][0] == "podman"


def test_build_raises_when_the_tool_is_not_installed(tmp_path):
    with patch("app.base.ImageBuilder.subprocess.Popen", side_effect=FileNotFoundError):
        with pytest.raises(ImageBuildError):
            ImageBuilder(tool="nope").build(context_dir=tmp_path, tag="t")
