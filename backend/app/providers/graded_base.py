from dataclasses import dataclass
from typing import Protocol


@dataclass
class GradedPrices:
    psa10: float | None
    psa9: float | None
    source: str


class GradedPriceProvider(Protocol):
    def get_graded_prices(self, card_id: str) -> GradedPrices | None: ...
