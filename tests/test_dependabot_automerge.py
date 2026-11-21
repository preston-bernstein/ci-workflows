"""The reusable Dependabot auto-merge workflow: merges only when every other check on the PR's head commit passed.

The workflow's own shell step runs here against a fake `gh`, so the merge rule is tested by running it.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parent.parent / ".github/workflows/dependabot-automerge.yml"


@pytest.fixture(scope="module")
def doc():
    return yaml.safe_load(WORKFLOW.read_text())


def job(doc):
    return doc["jobs"]["automerge"]


def test_it_is_a_reusable_workflow_and_never_uses_pull_request_target(doc):
    triggers = doc[True]  # yaml reads the key `on` as True
    assert set(triggers) == {"workflow_call"}


def test_it_runs_only_for_dependabot_pull_requests(doc):
    assert job(doc)["if"] == "github.event.pull_request.user.login == 'dependabot[bot]'"


def test_permissions_are_the_least_that_can_merge(doc):
    assert doc["permissions"] == {}
    assert job(doc)["permissions"] == {"contents": "write", "pull-requests": "write", "checks": "read"}


def test_no_secret_is_used_and_no_third_party_action_runs(doc):
    text = WORKFLOW.read_text()
    assert "secrets." not in text and "inherit" not in text
    assert all("uses" not in step for step in job(doc)["steps"])


def test_the_job_name_ends_with_automerge_so_the_script_can_skip_itself(doc):
    assert "automerge" in doc["jobs"] and job(doc)["steps"][0]["run"].count('endswith("automerge")') == 1


def script(doc):
    return job(doc)["steps"][0]["run"]


def run(doc, tmp_path, polls):
    """Runs the step with a fake gh that answers each check-runs call from `polls`, then records any merge."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for i, runs in enumerate(polls):
        (tmp_path / f"poll{i}.json").write_text(json.dumps({"check_runs": runs}))
    (bin_dir / "gh").write_text(f"""#!/usr/bin/env bash
set -euo pipefail
d={tmp_path}
if [ "$1" = api ]; then
  n=$(cat "$d/n" 2>/dev/null || echo 0); echo $((n+1)) > "$d/n"
  f="$d/poll$n.json"; [ -f "$f" ] || f="$d/poll$(( {len(polls)} - 1 )).json"
  jq -c "$4" "$f" 2>/dev/null || jq -c "${{@: -1}}" "$f"
  exit 0
fi
echo "$@" >> "$d/gh.calls"
""")
    (bin_dir / "gh").chmod(0o755)
    (bin_dir / "sleep").write_text("#!/bin/sh\nexit 0\n")
    (bin_dir / "sleep").chmod(0o755)
    env = {"PATH": f"{bin_dir}:{os.environ['PATH']}", "GH_TOKEN": "x", "REPO": "o/r", "PR": "7", "SHA": "abc",
           "METHOD": "squash", "AUTOMERGE_POLLS": "6", "AUTOMERGE_SLEEP": "0", "AUTOMERGE_SETTLE": "0"}
    done = subprocess.run(["bash", "-c", script(doc)], env=env, capture_output=True, text=True, check=False)
    calls = (tmp_path / "gh.calls").read_text().splitlines() if (tmp_path / "gh.calls").exists() else []
    return done, calls


def check(name, status="completed", conclusion="success"):
    return {"name": name, "status": status, "conclusion": conclusion}


pytestmark = pytest.mark.skipif(not shutil.which("jq"), reason="jq is required to run the workflow step")


def test_it_merges_when_every_other_check_passed(doc, tmp_path):
    ok = [check("core"), check("shell"), check("automerge / automerge", "in_progress", None)]
    done, calls = run(doc, tmp_path, [ok, ok, ok])
    assert done.returncode == 0, done.stderr
    assert calls == ["pr merge 7 --repo o/r --squash --delete-branch"]


def test_a_skipped_or_neutral_check_does_not_block_the_merge(doc, tmp_path):
    ok = [check("core"), check("optional", conclusion="skipped"), check("note", conclusion="neutral")]
    done, calls = run(doc, tmp_path, [ok, ok, ok])
    assert done.returncode == 0 and len(calls) == 1


def test_a_failed_check_stops_the_merge(doc, tmp_path):
    bad = [check("core"), check("shell", conclusion="failure")]
    done, calls = run(doc, tmp_path, [bad])
    assert done.returncode == 1 and calls == []
    assert "failed" in done.stderr


def test_a_pending_check_waits_and_the_merge_follows_once_it_passes(doc, tmp_path):
    waiting = [check("core"), check("shell", "in_progress", None)]
    ok = [check("core"), check("shell")]
    done, calls = run(doc, tmp_path, [waiting, waiting, ok, ok, ok])
    assert done.returncode == 0 and len(calls) == 1


def test_no_other_check_yet_means_no_merge(doc, tmp_path):
    done, calls = run(doc, tmp_path, [[check("automerge / automerge", "in_progress", None)]])
    assert done.returncode == 1 and calls == []
    assert "timed out" in done.stderr


def test_a_check_that_appears_late_is_waited_for(doc, tmp_path):
    early = [check("core")]
    late = [check("core"), check("shell", "queued", None)]
    ok = [check("core"), check("shell")]
    done, calls = run(doc, tmp_path, [early, late, ok, ok, ok])
    assert done.returncode == 0 and len(calls) == 1
