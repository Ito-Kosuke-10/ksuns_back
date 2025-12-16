import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.api.auth import get_current_user
from app.config.concept_questions import CONCEPT_QUESTIONS
from app.config.funding_plan_questions import FUNDING_PLAN_QUESTIONS
from app.config.interior_exterior_questions import INTERIOR_EXTERIOR_QUESTIONS
from app.config.location_questions import LOCATION_QUESTIONS
from app.config.marketing_questions import MARKETING_QUESTIONS
from app.config.menu_questions import MENU_QUESTIONS
from app.config.operation_questions import OPERATION_QUESTIONS
from app.config.revenue_forecast_questions import REVENUE_FORECAST_QUESTIONS
from app.core.db import get_session
from app.models.axis import PlanningAxis
from app.models.concept_answer import ConceptAnswer
from app.models.funding_plan_answer import FundingPlanAnswer
from app.models.interior_exterior_answer import InteriorExteriorAnswer
from app.models.location_answer import LocationAnswer
from app.models.marketing_answer import MarketingAnswer
from app.models.menu_answer import MenuAnswer
from app.models.notes import OwnerNote, StoreStory
from app.models.operation_answer import OperationAnswer
from app.models.revenue_forecast_answer import RevenueForecastAnswer
from app.schemas.auth import UserInfo
from app.schemas.dashboard import (
    AxisSummary,
    DashboardResponse,
    DetailProgress,
    NextFocus,
    OwnerNoteRequest,
    OwnerNoteResponse,
)
from app.services.detail_questions import (
    calculate_axis_scores,
    calculate_detail_progress,
    fetch_axis_meta,
    fetch_detail_answers,
    summarize_concept_text,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> DashboardResponse:
    try:
        # 1. まずdetail_questionsのデータからレーダーチャートを作成（ベーススコア）
        axis_meta = await fetch_axis_meta(session)
        detail_answers = await fetch_detail_answers(session, current_user.id)
        axis_scores_raw = await calculate_axis_scores(
            session, current_user.id, detail_answers, axis_meta
        )
        
        # AxisScoreResultをAxisSummaryに変換して辞書化（軸コードをキーに）
        # 注意: detail_questionsでは"equipment"を使用するが、planning_axesでは"interior_exterior"を使用
        # そのため、両方のキーでマッピングを作成
        base_scores_dict = {}
        for score in axis_scores_raw:
            axis_summary = AxisSummary(
                code=score.code,
                name=score.name,
                score=score.score,
                ok_line=score.ok_line,
                growth_zone=score.growth_zone,
                comment=score.comment,
                next_step=score.next_step,
                answered=score.answered,
                total_questions=score.total_questions,
                missing=score.missing,
            )
            base_scores_dict[score.code] = axis_summary
            # "equipment"と"interior_exterior"の互換性マッピング
            if score.code == "equipment":
                base_scores_dict["interior_exterior"] = axis_summary
            elif score.code == "interior_exterior":
                base_scores_dict["equipment"] = axis_summary
        
        # 2. Deep Questionsの完了カード数に基づいてスコアを上書き
        # 軸のマッピング（軸コード -> (Answerモデル, 質問定義辞書)）
        axis_mapping = {
            "concept": (ConceptAnswer, CONCEPT_QUESTIONS),
            "revenue_forecast": (RevenueForecastAnswer, REVENUE_FORECAST_QUESTIONS),
            "funds": (FundingPlanAnswer, FUNDING_PLAN_QUESTIONS),
            "operation": (OperationAnswer, OPERATION_QUESTIONS),
            "location": (LocationAnswer, LOCATION_QUESTIONS),
            "interior_exterior": (InteriorExteriorAnswer, INTERIOR_EXTERIOR_QUESTIONS),
            "equipment": (InteriorExteriorAnswer, INTERIOR_EXTERIOR_QUESTIONS),  # 旧コード名との互換性
            "marketing": (MarketingAnswer, MARKETING_QUESTIONS),
            "menu": (MenuAnswer, MENU_QUESTIONS),
        }
        
        # 軸のメタデータを取得
        try:
            axis_meta_result = await session.execute(
                select(PlanningAxis).order_by(PlanningAxis.display_order)
            )
            axis_list = list(axis_meta_result.scalars())
            axis_meta_dict = {axis.code: axis for axis in axis_list}
        except SQLAlchemyError as e:
            logger.warning(f"planning_axesテーブルの取得に失敗: {e}")
            axis_list = []
            axis_meta_dict = {}
        
        # 処理する軸の順序を決定（planning_axesテーブルの順序に従う）
        # 軸コードの正規化マッピング（detail_questionsの"equipment"を"interior_exterior"にマッピング）
        code_normalization = {
            "equipment": "interior_exterior",
            "interior_exterior": "interior_exterior",
        }
        
        axis_order = []
        # まず、planning_axesテーブルから軸の順序を取得
        for axis in axis_list:
            normalized_code = code_normalization.get(axis.code, axis.code)
            if normalized_code in axis_mapping or normalized_code in base_scores_dict or axis.code in base_scores_dict:
                axis_order.append(axis.code)
        
        # planning_axesにない軸は、base_scores_dictまたはaxis_mappingの順序で追加
        # ただし、既にaxis_orderに含まれている軸（正規化後のコードで）は追加しない
        existing_normalized = {code_normalization.get(a, a) for a in axis_order}
        for axis_code in list(base_scores_dict.keys()) + list(axis_mapping.keys()):
            normalized = code_normalization.get(axis_code, axis_code)
            if normalized not in existing_normalized:
                # 正規化後のコードが既に存在する場合は、元のコードを追加
                # ただし、interior_exteriorとequipmentの場合は、interior_exteriorを優先
                if normalized == "interior_exterior":
                    # interior_exteriorが既に存在するか確認
                    if "interior_exterior" not in axis_order:
                        axis_order.append("interior_exterior")
                        existing_normalized.add("interior_exterior")
                elif axis_code not in axis_order:
                    axis_order.append(axis_code)
                    existing_normalized.add(normalized)

        # 各軸のスコアを計算（Deep Questionsの完了カード数で上書き）
        axis_scores = []
        ok_line = 5.0
        growth_zone = 6.0

        for axis_code in axis_order:
            # ベーススコアを取得（detail_questionsから）
            # "equipment"と"interior_exterior"の互換性を考慮
            base_score = base_scores_dict.get(axis_code)
            if not base_score:
                # "equipment"の場合は"interior_exterior"を、その逆も試す
                if axis_code == "equipment":
                    base_score = base_scores_dict.get("interior_exterior")
                elif axis_code == "interior_exterior":
                    base_score = base_scores_dict.get("equipment")
            
            # Deep Questionsの回答カード数を取得
            deep_questions_score = None
            answered_cards = 0
            total_questions = 0
            # "equipment"と"interior_exterior"の両方をチェック
            # planning_axesでは"interior_exterior"、detail_questionsでは"equipment"を使用
            deep_axis_code = axis_code
            if axis_code == "equipment":
                deep_axis_code = "interior_exterior"
            elif axis_code == "interior_exterior":
                deep_axis_code = "interior_exterior"
            
            # ========== デバッグログ: ループ処理の入り口 ==========
            print(f"\n{'='*80}")
            print(f"[DEBUG] ループ処理開始: axis_code='{axis_code}', deep_axis_code='{deep_axis_code}'")
            print(f"[DEBUG] deep_axis_codeの型: {type(deep_axis_code)}")
            print(f"[DEBUG] deep_axis_codeの長さ: {len(deep_axis_code)}")
            print(f"[DEBUG] deep_axis_codeのrepr: {repr(deep_axis_code)}")
            
            # ========== デバッグログ: axis_mappingのキー一覧 ==========
            print(f"[DEBUG] axis_mappingのすべてのキー: {list(axis_mapping.keys())}")
            print(f"[DEBUG] deep_axis_code in axis_mapping: {deep_axis_code in axis_mapping}")
            if deep_axis_code in axis_mapping:
                print(f"[DEBUG] ✅ deep_axis_code '{deep_axis_code}' は axis_mapping に存在します")
            else:
                print(f"[DEBUG] ❌ deep_axis_code '{deep_axis_code}' は axis_mapping に存在しません")
                # 類似キーを探す
                similar_keys = [k for k in axis_mapping.keys() if "interior" in k.lower() or "exterior" in k.lower() or "equipment" in k.lower()]
                print(f"[DEBUG] 類似キー（interior/exterior/equipmentを含む）: {similar_keys}")
            
            if deep_axis_code in axis_mapping:
                AnswerModel, questions_dict = axis_mapping[deep_axis_code]
                total_questions = len(questions_dict)
                
                print(f"[DEBUG] AnswerModel: {AnswerModel}")
                print(f"[DEBUG] questions_dictのキー数: {len(questions_dict)}")
                print(f"[DEBUG] total_questions: {total_questions}")
                
                # ========== 内装外装専用の激しいデバッグログ ==========
                if deep_axis_code == "interior_exterior":
                    print(f"\n{'#'*80}")
                    print(f"[DEBUG INTERIOR_EXTERIOR] 内装外装の処理を開始します")
                    print(f"[DEBUG INTERIOR_EXTERIOR] current_user.id: {current_user.id}")
                    print(f"[DEBUG INTERIOR_EXTERIOR] AnswerModel.__tablename__: {AnswerModel.__tablename__}")
                
                try:
                    # ========== デバッグログ: フィルタなしの全件数 ==========
                    all_count_result = await session.execute(
                        select(func.count(AnswerModel.id))
                    )
                    all_count = all_count_result.scalar() or 0
                    print(f"[DEBUG] フィルタなしの全件数: {all_count}")
                    
                    if deep_axis_code == "interior_exterior":
                        print(f"[DEBUG INTERIOR_EXTERIOR] フィルタなしの全件数: {all_count}")
                    
                    # 回答があるカード数（chat_historyが空でない、またはsummaryがある、またはis_completed=True）を取得
                    # まず、すべての回答レコードを取得
                    all_answers_result = await session.execute(
                        select(AnswerModel).where(
                            AnswerModel.user_id == current_user.id
                        )
                    )
                    all_answers = all_answers_result.scalars().all()
                    
                    # ========== デバッグログ: ユーザーでフィルタした後の件数 ==========
                    user_filtered_count = len(all_answers)
                    print(f"[DEBUG] ユーザー({current_user.id})でフィルタした後の件数: {user_filtered_count}")
                    
                    if deep_axis_code == "interior_exterior":
                        print(f"[DEBUG INTERIOR_EXTERIOR] ユーザー({current_user.id})でフィルタした後の件数: {user_filtered_count}")
                        print(f"[DEBUG INTERIOR_EXTERIOR] 取得したレコードの詳細:")
                        for idx, answer in enumerate(all_answers):
                            print(f"  [{idx}] card_id={answer.card_id}, "
                                  f"is_completed={answer.is_completed}, "
                                  f"chat_history_len={len(answer.chat_history) if answer.chat_history else 0}, "
                                  f"has_summary={bool(answer.summary)}")
                    
                    # 回答があるカードをカウント（chat_historyが空でない、またはsummaryがある、またはis_completed=True）
                    answered_cards = sum(
                        1 for answer in all_answers
                        if (
                            (answer.chat_history and len(answer.chat_history) > 0) or
                            (answer.summary and len(answer.summary) > 0) or
                            answer.is_completed
                        )
                    )
                    
                    # ========== デバッグログ: 最終的な計算式 ==========
                    print(f"[DEBUG] answered_cards (分子): {answered_cards}")
                    print(f"[DEBUG] total_questions (分母): {total_questions}")
                    
                    if deep_axis_code == "interior_exterior":
                        print(f"[DEBUG INTERIOR_EXTERIOR] answered_cards (分子): {answered_cards}")
                        print(f"[DEBUG INTERIOR_EXTERIOR] total_questions (分母): {total_questions}")
                        print(f"[DEBUG INTERIOR_EXTERIOR] 計算式: ({answered_cards} / {total_questions}) * 10")
                    
                    # 回答カード数が1つ以上ある場合は、Deep Questionsのスコアで上書き
                    if answered_cards > 0 and total_questions > 0:
                        deep_questions_score = round((answered_cards / total_questions) * 10, 1)
                        print(f"[DEBUG] 計算結果: deep_questions_score = {deep_questions_score}")
                        
                        if deep_axis_code == "interior_exterior":
                            print(f"[DEBUG INTERIOR_EXTERIOR] ✅ 計算結果: deep_questions_score = {deep_questions_score}")
                            print(f"{'#'*80}\n")
                    else:
                        print(f"[DEBUG] ⚠️ スコア計算をスキップ: answered_cards={answered_cards}, total_questions={total_questions}")
                        
                        if deep_axis_code == "interior_exterior":
                            print(f"[DEBUG INTERIOR_EXTERIOR] ⚠️ スコア計算をスキップ")
                            print(f"[DEBUG INTERIOR_EXTERIOR] answered_cards={answered_cards}, total_questions={total_questions}")
                            print(f"{'#'*80}\n")
                except SQLAlchemyError as e:
                    logger.warning(f"{axis_code}軸のDeep Questions回答数取得に失敗: {e}")
                    print(f"[DEBUG] ❌ SQLAlchemyError: {e}")
                    
                    if deep_axis_code == "interior_exterior":
                        print(f"[DEBUG INTERIOR_EXTERIOR] ❌ SQLAlchemyError: {e}")
                        print(f"{'#'*80}\n")
                except Exception as e:
                    logger.error(f"{axis_code}軸のDeep Questions処理中に予期しないエラー: {e}", exc_info=True)
                    print(f"[DEBUG] ❌ 予期しないエラー: {e}")
                    
                    if deep_axis_code == "interior_exterior":
                        print(f"[DEBUG INTERIOR_EXTERIOR] ❌ 予期しないエラー: {e}")
                        import traceback
                        print(f"[DEBUG INTERIOR_EXTERIOR] トレースバック:\n{traceback.format_exc()}")
                        print(f"{'#'*80}\n")
            else:
                print(f"[DEBUG] ⚠️ deep_axis_code '{deep_axis_code}' が axis_mapping に存在しないため、スキップします")
            
            print(f"{'='*80}\n")
            
            # スコアの決定：Deep Questionsの回答カードがある場合は上書き、なければベーススコアを使用
            if deep_questions_score is not None:
                score = deep_questions_score
                answered = answered_cards
                missing = max(total_questions - answered_cards, 0)
                
                if deep_axis_code == "interior_exterior":
                    print(f"[DEBUG INTERIOR_EXTERIOR] ✅ deep_questions_scoreを使用: score={score}, answered={answered}, missing={missing}")
            elif base_score:
                score = base_score.score
                answered = base_score.answered
                missing = base_score.missing
                
                if deep_axis_code == "interior_exterior":
                    print(f"[DEBUG INTERIOR_EXTERIOR] ⚠️ base_scoreを使用: score={score}, answered={answered}, missing={missing}")
            else:
                # どちらもない場合は0点
                score = 0.0
                answered = 0
                missing = 0
                
                if deep_axis_code == "interior_exterior":
                    print(f"[DEBUG INTERIOR_EXTERIOR] ⚠️ デフォルト値を使用: score={score}, answered={answered}, missing={missing}")
            
            # 軸の名前を取得
            axis = axis_meta_dict.get(axis_code)
            axis_name = axis.name if axis else (base_score.name if base_score else axis_code)
            
            # コメントとnext_step
            if base_score and deep_questions_score is None:
                # detail_questionsのコメントを使用
                comment = base_score.comment
                next_step = base_score.next_step
            else:
                # Deep Questionsまたは新規軸の場合
                if missing > 0:
                    comment = f"未回答が{missing}件あります。質問に回答を進めましょう。"
                    next_step = f"{axis_name}の質問に回答を進めましょう。"
                elif score >= 8.0:
                    comment = "順調です。このまま強みを仕上げましょう。"
                    next_step = f"{axis_name}の内容をさらに深掘りしましょう。"
                elif score >= 5.0:
                    comment = "OKライン付近です。弱い部分を1つ補強しましょう。"
                    next_step = f"{axis_name}の未完了項目を確認しましょう。"
                else:
                    comment = "まだ余白があります。基本の質問に回答することから始めましょう。"
                    next_step = f"{axis_name}の質問に回答を始めましょう。"
            
            # total_questionsの決定
            if deep_questions_score is not None:
                total_questions_for_axis = total_questions
            elif base_score:
                total_questions_for_axis = base_score.total_questions
            else:
                total_questions_for_axis = 0
            
            final_axis_summary = AxisSummary(
                code=axis_code,
                name=axis_name,
                score=score,
                ok_line=ok_line,
                growth_zone=growth_zone,
                comment=comment,
                next_step=next_step,
                answered=answered,
                total_questions=total_questions_for_axis,
                missing=missing,
            )
            
            if deep_axis_code == "interior_exterior":
                print(f"[DEBUG INTERIOR_EXTERIOR] 📊 最終的なAxisSummary:")
                print(f"  code={final_axis_summary.code}")
                print(f"  name={final_axis_summary.name}")
                print(f"  score={final_axis_summary.score}")
                print(f"  answered={final_axis_summary.answered}")
                print(f"  total_questions={final_axis_summary.total_questions}")
                print(f"  missing={final_axis_summary.missing}")
            
            axis_scores.append(final_axis_summary)

        # StoreStoryを取得
        try:
            story_result = await session.execute(
                select(StoreStory)
                .where(StoreStory.user_id == current_user.id)
                .order_by(desc(StoreStory.created_at))
                .limit(1)
            )
            story = story_result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.warning(f"StoreStoryの取得に失敗: {e}")
            story = None

        # OwnerNoteを取得
        try:
            note_result = await session.execute(
                select(OwnerNote).where(OwnerNote.user_id == current_user.id)
            )
            note = note_result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.warning(f"OwnerNoteの取得に失敗: {e}")
            note = None

        # Concept summary
        concept = summarize_concept_text(story.content if story else None)

        # Next focus（スコアが最も低い軸、または未回答が多い軸）
        next_focus = None
        if axis_scores:
            # 未回答が多い軸を優先、次にスコアが低い軸
            sorted_axes = sorted(
                axis_scores,
                key=lambda a: (a.missing, -a.score),
                reverse=True
            )
            target = sorted_axes[0]
            if target.missing > 0 or target.score < 7.0:
                next_focus = NextFocus(
                    axis_code=target.code,
                    axis_name=target.name,
                    reason=(
                        f"{target.missing}件が未回答です。"
                        if target.missing > 0
                        else f"{target.name}のスコアが{target.score:.1f}点と低めです。"
                    ),
                    message=target.next_step,
                )

        # Detail progress（detail_questionsの進捗を返す）
        detail_progress_dict = calculate_detail_progress(detail_answers)
        detail_progress = DetailProgress(
            answered=detail_progress_dict.get("answered", 0),
            total=detail_progress_dict.get("total", 0),
        )

        return DashboardResponse(
            concept=concept,
            axes=axis_scores,
            detail_progress=detail_progress,
            next_focus=next_focus,
            ok_line=ok_line,
            growth_zone=growth_zone,
            owner_note=note.content if note else "",
            latest_store_story=story.content if story else "",
            user_email=current_user.email,
        )
    except Exception as e:
        logger.error(f"ダッシュボード取得エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ダッシュボードの取得に失敗しました: {str(e)}"
        )


@router.put("/owner-note", response_model=OwnerNoteResponse)
async def upsert_owner_note(
    payload: OwnerNoteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> OwnerNoteResponse:
    result = await session.execute(
        select(OwnerNote).where(OwnerNote.user_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note:
        note.content = payload.content
    else:
        note = OwnerNote(user_id=current_user.id, content=payload.content)
        session.add(note)
    await session.commit()
    await session.refresh(note)
    return OwnerNoteResponse(owner_note=note.content)
