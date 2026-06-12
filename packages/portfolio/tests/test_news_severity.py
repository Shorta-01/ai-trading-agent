"""Tests for the news-severity classifier + exit evaluator (V1.2 §K)."""

from __future__ import annotations

from portfolio_outlook_portfolio import (
    NewsItem,
    NewsSeverity,
    classify_news_severity,
    evaluate_news_exit,
)

# ---- single-item classification --------------------------------------


def test_routine_news_classified_as_info() -> None:
    result = classify_news_severity(NewsItem(title="Apple unveils new iPhone color"))
    assert result.severity is NewsSeverity.INFO
    assert result.matched_keyword is None


def test_dividend_news_classified_as_info() -> None:
    result = classify_news_severity(NewsItem(title="Microsoft declares quarterly dividend"))
    assert result.severity is NewsSeverity.INFO


# ---- WARN tier -------------------------------------------------------


def test_downgrade_classified_as_warn() -> None:
    result = classify_news_severity(
        NewsItem(title="Morgan Stanley downgrade for XYZ Corp")
    )
    assert result.severity is NewsSeverity.WARN
    assert result.matched_keyword == "downgrade"


def test_below_estimates_classified_as_warn() -> None:
    result = classify_news_severity(
        NewsItem(title="Q3 revenue below estimates")
    )
    assert result.severity is NewsSeverity.WARN


def test_regulatory_inquiry_classified_as_warn() -> None:
    result = classify_news_severity(
        NewsItem(title="Regulatory inquiry into pricing practices")
    )
    assert result.severity is NewsSeverity.WARN


# ---- ALERT tier ------------------------------------------------------


def test_profit_warning_classified_as_alert() -> None:
    result = classify_news_severity(NewsItem(title="Company issues profit warning"))
    assert result.severity is NewsSeverity.ALERT
    assert result.matched_keyword == "profit warning"


def test_dutch_winstwaarschuwing_classified_as_alert() -> None:
    result = classify_news_severity(
        NewsItem(title="Bedrijf geeft winstwaarschuwing af")
    )
    assert result.severity is NewsSeverity.ALERT
    assert result.matched_keyword == "winstwaarschuwing"


def test_ceo_resignation_classified_as_alert() -> None:
    result = classify_news_severity(NewsItem(title="CEO resigns amid concerns"))
    assert result.severity is NewsSeverity.ALERT


def test_dutch_ceo_vertrekt_classified_as_alert() -> None:
    result = classify_news_severity(NewsItem(title="CEO vertrekt na boekjaar"))
    assert result.severity is NewsSeverity.ALERT


def test_class_action_classified_as_alert() -> None:
    result = classify_news_severity(
        NewsItem(title="Shareholders file class action lawsuit")
    )
    assert result.severity is NewsSeverity.ALERT


def test_product_recall_classified_as_alert() -> None:
    result = classify_news_severity(NewsItem(title="Massive product recall ordered"))
    assert result.severity is NewsSeverity.ALERT


def test_fda_rejection_classified_as_alert() -> None:
    result = classify_news_severity(NewsItem(title="FDA rejects new drug approval"))
    assert result.severity is NewsSeverity.ALERT


# ---- CRITICAL tier ---------------------------------------------------


def test_fraud_classified_as_critical() -> None:
    result = classify_news_severity(NewsItem(title="Accounting fraud uncovered"))
    assert result.severity is NewsSeverity.CRITICAL
    assert result.matched_keyword == "fraud"


def test_dutch_fraude_classified_as_critical() -> None:
    result = classify_news_severity(NewsItem(title="Fraude bij beursfonds"))
    assert result.severity is NewsSeverity.CRITICAL
    assert result.matched_keyword == "fraude"


def test_bankruptcy_classified_as_critical() -> None:
    result = classify_news_severity(NewsItem(title="Company files for bankruptcy"))
    assert result.severity is NewsSeverity.CRITICAL


def test_chapter_11_classified_as_critical() -> None:
    result = classify_news_severity(NewsItem(title="Files Chapter 11 protection"))
    assert result.severity is NewsSeverity.CRITICAL
    assert result.matched_keyword == "chapter 11"


def test_dutch_faillissement_classified_as_critical() -> None:
    result = classify_news_severity(
        NewsItem(title="Faillissement aangevraagd voor onderneming")
    )
    assert result.severity is NewsSeverity.CRITICAL


def test_going_concern_classified_as_critical() -> None:
    result = classify_news_severity(
        NewsItem(title="Auditor raises going concern doubt")
    )
    assert result.severity is NewsSeverity.CRITICAL


def test_sec_investigation_classified_as_critical() -> None:
    result = classify_news_severity(
        NewsItem(title="SEC investigation opened into accounting practices")
    )
    assert result.severity is NewsSeverity.CRITICAL


def test_delisting_classified_as_critical() -> None:
    result = classify_news_severity(NewsItem(title="Exchange announces delisting"))
    assert result.severity is NewsSeverity.CRITICAL


# ---- precedence: highest severity wins -------------------------------


def test_critical_beats_alert_when_both_present() -> None:
    # Body has profit warning (ALERT); title has fraud (CRITICAL).
    # CRITICAL must win.
    result = classify_news_severity(
        NewsItem(
            title="Fraud allegations emerge",
            body="The company also issued a profit warning today.",
        )
    )
    assert result.severity is NewsSeverity.CRITICAL
    assert result.matched_keyword == "fraud"


def test_alert_beats_warn_when_both_present() -> None:
    result = classify_news_severity(
        NewsItem(
            title="Downgrade and profit warning issued",
            body="",
        )
    )
    assert result.severity is NewsSeverity.ALERT


def test_match_in_body_also_counted() -> None:
    result = classify_news_severity(
        NewsItem(
            title="Routine 8-K filing",
            body="The filing discloses a winstwaarschuwing for next quarter.",
        )
    )
    assert result.severity is NewsSeverity.ALERT


# ---- false-positive guards -------------------------------------------


def test_fraud_substring_does_not_falsely_trigger_on_fraudster_article() -> None:
    # "fraudster" should NOT match "fraud" because of \b word
    # boundary on single-word keywords.
    #
    # NOTE: in current implementation, the \b boundary makes
    # "fraudster" not match "fraud". Test the negation.
    result = classify_news_severity(
        NewsItem(title="Cybersecurity firm tracks fraudsters in the wild")
    )
    # "fraudsters" should not match "fraud" — strict word boundary.
    assert result.severity is NewsSeverity.INFO


def test_downgrade_within_word_not_triggered() -> None:
    # A made-up word containing "downgrade" as substring shouldn't
    # fire — single-word keywords use \b.
    result = classify_news_severity(NewsItem(title="Subdowngrades unusual"))
    assert result.severity is NewsSeverity.INFO


# ---- exit evaluator --------------------------------------------------


def test_evaluator_no_news_returns_no_exit() -> None:
    result = evaluate_news_exit([])
    assert not result.should_exit
    assert result.exit_severity is None
    assert result.classification_counts[NewsSeverity.INFO] == 0


def test_evaluator_only_info_returns_no_exit() -> None:
    result = evaluate_news_exit(
        [
            NewsItem(title="New product launch"),
            NewsItem(title="Quarterly dividend declared"),
        ]
    )
    assert not result.should_exit
    assert result.classification_counts[NewsSeverity.INFO] == 2


def test_evaluator_only_warn_returns_no_exit() -> None:
    # WARN is informational, not actionable.
    result = evaluate_news_exit(
        [NewsItem(title="Morgan Stanley downgrade for stock")]
    )
    assert not result.should_exit
    assert result.classification_counts[NewsSeverity.WARN] == 1


def test_evaluator_one_alert_triggers_exit() -> None:
    result = evaluate_news_exit(
        [
            NewsItem(title="Routine market commentary"),
            NewsItem(title="Company issues profit warning"),
        ]
    )
    assert result.should_exit
    assert result.exit_severity is NewsSeverity.ALERT
    assert result.triggering_keyword == "profit warning"
    assert result.classification_counts[NewsSeverity.ALERT] == 1
    assert result.classification_counts[NewsSeverity.INFO] == 1


def test_evaluator_one_critical_triggers_exit() -> None:
    result = evaluate_news_exit(
        [NewsItem(title="Accounting fraud uncovered at firm")]
    )
    assert result.should_exit
    assert result.exit_severity is NewsSeverity.CRITICAL
    assert result.triggering_keyword == "fraud"


def test_evaluator_first_actionable_wins_when_multiple_present() -> None:
    # Items in sequence: INFO, ALERT, CRITICAL. The ALERT is the
    # first that crosses the bar, so it's the trigger.
    result = evaluate_news_exit(
        [
            NewsItem(title="Press release routine"),
            NewsItem(title="Issued profit warning"),
            NewsItem(title="Reports of fraud emerging"),
        ]
    )
    assert result.should_exit
    assert result.exit_severity is NewsSeverity.ALERT
    assert result.triggering_keyword == "profit warning"
    # Counts include all items.
    assert result.classification_counts[NewsSeverity.INFO] == 1
    assert result.classification_counts[NewsSeverity.ALERT] == 1
    assert result.classification_counts[NewsSeverity.CRITICAL] == 1


def test_evaluator_counts_all_classifications() -> None:
    result = evaluate_news_exit(
        [
            NewsItem(title="Product update"),
            NewsItem(title="Dividend declared"),
            NewsItem(title="Stock downgrade today"),
            NewsItem(title="Earnings missed estimates"),
            NewsItem(title="Company files for bankruptcy"),
        ]
    )
    assert result.should_exit
    counts = result.classification_counts
    assert counts[NewsSeverity.INFO] == 2
    assert counts[NewsSeverity.WARN] == 2
    assert counts[NewsSeverity.ALERT] == 0
    assert counts[NewsSeverity.CRITICAL] == 1
