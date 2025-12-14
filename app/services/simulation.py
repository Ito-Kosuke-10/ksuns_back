"""Simulation service for simple simulation functionality."""
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simple_simulation import (
    FundsCommentCategory,
    SimpleSimulationAnswer,
    SimpleSimulationResult,
    SimpleSimulationSession,
    SimulationStatus,
)
from app.models.axis import PlanningAxis, AxisScore
from app.schemas.simulation import FinancialForecast, SimulationResultResponse, SubmitSimulationRequest


# Required fields for store profile
REQUIRED_FIELDS = ["main_genre", "sub_genre", "seats", "price_point", "business_hours", "location"]

# ========================================
# ラベルマッピング定義
# ========================================

MAIN_GENRE_LABELS = {
    "izakaya": "居酒屋",
    "ramen": "ラーメン店",
    "cafe": "カフェ",
    "bar": "バー",
    "yakiniku": "焼肉店",
    "sushi": "寿司店",
    "italian": "イタリアン",
    "french": "フレンチ",
    "chinese": "中華料理店",
    "japanese": "和食店",
    "curry": "カレー店",
    "udon": "うどん店",
    "soba": "そば店",
    "takoyaki": "たこ焼き店",
    "okonomiyaki": "お好み焼き店",
    "gyudon": "牛丼店",
    "teishoku": "定食屋",
    "bakery": "ベーカリー",
    "sweets": "スイーツ店",
    "undecided_main": "飲食店",
}

SUB_GENRE_LABELS = {
    "izakaya_taishu": "大衆",
    "izakaya_modern": "モダン",
    "izakaya_standing": "立ち飲み",
    "ramen_tonkotsu": "豚骨系",
    "ramen_shoyu": "醤油系",
    "ramen_miso": "味噌系",
    "cafe_specialty": "スペシャルティコーヒー",
    "cafe_casual": "カジュアル",
    "bar_authentic": "本格派",
    "bar_casual": "カジュアル",
    "undecided_sub": "",
}

LOCATION_LABELS = {
    "near_station": "駅近",
    "shopping_street": "商店街",
    "office_area": "オフィス街",
    "residential": "住宅街",
    "tourist_area": "観光地",
    "roadside": "ロードサイド",
    "underground": "地下",
    "building_upper": "ビル上階",
}

TARGET_CUSTOMER_LABELS = {
    "near_station": "サラリーマン向け",
    "shopping_street": "地域密着型",
    "office_area": "ビジネスパーソン向け",
    "residential": "ファミリー向け",
    "tourist_area": "観光客向け",
    "roadside": "ドライバー向け",
    "underground": "通勤客向け",
    "building_upper": "隠れ家的",
}

# ========================================
# コンセプトサブコメント定義 (20-30文字)
# ========================================

CONCEPT_SUB_COMMENTS = {
    "izakaya": {
        "near_station": "仕事帰りにふらっと立ち寄れる憩いの場",
        "shopping_street": "地元に愛される昔ながらの味わい",
        "office_area": "ランチからディナーまで幅広く対応",
        "residential": "家族で楽しめるアットホームな空間",
        "tourist_area": "日本の食文化を体験できる場所",
        "default": "気軽に楽しめる居心地の良い空間",
    },
    "ramen": {
        "near_station": "忙しい毎日に寄り添う一杯を提供",
        "shopping_street": "地域で愛される味を目指して",
        "office_area": "ランチタイムの強い味方",
        "residential": "家族連れも安心の明るい店内",
        "tourist_area": "本場の味を観光客にお届け",
        "default": "こだわりの一杯を提供します",
    },
    "cafe": {
        "near_station": "通勤前後のひとときを彩る空間",
        "shopping_street": "お買い物の合間にほっと一息",
        "office_area": "仕事の合間のリフレッシュに",
        "residential": "地域のコミュニティスペースとして",
        "tourist_area": "観光の思い出に残るカフェ体験",
        "default": "くつろぎの時間を提供します",
    },
    "default": {
        "default": "お客様に喜ばれる店舗を目指します",
    },
}

# ========================================
# 開店にあたっての留意事項
# ========================================

OPENING_NOTES = {
    "near_station": """【立地について】
駅近物件は家賃が高めですが、集客力があります。競合店との差別化が重要です。

【営業時間】
通勤時間帯（朝・夕方）の集客を意識したオペレーションを検討してください。

【ターゲット】
サラリーマンやOLが主要ターゲットとなります。回転率を意識した席配置が効果的です。""",

    "shopping_street": """【立地について】
商店街は地域密着型の営業が求められます。常連客の獲得が成功の鍵です。

【営業時間】
商店街の営業時間に合わせた運営を検討してください。

【ターゲット】
地域住民との関係構築が重要です。イベントや季節メニューで話題作りを。""",

    "office_area": """【立地について】
オフィス街はランチ需要が高く、回転率重視の運営が求められます。

【営業時間】
平日ランチの効率化と、夜の宴会需要の両立がポイントです。

【ターゲット】
ビジネスパーソン向けのスピーディーなサービスを心がけてください。""",

    "residential": """【立地について】
住宅街は家族連れやシニア層が主要ターゲットとなります。

【営業時間】
土日祝日の集客が見込めます。平日の集客戦略も検討してください。

【ターゲット】
地域に根差した営業で、口コミでの評判が重要です。""",

    "tourist_area": """【立地について】
観光地は季節変動が大きいため、閑散期対策が必要です。

【営業時間】
観光客の動線を意識した営業時間の設定を検討してください。

【ターゲット】
SNS映えするメニューや内装で、口コミ拡散を狙いましょう。""",

    "default": """【立地について】
立地特性を分析し、ターゲット顧客を明確にしましょう。

【営業時間】
ターゲット層の生活リズムに合わせた営業時間を設定してください。

【ターゲット】
競合分析を行い、差別化ポイントを明確にしましょう。""",
}


def calculate_axis_scores(answers: dict) -> dict[str, float]:
    """Calculate axis scores from simulation answers."""
    scores = {
        "concept": 0.0,
        "funds": 0.0,
        "compliance": 0.0,
        "operation": 0.0,
        "location": 0.0,
        "interior": 0.0,
        "marketing": 0.0,
        "menu": 0.0,
    }

    main_genre = answers.get("main_genre", [])
    if main_genre and main_genre[0] != "undecided_main":
        scores["concept"] = 5.0

    sub_genre = answers.get("sub_genre", [])
    if sub_genre:
        scores["concept"] += 2.5

    seats = answers.get("seats", [])
    if seats:
        scores["operation"] = 5.0

    price_point = answers.get("price_point", [])
    if price_point:
        scores["funds"] = 5.0

    location = answers.get("location", [])
    if location:
        scores["location"] = 5.0

    if scores["compliance"] == 0.0:
        scores["compliance"] = 1.0

    return scores


def generate_concept_name(profile: dict) -> str:
    """Generate concept name from profile selections."""
    location_code = profile.get("location", "")
    main_genre_code = profile.get("main_genre", "")
    sub_genre_code = profile.get("sub_genre", "")

    # Get labels
    location_label = LOCATION_LABELS.get(location_code, "")
    target_label = TARGET_CUSTOMER_LABELS.get(location_code, "")
    main_genre_label = MAIN_GENRE_LABELS.get(main_genre_code, "飲食店")
    sub_genre_label = SUB_GENRE_LABELS.get(sub_genre_code, "")

    # Build concept name
    parts = []
    if location_label:
        parts.append(location_label)
    if target_label:
        parts.append(target_label)
    if sub_genre_label:
        parts.append(sub_genre_label)
    parts.append(main_genre_label)

    return "の".join(parts) if len(parts) > 1 else main_genre_label


def generate_concept_sub_comment(profile: dict) -> str:
    """Generate 20-30 character sub-comment for concept."""
    main_genre_code = profile.get("main_genre", "default")
    location_code = profile.get("location", "default")

    genre_comments = CONCEPT_SUB_COMMENTS.get(main_genre_code, CONCEPT_SUB_COMMENTS["default"])
    comment = genre_comments.get(location_code, genre_comments.get("default", "お客様に喜ばれる店舗を目指します"))

    return comment


def generate_opening_notes(profile: dict) -> str:
    """Generate opening notes based on location."""
    location_code = profile.get("location", "default")
    return OPENING_NOTES.get(location_code, OPENING_NOTES["default"])


def calculate_financial_forecast(profile: dict) -> tuple[FinancialForecast, FundsCommentCategory, str]:
    """Calculate detailed financial forecast."""
    seats = profile.get("seats", 0)
    price_point = profile.get("price_point", 0)
    location_code = profile.get("location", "")

    if isinstance(seats, str):
        seats = int(seats) if seats.isdigit() else 20
    if isinstance(price_point, str):
        price_point = int(price_point) if price_point.isdigit() else 3000

    # 想定月商（70%稼働率）
    monthly_sales = int(seats * price_point * 30 * 0.7)

    # 推定家賃（立地による）
    rent_multiplier = {
        "near_station": 1.5,
        "office_area": 1.4,
        "tourist_area": 1.3,
        "shopping_street": 1.0,
        "residential": 0.8,
        "roadside": 0.7,
    }
    base_rent = seats * 15000  # 1席あたり1.5万円
    estimated_rent = int(base_rent * rent_multiplier.get(location_code, 1.0))

    # 原価率（業態による）
    cost_ratio = 30.0  # 標準30%

    # 人件費率
    labor_cost_ratio = 25.0  # 標準25%

    # 利益率計算
    other_costs_ratio = 15.0  # その他経費15%
    rent_ratio = (estimated_rent / monthly_sales * 100) if monthly_sales > 0 else 10.0
    profit_ratio = max(0, 100 - cost_ratio - labor_cost_ratio - other_costs_ratio - rent_ratio)

    # 損益分岐売上
    fixed_costs = estimated_rent + (monthly_sales * 0.15)  # 家賃 + その他固定費
    variable_cost_ratio = (cost_ratio + labor_cost_ratio) / 100
    break_even_sales = int(fixed_costs / (1 - variable_cost_ratio)) if variable_cost_ratio < 1 else 0

    # 資金計画コメント
    if profit_ratio >= 15:
        category = FundsCommentCategory.RELAXED
        text = "収支バランスが良好です。安定した経営が期待できます。"
    elif profit_ratio >= 5:
        category = FundsCommentCategory.TIGHT
        text = "収支は標準的です。コスト管理を意識した運営が必要です。"
    else:
        category = FundsCommentCategory.TIGHT
        text = "収支が厳しい可能性があります。価格設定や経費の見直しを検討してください。"

    forecast = FinancialForecast(
        monthly_sales=monthly_sales,
        estimated_rent=estimated_rent,
        cost_ratio=round(cost_ratio, 1),
        labor_cost_ratio=round(labor_cost_ratio, 1),
        profit_ratio=round(profit_ratio, 1),
        break_even_sales=break_even_sales,
        funds_comment_category=category.value,
        funds_comment_text=text,
    )

    return forecast, category, text


def _build_store_profile(answers: dict) -> dict:
    """Build store profile from answers."""
    profile = {}
    for key in REQUIRED_FIELDS:
        value = answers.get(key, [])
        if value:
            profile[key] = value[0] if isinstance(value, list) else value
    return profile


async def _get_axis_id_map(db: AsyncSession) -> dict[str, int]:
    """Get mapping of axis codes to axis IDs."""
    result = await db.execute(select(PlanningAxis))
    axes = result.scalars().all()
    return {axis.code: axis.id for axis in axes}


async def process_simulation_submission(
    db: AsyncSession,
    payload: SubmitSimulationRequest,
    user_id: Optional[int],
) -> SimulationResultResponse:
    """Process simulation submission and return results."""

    # Convert answers to dict
    answers_dict = {item.question_code: item.values for item in payload.answers}

    # Build store profile
    profile = _build_store_profile(answers_dict)

    # Calculate scores
    axis_scores = calculate_axis_scores(answers_dict)

    # Generate concept name and sub-comment
    concept_name = generate_concept_name(profile)
    concept_sub_comment = generate_concept_sub_comment(profile)

    # Calculate financial forecast
    financial_forecast, funds_category, funds_text = calculate_financial_forecast(profile)

    # Generate opening notes
    opening_notes = generate_opening_notes(profile)

    # Build response
    def build_response(session_id: int) -> SimulationResultResponse:
        return SimulationResultResponse(
            session_id=session_id,
            axis_scores=axis_scores,
            concept_name=concept_name,
            concept_sub_comment=concept_sub_comment,
            financial_forecast=financial_forecast,
            opening_notes=opening_notes,
            # 後方互換性フィールド
            funds_comment_category=funds_category.value,
            funds_comment_text=funds_text,
            store_story_text="",
            concept_title=MAIN_GENRE_LABELS.get(profile.get("main_genre", ""), ""),
            concept_detail=SUB_GENRE_LABELS.get(profile.get("sub_genre", ""), ""),
            funds_summary=funds_text,
            monthly_sales=financial_forecast.monthly_sales,
        )

    # If no user and no guest token, return without saving
    if user_id is None and not payload.guest_session_token:
        return build_response(0)

    # Guest without token - require token
    if user_id is None and payload.guest_session_token == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guest session token is required for saving results",
        )

    # Check if session with same guest_session_token already exists
    session_obj = None
    if payload.guest_session_token:
        result = await db.execute(
            select(SimpleSimulationSession).where(
                SimpleSimulationSession.guest_session_token == payload.guest_session_token
            )
        )
        session_obj = result.scalar_one_or_none()

    if session_obj:
        # Update existing session
        await db.execute(
            delete(SimpleSimulationAnswer).where(
                SimpleSimulationAnswer.session_id == session_obj.id
            )
        )
        await db.execute(
            delete(SimpleSimulationResult).where(
                SimpleSimulationResult.session_id == session_obj.id
            )
        )
        session_obj.status = SimulationStatus.COMPLETED
        session_obj.user_id = user_id
    else:
        # Create new session
        session_obj = SimpleSimulationSession(
            user_id=user_id,
            guest_session_token=payload.guest_session_token if not user_id else None,
            status=SimulationStatus.COMPLETED,
        )
        db.add(session_obj)
        await db.flush()

    # Save answers
    for item in payload.answers:
        answer = SimpleSimulationAnswer(
            session_id=session_obj.id,
            question_code=item.question_code,
            answer_values={"values": item.values},
        )
        db.add(answer)

    # Save result
    result_obj = SimpleSimulationResult(
        session_id=session_obj.id,
        axis_scores=axis_scores,
        funds_comment_category=funds_category,
        funds_comment_text=funds_text,
        store_story_text="",
    )
    db.add(result_obj)

    # If user is logged in, save axis scores
    if user_id:
        axis_map = await _get_axis_id_map(db)
        for axis_code, score in axis_scores.items():
            if axis_code in axis_map:
                axis_score = AxisScore(
                    user_id=user_id,
                    axis_id=axis_map[axis_code],
                    score=score,
                )
                db.add(axis_score)

    await db.commit()

    return build_response(session_obj.id)


async def attach_session_to_user(
    db: AsyncSession,
    session_id: int,
    user_id: int,
) -> Optional[SimulationResultResponse]:
    """Attach an existing simulation session to a user."""

    # Get session
    result = await db.execute(
        select(SimpleSimulationSession).where(SimpleSimulationSession.id == session_id)
    )
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        return None

    # Update user_id
    session_obj.user_id = user_id

    # Get simulation result
    result = await db.execute(
        select(SimpleSimulationResult).where(SimpleSimulationResult.session_id == session_id)
    )
    sim_result = result.scalar_one_or_none()

    if not sim_result:
        return None

    # Save axis scores for user
    axis_map = await _get_axis_id_map(db)
    for axis_code, score in sim_result.axis_scores.items():
        if axis_code in axis_map:
            axis_score = AxisScore(
                user_id=user_id,
                axis_id=axis_map[axis_code],
                score=score,
            )
            db.add(axis_score)

    await db.commit()

    # Build default financial forecast for attached sessions
    forecast = FinancialForecast(
        monthly_sales=None,
        estimated_rent=None,
        cost_ratio=None,
        labor_cost_ratio=None,
        profit_ratio=None,
        break_even_sales=None,
        funds_comment_category=sim_result.funds_comment_category.value,
        funds_comment_text=sim_result.funds_comment_text or "",
    )

    return SimulationResultResponse(
        session_id=session_id,
        axis_scores=sim_result.axis_scores,
        concept_name="",
        concept_sub_comment="",
        financial_forecast=forecast,
        opening_notes="",
        funds_comment_category=sim_result.funds_comment_category.value,
        funds_comment_text=sim_result.funds_comment_text or "",
        store_story_text=sim_result.store_story_text or "",
        concept_title="",
        concept_detail="",
        funds_summary=sim_result.funds_comment_text or "",
        monthly_sales=None,
    )
