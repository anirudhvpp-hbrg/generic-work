"""Tests for the Monarch OS local runtime (offline)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monarchos import boot  # noqa: E402
from monarchos.cli import main  # noqa: E402


def test_boot_offline_runs_the_engine(tmp_path):
    rt = boot(state_path=str(tmp_path / "state.json"), offline=True)
    assert rt.online is False
    task = rt.run("tighten this proposal deck")
    assert task.shipped is True
    assert task.shadow_loadout                      # the fleet ran
    assert len(rt.kernel.memory) == 1               # persisted to kernel memory


def test_runtime_persists_across_boots(tmp_path):
    path = str(tmp_path / "state.json")
    boot(state_path=path, offline=True).run("research why retention dropped")
    # A fresh boot on the same state file rehydrates prior memory.
    rt2 = boot(state_path=path, offline=True)
    assert len(rt2.kernel.memory) == 1


def test_ephemeral_does_not_write_disk(tmp_path):
    rt = boot(offline=True, persist=False)
    assert rt.state_path is None
    rt.run("draft the summary")
    # nothing written under the default dir for this run path
    assert rt.kernel.storage.path is None


def test_status_reports_offline_and_fleet(tmp_path):
    rt = boot(state_path=str(tmp_path / "s.json"), offline=True)
    s = rt.status()
    assert s["model"].startswith("offline")
    assert "thresher" in s["shadows"]


def test_personal_routes_to_ira(tmp_path):
    rt = boot(state_path=str(tmp_path / "s.json"), offline=True)
    task = rt.run("I'm stuck on how to approach the launch", personal=True)
    assert "ira" in task.shadow_loadout


def test_cli_one_shot_offline(tmp_path, capsys):
    code = main(["--offline", "--ephemeral", "tighten this deck"])
    out = capsys.readouterr().out
    assert code == 0
    assert "SHIPPED" in out
    assert "loadout=" in out
