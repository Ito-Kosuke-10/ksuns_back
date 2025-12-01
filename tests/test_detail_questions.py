import pytest

from app.services.detail_questions import (
    AxisScoreResult,
    calculate_detail_progress,
    pick_next_focus_axis,
    summarize_concept_text,
)


def test_calculate_detail_progress_counts_answered_and_total():
    answers = {
        "concept_q1": True,
        "concept_q2": None,
        "funds_q1": False,
        "operation_q1": None,
    }
    progress = calculate_detail_progress(answers)
    assert progress["total"] == 24  # 定義済みの24問が対象
    assert progress["answered"] == 2  # True/False のみカウントされる


def test_pick_next_focus_axis_prefers_missing_answers():
    axes = [
        AxisScoreResult(
            code="concept",
            name="コンセプト",
            score=6.0,
            ok_line=5.0,
            growth_zone=6.0,
            answered=3,
            total_questions=3,
            missing=0,
            comment="",
            next_step="",
        ),
        AxisScoreResult(
            code="funds",
            name="収支予測",
            score=5.0,
            ok_line=5.0,
            growth_zone=6.0,
            answered=1,
            total_questions=3,
            missing=2,
            comment="",
            next_step="",
        ),
    ]

    focus = pick_next_focus_axis(axes)
    assert focus is not None
    assert focus["axis_code"] == "funds"
    assert "未回答" in focus["reason"]


def test_pick_next_focus_axis_low_score_when_no_missing():
    axes = [
        AxisScoreResult(
            code="concept",
            name="コンセプト",
            score=2.0,
            ok_line=5.0,
            growth_zone=6.0,
            answered=3,
            total_questions=3,
            missing=0,
            comment="",
            next_step="",
        ),
        AxisScoreResult(
            code="funds",
            name="収支予測",
            score=4.0,
            ok_line=5.0,
            growth_zone=6.0,
            answered=3,
            total_questions=3,
            missing=0,
            comment="",
            next_step="",
        ),
    ]

    focus = pick_next_focus_axis(axes)
    assert focus is not None
    assert focus["axis_code"] == "concept"
    assert "低め" in focus["reason"]


def test_summarize_concept_text_uses_first_line_as_title():
    raw = "一行目のタイトル\n二行目以降が説明文"
    summary = summarize_concept_text(raw)
    assert summary["title"] == "一行目のタイトル"
    assert "二行目以降" in summary["description"]
