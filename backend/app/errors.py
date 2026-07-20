class PriceProviderError(Exception):
    """External price source failed."""


class CardNotFoundError(Exception):
    """No card matched the given id."""


class HoldingNotFoundError(Exception):
    """No holding matched the given id."""
