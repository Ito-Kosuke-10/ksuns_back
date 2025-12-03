from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.axis import AxisScore, PlanningAxis
from app.models.detail_question import DetailQuestionAnswer

OK_LINE = 5.0
GROWTH_ZONE = 6.0

AXIS_DEFAULTS: dict[str, str] = {
    "concept": "コンセプト",
    "funds": "収支予測",
    "compliance": "資金計画",
    "operation": "オペレーション",
    "location": "立地",
    "equipment": "内装外装",
    "marketing": "販促",
    "menu": "メニュー",
}

AXIS_ORDER: list[str] = [
    "concept",
    "funds",
    "compliance",
    "operation",
    "location",
    "equipment",
    "marketing",
    "menu",
]

DETAIL_QUESTION_DEFINITIONS: list[dict[str, str]] = [
    {
        "code": "concept_q1",
        "axis_code": "concept",
        "axis_label": AXIS_DEFAULTS["concept"],
        "text": "誰に・どんなシーンで・何を提供するかを一文で言葉にできている",
    },
    {
        "code": "concept_q2",
        "axis_code": "concept",
        "axis_label": AXIS_DEFAULTS["concept"],
        "text": "競合との差別化ポイントやポジションイメージが決まっている",
    },
    {
        "code": "concept_q3",
        "axis_code": "concept",
        "axis_label": AXIS_DEFAULTS["concept"],
        "text": "価格帯と体験のバランスが整合しており、理想の客像が浮かぶ",
    },
    {
        "code": "funds_q1",
        "axis_code": "funds",
        "axis_label": AXIS_DEFAULTS["funds"],
        "text": "月次売上（客数・客単価・回転数）のラフな試算をしている",
    },
    {
        "code": "funds_q2",
        "axis_code": "funds",
        "axis_label": AXIS_DEFAULTS["funds"],
        "text": "主要費用（原価・人件費・固定費）の見積もりと根拠を持っている",
    },
    {
        "code": "funds_q3",
        "axis_code": "funds",
        "axis_label": AXIS_DEFAULTS["funds"],
        "text": "損益分岐点とキャッシュフローのイメージを把握している",
    },
    {
        "code": "compliance_q1",
        "axis_code": "compliance",
        "axis_label": AXIS_DEFAULTS["compliance"],
        "text": "初期投資額と自己資金・融資・補助金などの調達計画を描いている",
    },
    {
        "code": "compliance_q2",
        "axis_code": "compliance",
        "axis_label": AXIS_DEFAULTS["compliance"],
        "text": "返済計画と月次キャッシュフローの耐久性を確認している",
    },
    {
        "code": "compliance_q3",
        "axis_code": "compliance",
        "axis_label": AXIS_DEFAULTS["compliance"],
        "text": "設備・内装・許認可にかかる主要コストを洗い出している",
    },
    {
        "code": "operation_q1",
        "axis_code": "operation",
        "axis_label": AXIS_DEFAULTS["operation"],
        "text": "営業時間・シフト・導線など1日のオペレーションを具体的に描いている",
    },
    {
        "code": "operation_q2",
        "axis_code": "operation",
        "axis_label": AXIS_DEFAULTS["operation"],
        "text": "衛生管理・レジ・予約など基本ルールを決めている",
    },
    {
        "code": "operation_q3",
        "axis_code": "operation",
        "axis_label": AXIS_DEFAULTS["operation"],
        "text": "繁忙・閑散時の体制をシミュレーションしリスクを把握している",
    },
    {
        "code": "location_q1",
        "axis_code": "location",
        "axis_label": AXIS_DEFAULTS["location"],
        "text": "候補エリアの人通り・競合・賃料相場を調べて比較できている",
    },
    {
        "code": "location_q2",
        "axis_code": "location",
        "axis_label": AXIS_DEFAULTS["location"],
        "text": "想定売上に対する家賃比率が妥当かを検証している",
    },
    {
        "code": "location_q3",
        "axis_code": "location",
        "axis_label": AXIS_DEFAULTS["location"],
        "text": "看板・導線・視認性を踏まえた物件条件を整理している",
    },
    {
        "code": "equipment_q1",
        "axis_code": "equipment",
        "axis_label": AXIS_DEFAULTS["equipment"],
        "text": "コンセプトに合う内外装イメージ（ラフでも可）を持っている",
    },
    {
        "code": "equipment_q2",
        "axis_code": "equipment",
        "axis_label": AXIS_DEFAULTS["equipment"],
        "text": "厨房・客席・収納の配置を簡易レイアウトに落とし込んでいる",
    },
    {
        "code": "equipment_q3",
        "axis_code": "equipment",
        "axis_label": AXIS_DEFAULTS["equipment"],
        "text": "必要な設備要件や許可の条件を把握している",
    },
    {
        "code": "marketing_q1",
        "axis_code": "marketing",
        "axis_label": AXIS_DEFAULTS["marketing"],
        "text": "オープン前〜初月の集客チャネルと施策を決めている",
    },
    {
        "code": "marketing_q2",
        "axis_code": "marketing",
        "axis_label": AXIS_DEFAULTS["marketing"],
        "text": "口コミ・レビューを集める動線を設計している",
    },
    {
        "code": "marketing_q3",
        "axis_code": "marketing",
        "axis_label": AXIS_DEFAULTS["marketing"],
        "text": "リピートにつながる仕組み（会員・LINE・スタンプ等）を用意する予定",
    },
    {
        "code": "menu_q1",
        "axis_code": "menu",
        "axis_label": AXIS_DEFAULTS["menu"],
        "text": "看板メニューと価格設定の叩き台がある",
    },
    {
        "code": "menu_q2",
        "axis_code": "menu",
        "axis_label": AXIS_DEFAULTS["menu"],
        "text": "主要メニューの原価計算を行っている",
    },
    {
        "code": "menu_q3",
        "axis_code": "menu",
        "axis_label": AXIS_DEFAULTS["menu"],
        "text": "仕入れ・仕込み・提供フローを具体的にイメージしている",
    },
]

AXIS_NEXT_STEPS: dict[str, str] = {
    "concept": "ターゲット・提供価値・体験を1文にまとめ、写真やキーワードで共有しましょう。",
    "funds": "客数×客単価×回転数で売上を算出し、原価・人件費・家賃をセットで確認しましょう。",
    "compliance": "自己資金・融資・補助金の組み合わせと返済計画をラフに計算してみましょう。",
    "operation": "1日の流れをタイムラインにし、シフトと導線を簡単なメモに落としましょう。",
    "location": "候補エリアの賃料相場と人通りを比較し、家賃比率が妥当か確認しましょう。",
    "equipment": "厨房・客席・収納のラフ図を作り、必要設備のチェックリストを埋めましょう。",
    "marketing": "初月の集客チャネルを3つ決め、口コミ収集と再来店の仕組みをセットで用意しましょう。",
    "menu": "看板メニュー3品の原価と提供フローを決め、価格を仮置きして試算しましょう。",
}


@dataclass
class AxisScoreResult:
    code: str
    name: str
    score: float
    ok_line: float
    growth_zone: float
    answered: int
    total_questions: int
    missing: int
    comment: str
    next_step: str


def get_detail_questions() -> list[dict[str, str]]:
    return DETAIL_QUESTION_DEFINITIONS


async def fetch_axis_meta(session: AsyncSession) -> dict[str, dict[str, str | int]]:
    result = await session.execute(select(PlanningAxis))
    meta: dict[str, dict[str, str | int]] = {}
    for axis in result.scalars():
        meta[axis.code] = {
            "id": axis.id,
            "name": axis.name or AXIS_DEFAULTS.get(axis.code, axis.code),
            "description": axis.description or "",
        }
    return meta


async def fetch_detail_answers(session: AsyncSession, user_id: int) -> dict[str, bool | None]:
    result = await session.execute(
        select(DetailQuestionAnswer).where(DetailQuestionAnswer.user_id == user_id)
    )
    answers: dict[str, bool | None] = {}
    for row in result.scalars():
        answers[row.question_code] = row.answer
    return answers


async def save_detail_answers(session: AsyncSession, user_id: int, answers: dict[str, bool | None]) -> None:
    valid_codes = {q["code"] for q in DETAIL_QUESTION_DEFINITIONS}
    axis_by_question = {q["code"]: q["axis_code"] for q in DETAIL_QUESTION_DEFINITIONS}

    unknown_codes = [code for code in answers.keys() if code not in valid_codes]
    if unknown_codes:
        raise ValueError(f"Unknown question codes: {', '.join(unknown_codes)}")

    existing_result = await session.execute(
        select(DetailQuestionAnswer).where(
            DetailQuestionAnswer.user_id == user_id,
            DetailQuestionAnswer.question_code.in_(list(answers.keys())),
        )
    )
    existing_map = {row.question_code: row for row in existing_result.scalars()}

    # 全問回答必須: 1問でも None があれば 400 相当のエラー
    total = len(DETAIL_QUESTION_DEFINITIONS)
    answered_count = sum(1 for q in DETAIL_QUESTION_DEFINITIONS if answers.get(q["code"]) is not None)
    if answered_count < total:
        raise ValueError("All detail questions (24) must be answered before saving.")

    for question_code, value in answers.items():
        existing = existing_map.get(question_code)
        if value is None:
            if existing:
                await session.execute(
                    delete(DetailQuestionAnswer).where(DetailQuestionAnswer.id == existing.id)
                )
            continue
        if existing:
            existing.answer = bool(value)
        else:
            session.add(
                DetailQuestionAnswer(
                    user_id=user_id,
                    axis_code=axis_by_question[question_code],
                    question_code=question_code,
                    answer=bool(value),
                )
            )

    await session.commit()


def calculate_detail_progress(answers: dict[str, bool | None]) -> dict[str, int]:
    total = len(DETAIL_QUESTION_DEFINITIONS)
    answered = sum(1 for q in DETAIL_QUESTION_DEFINITIONS if answers.get(q["code"]) is not None)
    return {"answered": answered, "total": total}


def _build_axis_question_map() -> dict[str, list[str]]:
    axis_question_map: dict[str, list[str]] = {}
    for q in DETAIL_QUESTION_DEFINITIONS:
        axis_question_map.setdefault(q["axis_code"], []).append(q["code"])
    return axis_question_map


def _build_axis_checkpoints(axis_question_map: dict[str, list[str]]) -> dict[str, list[str]]:
    checkpoints: dict[str, list[str]] = {}
    for axis_code, questions in axis_question_map.items():
        if len(questions) < 3:
            continue
        checkpoints[axis_code] = (
            [questions[0]] * 4 + [questions[1]] * 3 + [questions[2]] * 3
        )
    return checkpoints


def _checkpoint_value(answer: Optional[bool]) -> float:
    if answer is True:
        return 1.0
    if answer is False:
        return 0.0
    return 0.0


def _comment_for_axis(score: float, missing: int) -> str:
    if missing > 0:
        return "未回答があるため推定スコアです。まず3問すべてを埋めましょう。"
    if score >= 8:
        return "順調です。このまま強みを仕上げましょう。"
    if score >= OK_LINE:
        return "OKライン付近です。弱い部分を1つ補強しましょう。"
    if score >= 3:
        return "方向性は見えています。数字や導線を具体化しましょう。"
    return "まだ余白があります。基本のYESをそろえることから始めましょう。"


def _next_step_for_axis(axis_code: str, missing: int) -> str:
    hint = AXIS_NEXT_STEPS.get(axis_code, "次の一歩を具体化しましょう。")
    if missing > 0:
        return f"未回答を埋めた上で、{hint}"
    return hint


def pick_next_focus_axis(axis_scores: list[AxisScoreResult]) -> Optional[dict[str, str]]:
    if not axis_scores:
        return None
    candidates = [a for a in axis_scores if a.score < 7 or a.missing > 0]
    if not candidates:
        candidates = axis_scores
    sorted_axes = sorted(candidates, key=lambda a: (a.score, -a.missing))
    target = sorted_axes[0]
    reason = (
        f"{target.name}の質問がまだ{target.missing}件未回答です。"
        if target.missing
        else f"{target.name}のスコアが{target.score:.1f}点と低めです。"
    )
    return {
        "axis_code": target.code,
        "axis_name": target.name,
        "reason": reason,
        "message": target.next_step,
    }


async def calculate_axis_scores(
    session: AsyncSession,
    user_id: int,
    answers: dict[str, bool | None],
    axis_meta: dict[str, dict[str, str | int]],
) -> list[AxisScoreResult]:
    axis_question_map = _build_axis_question_map()
    checkpoints = _build_axis_checkpoints(axis_question_map)
    results: list[AxisScoreResult] = []

    for axis_code in AXIS_ORDER:
        question_codes = axis_question_map.get(axis_code, [])
        cp_questions = checkpoints.get(axis_code, [])
        if not cp_questions:
            continue

        values = [_checkpoint_value(answers.get(q)) for q in cp_questions]
        score = round((sum(values) / len(values)) * 10, 1) if values else 0.0
        answered = sum(1 for q in question_codes if answers.get(q) is not None)
        missing = max(len(question_codes) - answered, 0)
        name = (
            axis_meta.get(axis_code, {}).get("name")
            or AXIS_DEFAULTS.get(axis_code)
            or axis_code
        )
        results.append(
            AxisScoreResult(
                code=axis_code,
                name=str(name),
                score=score,
                ok_line=OK_LINE,
                growth_zone=GROWTH_ZONE,
                answered=answered,
                total_questions=len(question_codes),
                missing=missing,
                comment=_comment_for_axis(score, missing),
                next_step=_next_step_for_axis(axis_code, missing),
            )
        )

    await _persist_axis_scores(session, user_id, results, axis_meta)
    return results


async def _persist_axis_scores(
    session: AsyncSession,
    user_id: int,
    axis_scores: Iterable[AxisScoreResult],
    axis_meta: dict[str, dict[str, str | int]],
) -> None:
    existing_result = await session.execute(
        select(AxisScore).where(AxisScore.user_id == user_id)
    )
    existing_map = {row.axis_id: row for row in existing_result.scalars()}

    for axis_score in axis_scores:
        axis_id = axis_meta.get(axis_score.code, {}).get("id")
        if axis_id is None:
            continue
        existing = existing_map.get(axis_id)
        completion_ratio = (
            axis_score.answered / axis_score.total_questions
            if axis_score.total_questions
            else 0
        )
        if existing:
            existing.score = axis_score.score
            existing.level1_completion_ratio = completion_ratio
            existing.level2_completion_ratio = completion_ratio
            existing.calculated_at = datetime.utcnow()
        else:
            session.add(
                AxisScore(
                    user_id=user_id,
                    axis_id=axis_id,
                    score=axis_score.score,
                    level1_completion_ratio=completion_ratio,
                    level2_completion_ratio=completion_ratio,
                    calculated_at=datetime.utcnow(),
                )
            )
    await session.commit()


def summarize_concept_text(latest_story: str | None) -> dict[str, str]:
    if latest_story:
        lines = [line.strip() for line in latest_story.splitlines() if line.strip()]
        title = lines[0][:60] if lines else "現在のコンセプト"
        description = " ".join(lines[1:]) if len(lines) > 1 else latest_story
    else:
        title = "現在のコンセプト"
        description = "簡易シミュレーションや質問の回答からコンセプトを整備していきましょう。"
    return {"title": title, "description": description}
