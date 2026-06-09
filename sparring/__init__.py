"""In-house sparring opponents for ANL 2026 evaluation (2026-native, no oracle ufun)."""

from sparring.learner_strong import LearnerStrong
from sparring.mirror import MirrorAgent
from sparring.renting_lite import RentingLite
from sparring.shochan_lite import ShochanLite
from sparring.uoagent_lite import UOAgentLite

__all__ = [
    "LearnerStrong",
    "MirrorAgent",
    "RentingLite",
    "ShochanLite",
    "UOAgentLite",
    "SPARRING_OPPONENTS",
    "SPARRING_LITE_CLASS_PATHS",
    "sparring_opponent_kwargs",
]

# Lite agents from ANL 2024 support optional decoy/bait persona (default on).
SPARRING_LITE_CLASS_PATHS: frozenset[str] = frozenset(
    {
        "sparring.shochan_lite.ShochanLite",
        "sparring.uoagent_lite.UOAgentLite",
        "sparring.renting_lite.RentingLite",
    }
)


def sparring_opponent_kwargs(class_path: str, *, deceptive: bool = True) -> dict:
    """Constructor kwargs for sparring panel opponents."""
    if class_path in SPARRING_LITE_CLASS_PATHS:
        return {"deceptive": deceptive}
    return {}


# (import path, short label, family tag)
SPARRING_OPPONENTS: list[tuple[str, str, str]] = [    ("sparring.shochan_lite.ShochanLite", "ShochanLite", "sparring"),
    ("sparring.uoagent_lite.UOAgentLite", "UOAgentLite", "sparring"),
    ("sparring.renting_lite.RentingLite", "RentingLite", "sparring"),
    ("sparring.learner_strong.LearnerStrong", "LearnerStrong", "sparring"),
    ("sparring.mirror.MirrorAgent", "MirrorAgent", "mirror"),
]
