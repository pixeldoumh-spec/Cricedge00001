"""Point-in-time pre-match feature construction.

Feature calculation will be implemented after the historical data contract is
finalized. Keeping the builder separate from the schema prevents training and
serving code from inventing feature names independently.
"""

from .schema import PreMatchFeatures


class PreMatchFeatureBuilder:
    """Build ``PreMatchFeatures`` from point-in-time cricket data."""

    def build(self, *, team: str, opponent: str, venue: str) -> PreMatchFeatures:
        """Return the feature vector for a future match.

        This method is intentionally not implemented yet. The next model step
        will connect it to historical, leakage-safe feature sources.
        """
        raise NotImplementedError(
            "Pre-match feature calculation will be implemented after the "
            "historical dataset contract is finalized."
        )
