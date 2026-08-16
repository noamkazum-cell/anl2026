"""Back-compat alias for the final submission module.

The submitted agent lives in ``agent360_FINAL.py`` (packaged as ``submitted_v4.zip``).
"""

from agent360_FINAL import *  # noqa: F403
from agent360_FINAL import Agent360, Agent360Base, Agent360V2

__all__ = ["Agent360", "Agent360Base", "Agent360V2"]
