"""Strong learner baseline: modular BOA with Smith frequency model."""

from negmas.gb.components.genius.models import GSmithFrequencyModel
from negmas.sao.components.acceptance import ACNext
from negmas.sao.components.offering import TimeBasedOfferingPolicy
from negmas.sao.negotiators.modular import BOANegotiator

__all__ = ["LearnerStrong"]


class LearnerStrong(BOANegotiator):
    """
    Tougher BOA-style learner for sparring (frequency model + time-based bids).

    Same architecture family as ``examples.boa.BOANeg`` but registered as a
    dedicated comparison opponent.
    """

    def __init__(self, *args, **kwargs) -> None:
        offering = TimeBasedOfferingPolicy()
        kwargs |= dict(
            acceptance=ACNext(offering),
            offering=offering,
            model=GSmithFrequencyModel(),
        )
        super().__init__(*args, **kwargs)
