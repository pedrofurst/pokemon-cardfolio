from dataclasses import dataclass


@dataclass
class GradingInput:
    raw_price: float
    psa10_price: float | None
    psa9_price: float | None
    grading_cost: float = 25.0
    selling_fees_pct: float = 13.0
    prob_psa10: float = 0.5


@dataclass
class GradingResult:
    raw_net: float
    psa10_net: float | None
    psa9_net: float | None
    expected_graded_net: float | None
    uplift: float | None
    roi_pct: float | None
    recommendation: str
    rationale: str


class GradingService:
    def evaluate(self, data: GradingInput) -> GradingResult:
        fees = data.selling_fees_pct / 100
        raw_net = data.raw_price * (1 - fees)

        psa10_net = self._graded_net(data.psa10_price, fees, data.grading_cost)
        psa9_net = self._graded_net(data.psa9_price, fees, data.grading_cost)
        expected_graded_net = self._expected_graded_net(psa10_net, psa9_net, data.prob_psa10)

        uplift = expected_graded_net - raw_net if expected_graded_net is not None else None
        roi_pct = (
            uplift / data.grading_cost * 100
            if uplift is not None and data.grading_cost > 0
            else None
        )

        recommendation, rationale = self._recommend(raw_net, expected_graded_net, uplift)
        rationale = self._append_single_grade_caveat(
            recommendation, rationale, data.psa10_price, data.psa9_price,
        )

        return GradingResult(
            raw_net=raw_net,
            psa10_net=psa10_net,
            psa9_net=psa9_net,
            expected_graded_net=expected_graded_net,
            uplift=uplift,
            roi_pct=roi_pct,
            recommendation=recommendation,
            rationale=rationale,
        )

    def _graded_net(self, price: float | None, fees: float, grading_cost: float) -> float | None:
        if price is None:
            return None
        return price * (1 - fees) - grading_cost

    def _expected_graded_net(
        self, psa10_net: float | None, psa9_net: float | None, prob_psa10: float,
    ) -> float | None:
        if psa10_net is not None and psa9_net is not None:
            return prob_psa10 * psa10_net + (1 - prob_psa10) * psa9_net
        if psa10_net is not None:
            return psa10_net
        if psa9_net is not None:
            return psa9_net
        return None

    def _recommend(
        self, raw_net: float, expected_graded_net: float | None, uplift: float | None,
    ) -> tuple[str, str]:
        if expected_graded_net is None:
            return "INSUFFICIENT_DATA", "Enter at least a PSA 10 (or PSA 9) price"
        if uplift is not None and uplift > 0:
            rationale = (
                f"Expected graded net ${expected_graded_net:.2f} beats raw "
                f"${raw_net:.2f} by ${uplift:.2f}"
            )
            return "GRADE", rationale
        rationale = (
            f"Raw net ${raw_net:.2f} >= expected graded net ${expected_graded_net:.2f}; "
            "grading not worth the cost"
        )
        return "DONT_GRADE", rationale

    def _append_single_grade_caveat(
        self,
        recommendation: str,
        rationale: str,
        psa10_price: float | None,
        psa9_price: float | None,
    ) -> str:
        is_single_grade_branch = (psa10_price is not None) != (psa9_price is not None)
        if not is_single_grade_branch or recommendation not in ("GRADE", "DONT_GRADE"):
            return rationale
        assumed_grade = "10" if psa10_price is not None else "9"
        return (
            f"{rationale} (Assumes a guaranteed PSA {assumed_grade} outcome — enter both "
            "PSA 10 and PSA 9 prices to weight by grade probability.)"
        )
