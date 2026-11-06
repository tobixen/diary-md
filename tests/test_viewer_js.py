"""Run the viewer's JavaScript tests with node, when node is installed."""

import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which('node')


@pytest.mark.skipif(NODE is None, reason='node is not installed')
def test_viewer_escaping():
    script = Path(__file__).parent / 'js' / 'viewer_escape.test.js'
    result = subprocess.run([NODE, str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
