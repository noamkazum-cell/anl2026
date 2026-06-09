"""Submission package sanity checks."""

import zipfile
from pathlib import Path

from agent360_submit import Agent360, Agent360Base, Agent360V2
from agent360_v2 import Agent360V2 as DevAgent360V2
from agent360_v3 import Agent360V3


ROOT = Path(__file__).resolve().parent.parent


def test_submission_agent_inheritance():
    assert issubclass(Agent360, Agent360V2)
    assert issubclass(Agent360V2, Agent360Base)
    assert issubclass(Agent360V3, DevAgent360V2)


def test_submission_agent_instantiation():
    agent = Agent360()
    assert agent.FIRST_MIN_OPPONENT_OFFERS == 3
    assert agent.FIRST_DECOY_NO_REPEAT_WINDOW == 5


def test_submitted_zip_contains_only_upload_files():
    zip_path = ROOT / "submitted.zip"
    if not zip_path.is_file():
        return
    with zipfile.ZipFile(zip_path) as zf:
        assert sorted(zf.namelist()) == ["agent360.py", "requirements.txt"]
