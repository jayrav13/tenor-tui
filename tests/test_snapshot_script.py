import subprocess
import sys


def test_snapshot_script_list_exits_zero():
    """The snapshot script should accept --list and exit 0."""
    result = subprocess.run(
        [sys.executable, "bin/snapshot", "--list"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "hero" in result.stdout
