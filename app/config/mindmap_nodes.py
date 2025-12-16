"""
マインドマップのnodeId定義
既存の質問定義（*_questions.py）と完全一致させる
"""
from __future__ import annotations

from app.config.concept_questions import CONCEPT_QUESTIONS
from app.config.revenue_forecast_questions import REVENUE_FORECAST_QUESTIONS
from app.config.funding_plan_questions import FUNDING_PLAN_QUESTIONS
from app.config.operation_questions import OPERATION_QUESTIONS
from app.config.location_questions import LOCATION_QUESTIONS
from app.config.interior_exterior_questions import INTERIOR_EXTERIOR_QUESTIONS
from app.config.marketing_questions import MARKETING_QUESTIONS
from app.config.menu_questions import MENU_QUESTIONS


# 軸コード → 質問定義 / 表示名 / Answerテーブル名
AXIS_CONFIG = {
    "concept": {
        "name": "コンセプト",
        "questions": CONCEPT_QUESTIONS,
        "answer_table": "concept_answers",
    },
    "revenue_forecast": {
        "name": "収支予測",
        "questions": REVENUE_FORECAST_QUESTIONS,
        "answer_table": "revenue_forecast_answers",
    },
    "funds": {
        "name": "資金計画",
        "questions": FUNDING_PLAN_QUESTIONS,
        "answer_table": "funding_plan_answers",
    },
    "operation": {
        "name": "オペレーション",
        "questions": OPERATION_QUESTIONS,
        "answer_table": "operation_answers",
    },
    "location": {
        "name": "立地",
        "questions": LOCATION_QUESTIONS,
        "answer_table": "location_answers",
    },
    "interior_exterior": {
        "name": "内装外装",
        "questions": INTERIOR_EXTERIOR_QUESTIONS,
        "answer_table": "interior_exterior_answers",
    },
    "marketing": {
        "name": "販促",
        "questions": MARKETING_QUESTIONS,
        "answer_table": "marketing_answers",
    },
    "menu": {
        "name": "メニュー",
        "questions": MENU_QUESTIONS,
        "answer_table": "menu_answers",
    },
}


def _build_valid_node_ids() -> set[str]:
    """全nodeIdを自動生成"""
    ids = set()
    for axis_code, config in AXIS_CONFIG.items():
        # 軸ノード（第1階層）
        ids.add(axis_code)
        # カードノード（第2階層）
        for card_id in config["questions"].keys():
            ids.add(f"{axis_code}_{card_id}")
    return ids


VALID_NODE_IDS = _build_valid_node_ids()


def parse_node_id(node_id: str) -> tuple[str, str | None]:
    """
    nodeIdを(axis_code, card_id)に分解

    Args:
        node_id: 例 "concept" または "concept_1-1"

    Returns:
        tuple[str, str | None]: (axis_code, card_id)
        - 軸ノード: ("concept", None)
        - カードノード: ("concept", "1-1")

    Raises:
        ValueError: 不正なnodeIdの場合
    """
    # 軸ノードの場合
    if node_id in AXIS_CONFIG:
        return (node_id, None)

    # カードノードの場合: {axis_code}_{card_id}
    # concept_1-1 → axis_code="concept", card_id="1-1"
    # funds_3 → axis_code="funds", card_id="3"
    parts = node_id.split("_", 1)
    if len(parts) == 2:
        axis_code, card_id = parts
        if axis_code in AXIS_CONFIG and card_id in AXIS_CONFIG[axis_code]["questions"]:
            return (axis_code, card_id)

    raise ValueError(f"Invalid node_id: {node_id}")


def get_card_title(node_id: str) -> str | None:
    """nodeIdからカードタイトルを取得"""
    try:
        axis_code, card_id = parse_node_id(node_id)
        if card_id is None:
            return AXIS_CONFIG[axis_code]["name"]
        return AXIS_CONFIG[axis_code]["questions"][card_id]["title"]
    except (ValueError, KeyError):
        return None
