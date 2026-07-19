from app.providers.graded_base import GradedPrices


class NullGradedPriceProvider:
    def get_graded_prices(self, card_id: str) -> GradedPrices | None:
        return None
