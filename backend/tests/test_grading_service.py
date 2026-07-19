from app.services.grading_service import GradingInput, GradingService


def test_should_recommend_grade_when_expected_graded_net_beats_raw_net() -> None:
    service = GradingService()
    input = GradingInput(
        raw_price=50, psa10_price=300, psa9_price=120, grading_cost=25,
        selling_fees_pct=13, prob_psa10=0.5,
    )

    result = service.evaluate(input)

    assert result.recommendation == "GRADE"


def test_should_recommend_dont_grade_when_raw_net_beats_expected_graded_net() -> None:
    service = GradingService()
    input = GradingInput(
        raw_price=200, psa10_price=210, psa9_price=None, grading_cost=25,
        selling_fees_pct=13, prob_psa10=0.5,
    )

    result = service.evaluate(input)

    assert result.recommendation == "DONT_GRADE"


def test_should_recommend_insufficient_data_when_no_graded_prices_given() -> None:
    service = GradingService()
    input = GradingInput(
        raw_price=50, psa10_price=None, psa9_price=None, grading_cost=25,
        selling_fees_pct=13, prob_psa10=0.5,
    )

    result = service.evaluate(input)

    assert result.recommendation == "INSUFFICIENT_DATA"


def test_should_use_psa10_net_as_expected_graded_net_when_only_psa10_given() -> None:
    service = GradingService()
    input = GradingInput(
        raw_price=200, psa10_price=210, psa9_price=None, grading_cost=25,
        selling_fees_pct=13, prob_psa10=0.5,
    )

    result = service.evaluate(input)

    assert result.expected_graded_net == result.psa10_net


def test_should_compute_roi_pct_from_uplift_and_grading_cost() -> None:
    service = GradingService()
    input = GradingInput(
        raw_price=50, psa10_price=300, psa9_price=120, grading_cost=25,
        selling_fees_pct=13, prob_psa10=0.5,
    )

    result = service.evaluate(input)

    assert result.roi_pct == (result.uplift / 25 * 100)


def test_should_append_single_grade_caveat_when_only_psa10_given_and_grade_recommended() -> None:
    service = GradingService()
    input = GradingInput(
        raw_price=50, psa10_price=300, psa9_price=None, grading_cost=25,
        selling_fees_pct=13, prob_psa10=0.5,
    )

    result = service.evaluate(input)

    assert "grade probability" in result.rationale


def test_should_not_append_single_grade_caveat_when_both_prices_given() -> None:
    service = GradingService()
    input = GradingInput(
        raw_price=50, psa10_price=300, psa9_price=120, grading_cost=25,
        selling_fees_pct=13, prob_psa10=0.5,
    )

    result = service.evaluate(input)

    assert "grade probability" not in result.rationale
