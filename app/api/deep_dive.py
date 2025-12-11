"""
深掘り機能（Deep Dive）のAPIエンドポイント
既存のdeep_questionsとは別の新しいカードベースの深掘り機能
"""
import logging
import traceback
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.api.auth import get_current_user
from app.config.deep_dive_data import DEEP_DIVE_DATA
from app.core.db import get_session
from app.models.axis import PlanningAxis
from app.models.deep_dive import DeepDiveChatLog, DeepDiveProgress, DeepDiveStatus
from app.schemas.auth import UserInfo
from app.schemas.deep_dive import (
    DeepDiveCard,
    DeepDiveChatMessage,
    DeepDiveChatRequest,
    DeepDiveChatResponse,
    DeepDiveCompleteResponse,
    DeepDiveListResponse,
    DeepDiveStep,
)
from app.services.ai_client import answer_question, generate_deep_dive_summary

router = APIRouter(prefix="/deep-dive", tags=["deep-dive"])


@router.get("/test/{axis_code}/list", response_model=DeepDiveListResponse)
async def get_deep_dive_list_test(
    axis_code: str,
    session: AsyncSession = Depends(get_session),
) -> DeepDiveListResponse:
    """
    テスト用エンドポイント（認証なし）
    """
    logger.info(f"TEST: GET /deep-dive/test/{axis_code}/list")
    try:
        # 軸の存在確認と名前取得
        result = await session.execute(select(PlanningAxis).where(PlanningAxis.code == axis_code))
        axis = result.scalar_one_or_none()
        if not axis:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Axis not found")

        # 静的データから該当軸のデータを取得
        axis_data = DEEP_DIVE_DATA.get(axis_code, [])
        
        if not axis_data:
            return DeepDiveListResponse(axis_code=axis_code, axis_name=axis.name, steps=[])

        # テスト用：進捗は空
        progress_map = {}

        # ロック制御なし（テスト用）
        step_completion_map = {step_data["step"]: False for step_data in axis_data}

        # ステップとカードを構築
        steps = []
        for step_data in axis_data:
            step_num = step_data["step"]
            cards = []
            for card_data in step_data["cards"]:
                card_id = card_data["id"]
                progress = progress_map.get(card_id)
                base_status = (
                    progress.status.value if progress else DeepDiveStatus.NOT_STARTED.value
                )
                summary = progress.summary if progress and progress.summary else None

                cards.append(
                    DeepDiveCard(
                        id=card_id,
                        title=card_data["title"],
                        initial_question=card_data["initial_question"],
                        status=base_status,
                        summary=summary,
                    )
                )

            steps.append(
                DeepDiveStep(
                    step=step_data["step"],
                    step_title=step_data["step_title"],
                    cards=cards,
                )
            )

        return DeepDiveListResponse(
            axis_code=axis_code,
            axis_name=axis.name,
            steps=steps,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TEST endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{axis_code}/list", response_model=DeepDiveListResponse)
async def get_deep_dive_list(
    axis_code: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),  # 認証必須
) -> DeepDiveListResponse:
    """
    指定された軸の深掘りカード一覧と進捗を取得
    パフォーマンス最適化: DB一括取得 + メモリ内マージ方式
    """
    try:
        logger.info(f"GET /deep-dive/{axis_code}/list - User ID: {current_user.id}")
        
        # ステップ1: 軸の存在確認と名前取得
        logger.debug(f"Fetching axis: {axis_code}")
        try:
            result = await session.execute(select(PlanningAxis).where(PlanningAxis.code == axis_code))
            axis = result.scalar_one_or_none()
        except Exception as db_error:
            logger.error(f"データベースエラー（PlanningAxis取得）: {db_error}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"データベースエラー: {str(db_error)}"
            )
        
        if not axis:
            logger.warning(f"Axis not found: {axis_code}")
            # 軸が存在しない場合でも、マスタデータがあれば軸名をデフォルト値で返す
            axis_name = axis_code.capitalize() if axis_code else "Unknown"
            if axis_code not in DEEP_DIVE_DATA:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Axis '{axis_code}' not found")
            # マスタデータがある場合は、デフォルト名で続行
            logger.info(f"Axis not in DB but master data exists, using default name: {axis_name}")
        else:
            axis_name = axis.name
            logger.debug(f"Axis found: {axis_name}")

        # ステップ2: マスタデータの存在確認
        if axis_code not in DEEP_DIVE_DATA:
            logger.info(f"No master data for axis: {axis_code}")
            return DeepDiveListResponse(axis_code=axis_code, axis_name=axis_name, steps=[])
        
        steps_data = DEEP_DIVE_DATA[axis_code]
        if not steps_data:
            logger.info(f"Empty master data for axis: {axis_code}")
            return DeepDiveListResponse(axis_code=axis_code, axis_name=axis_name, steps=[])

        # ステップ3: DBから進捗データを1回のクエリで全件取得
        progress_map = {}
        try:
            logger.debug(f"Fetching ALL progress for user_id: {current_user.id}, axis_code: {axis_code}")
            stmt = select(DeepDiveProgress).where(
                DeepDiveProgress.user_id == current_user.id,
                DeepDiveProgress.axis_code == axis_code
            )
            result = await session.execute(stmt)
            all_progress = list(result.scalars().all())
            
            # ステップ4: 辞書化（card_idをキーにしたO(1)検索用）
            progress_map = {p.card_id: p for p in all_progress}
            logger.debug(f"Found {len(all_progress)} progress records, mapped to {len(progress_map)} entries")
        except Exception as e:
            # テーブルが存在しない場合などは進捗なしとして処理
            logger.warning(f"進捗データの取得に失敗しました（テーブルが存在しない可能性）: {e}", exc_info=True)
            # 進捗マップは空のまま（すべてのカードがNOT_STARTEDになる）

        # ステップ5: ロック制御用に各ステップの完了状況を事前計算（メモリ内）
        step_completion_map = {}  # {step_number: all_completed}
        for step in steps_data:
            step_num = step["step"]
            step_cards = step["cards"]
            # このステップのすべてのカードが完了しているか確認
            all_completed = all(
                progress_map.get(card["id"]) is not None
                and progress_map.get(card["id"]).status == DeepDiveStatus.COMPLETED
                for card in step_cards
            )
            step_completion_map[step_num] = all_completed

        # ステップ6: メモリ内マージ（ループ内でDBアクセスは行わない）
        response_steps = []
        for step in steps_data:
            step_num = step["step"]
            response_cards = []
            
            for card in step["cards"]:
                card_id = card["id"]
                
                # 辞書からO(1)で検索（DBアクセスなし）
                prog = progress_map.get(card_id)
                
                # ステータスの安全な取得
                if prog and prog.status:
                    base_status = prog.status.value
                else:
                    base_status = DeepDiveStatus.NOT_STARTED.value
                
                # ロック制御: 前のステップが完了していない場合はロック
                is_locked = False
                if step_num > 1:
                    prev_step = step_num - 1
                    is_locked = not step_completion_map.get(prev_step, False)
                
                # ロックされている場合はstatusを"locked"に、そうでなければ元のstatusを使用
                final_status = "locked" if is_locked else base_status
                
                # サマリーの安全な取得（Noneを許容）
                summary_value = None
                if prog and prog.summary:
                    summary_value = prog.summary
                
                # Pydanticモデルを安全に作成
                try:
                    card_obj = DeepDiveCard(
                        id=card_id,
                        title=card["title"],
                        initial_question=card["initial_question"],
                        status=final_status,
                        summary=summary_value,
                    )
                    response_cards.append(card_obj)
                except Exception as card_error:
                    logger.error(f"カード作成エラー: card_id={card_id}, error={card_error}", exc_info=True)
                    # エラーが発生しても処理を続行（デフォルト値で作成）
                    card_obj = DeepDiveCard(
                        id=card_id,
                        title=card["title"],
                        initial_question=card["initial_question"],
                        status=DeepDiveStatus.NOT_STARTED.value,
                        summary=None,
                    )
                    response_cards.append(card_obj)
            
            response_steps.append(
                DeepDiveStep(
                    step=step["step"],
                    step_title=step["step_title"],
                    cards=response_cards,
                )
            )

        logger.info(f"✅ レスポンス構築完了: {len(response_steps)} steps, {sum(len(s.cards) for s in response_steps)} cards")
        return DeepDiveListResponse(axis_code=axis_code, axis_name=axis_name, steps=response_steps)
        
    except HTTPException:
        raise
    except Exception as e:
        # エラーをコンソールとログの両方に出力（確実に表示されるように）
        error_msg = f"Error in get_deep_dive_list: {e}"
        error_type = type(e).__name__
        error_trace = traceback.format_exc()
        
        # コンソールに出力（stderrに出力して確実に表示）
        import sys
        print("=" * 60, file=sys.stderr, flush=True)
        print("DEEP DIVE API ERROR", file=sys.stderr, flush=True)
        print("=" * 60, file=sys.stderr, flush=True)
        print(f"Error: {error_msg}", file=sys.stderr, flush=True)
        print(f"Type: {error_type}", file=sys.stderr, flush=True)
        print("Traceback:", file=sys.stderr, flush=True)
        print(error_trace, file=sys.stderr, flush=True)
        print("=" * 60, file=sys.stderr, flush=True)
        
        # traceback.print_exc()も実行（確実に表示）
        traceback.print_exc()
        
        # ログにも出力
        logger.error("============== DEEP DIVE API ERROR ==============")
        logger.error(error_msg)
        logger.error(f"Error type: {error_type}")
        logger.error(f"Traceback:\n{error_trace}")
        logger.error("=================================================")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"深掘りデータの取得に失敗しました: {str(e)}"
        )


@router.get("/chat/{card_id}", response_model=DeepDiveChatResponse)
async def get_deep_dive_chat(
    card_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> DeepDiveChatResponse:
    """
    指定されたカードのチャット履歴を取得
    """
    # カード情報を静的データから取得
    card_info = None
    for axis_data in DEEP_DIVE_DATA.values():
        for step_data in axis_data:
            for card_data in step_data["cards"]:
                if card_data["id"] == card_id:
                    card_info = card_data
                    break
            if card_info:
                break
        if card_info:
            break

    if not card_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    # チャット履歴を取得（テーブルが存在しない場合でもエラーにならないように）
    messages = []
    try:
        result = await session.execute(
            select(DeepDiveChatLog)
            .where(DeepDiveChatLog.user_id == current_user.id, DeepDiveChatLog.card_id == card_id)
            .order_by(DeepDiveChatLog.created_at.asc())
        )
        chat_logs = list(result.scalars())
        messages = [
            DeepDiveChatMessage(role=log.role, message=log.message, created_at=log.created_at)
            for log in chat_logs
        ]
    except Exception as e:
        # テーブルが存在しない場合は空のメッセージリストを返す
        logger.warning(f"チャット履歴の取得に失敗しました（テーブルが存在しない可能性）: {e}")

    # 進捗を更新（初回アクセスの場合はIN_PROGRESSに）
    # テーブルが存在しない場合はスキップ
    try:
        progress_result = await session.execute(
            select(DeepDiveProgress).where(
                DeepDiveProgress.user_id == current_user.id,
                DeepDiveProgress.card_id == card_id,
            )
        )
        progress = progress_result.scalar_one_or_none()
        if not progress:
            # カードの軸コードを取得
            axis_code = None
            for ax_code, axis_data in DEEP_DIVE_DATA.items():
                for step_data in axis_data:
                    for card_data in step_data["cards"]:
                        if card_data["id"] == card_id:
                            axis_code = ax_code
                            break
                    if axis_code:
                        break
                if axis_code:
                    break

            if axis_code:
                progress = DeepDiveProgress(
                    user_id=current_user.id,
                    axis_code=axis_code,
                    card_id=card_id,
                    status=DeepDiveStatus.IN_PROGRESS,
                )
                session.add(progress)
                await session.commit()
    except Exception as e:
        # テーブルが存在しない場合は進捗の更新をスキップ
        logger.warning(f"進捗データの更新に失敗しました（テーブルが存在しない可能性）: {e}")

    # 進捗ステータスとサマリーを取得
    status = None
    summary = None
    try:
        progress_result = await session.execute(
            select(DeepDiveProgress).where(
                DeepDiveProgress.user_id == current_user.id,
                DeepDiveProgress.card_id == card_id,
            )
        )
        progress = progress_result.scalar_one_or_none()
        if progress:
            status = progress.status.value
            summary = progress.summary
    except Exception as e:
        logger.warning(f"進捗ステータスの取得に失敗しました: {e}")
    
    return DeepDiveChatResponse(
        card_id=card_id,
        card_title=card_info["title"],
        initial_question=card_info["initial_question"],
        messages=messages,
        status=status,
        summary=summary,
    )


@router.post("/chat/{card_id}", response_model=DeepDiveChatResponse)
async def post_deep_dive_chat(
    card_id: str,
    payload: DeepDiveChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> DeepDiveChatResponse:
    """
    チャットメッセージを送信
    """
    try:
        # カード情報を静的データから取得
        card_info = None
        axis_code = None
        for ax_code, axis_data in DEEP_DIVE_DATA.items():
            for step_data in axis_data:
                for card_data in step_data["cards"]:
                    if card_data["id"] == card_id:
                        card_info = card_data
                        axis_code = ax_code
                        break
                if card_info:
                    break
            if card_info:
                break

        if not card_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

        # ユーザーメッセージを保存（テーブルが存在しない場合はスキップ）
        try:
            user_message = DeepDiveChatLog(
                user_id=current_user.id,
                card_id=card_id,
                role="user",
                message=payload.message,
            )
            session.add(user_message)
            await session.flush()
        except Exception as e:
            logger.warning(f"ユーザーメッセージの保存に失敗しました（テーブルが存在しない可能性）: {e}")

        # AI回答を生成
        # コンテキストとして軸コードとカード情報を含める
        # 深掘り質問用のカスタムプロンプトを使用
        system_prompt = (
        "あなたは優秀な飲食店の開業コンサルタントです。"
        "ユーザーの回答を深掘りし、具体化させてください。"
        f"現在のテーマは「{card_info['title']}」です。"
        f"最初の質問は「{card_info['initial_question']}」でした。"
        "\n【回答の要件】"
        "\n- ユーザーの回答を肯定し、さらに深掘りする質問を投げかける"
        "\n- 具体的な例や提案を含める"
        "\n- 親しみやすく、建設的なトーン"
            "\n- 200〜400文字程度の簡潔な回答"
        )
        
        # チャット履歴を取得してコンテキストに含める
        chat_context = ""
        try:
            chat_logs_result = await session.execute(
                select(DeepDiveChatLog)
                .where(
                    DeepDiveChatLog.user_id == current_user.id,
                    DeepDiveChatLog.card_id == card_id,
                )
                .order_by(DeepDiveChatLog.created_at)
                .limit(10)  # 直近10件の履歴
            )
            chat_logs = list(chat_logs_result.scalars())
            if chat_logs:
                chat_context = "\n\n【これまでの会話】\n" + "\n".join(
                    [f"{log.role}: {log.message}" for log in chat_logs[-6:]]  # 直近6件
                )
        except Exception as e:
            logger.warning(f"チャット履歴の取得に失敗しました（要約生成用）: {e}")
        
        user_content = f"{payload.message}{chat_context}"
        
        # 深掘り質問用のコンテキストを作成
        context = {
            "axis_code": axis_code,
            "card_title": card_info["title"],
            "initial_question": card_info["initial_question"],
        }
        
        # AI回答を生成
        try:
            logger.info(f"AI回答を生成中: card_id={card_id}, user_id={current_user.id}")
            ai_response = await answer_question(context, user_content)
            if not ai_response:
                logger.warning("AI回答が空でした")
                ai_response = "回答の生成に失敗しました。別の聞き方でもう一度お試しください。"
            logger.info(f"AI回答生成完了: {len(ai_response)}文字")
        except Exception as e:
            logger.error(f"AI回答生成エラー: {e}", exc_info=True)
            ai_response = f"申し訳ありません、エラーが発生しました: {str(e)}"

        # AI回答を保存（テーブルが存在しない場合はスキップ）
        try:
            assistant_message = DeepDiveChatLog(
                user_id=current_user.id,
                card_id=card_id,
                role="assistant",
                message=ai_response,
            )
            session.add(assistant_message)
            await session.flush()  # flushで一旦保存（後でcommit）
        except Exception as e:
            logger.warning(f"AI回答の保存に失敗しました（テーブルが存在しない可能性）: {e}")

        # 進捗を更新（テーブルが存在しない場合はスキップ）
        try:
            progress_result = await session.execute(
                select(DeepDiveProgress).where(
                    DeepDiveProgress.user_id == current_user.id,
                    DeepDiveProgress.card_id == card_id,
                )
            )
            progress = progress_result.scalar_one_or_none()
            if not progress and axis_code:
                # 進捗レコードが存在しない場合は新規作成
                progress = DeepDiveProgress(
                    user_id=current_user.id,
                    axis_code=axis_code,
                    card_id=card_id,
                    status=DeepDiveStatus.IN_PROGRESS,
                )
                session.add(progress)
                logger.info(f"進捗レコードを新規作成: card_id={card_id}, status=IN_PROGRESS")
            elif progress and progress.status != DeepDiveStatus.COMPLETED:
                # 既存の進捗レコードがあり、完了していない場合はIN_PROGRESSに更新
                progress.status = DeepDiveStatus.IN_PROGRESS
                logger.info(f"進捗ステータスを更新: card_id={card_id}, status=IN_PROGRESS")
        except Exception as e:
            logger.warning(f"進捗データの更新に失敗しました（テーブルが存在しない可能性）: {e}")

        try:
            await session.commit()
            logger.info(f"進捗データのコミット成功: card_id={card_id}")
        except Exception as e:
            logger.warning(f"コミットに失敗しました（テーブルが存在しない可能性）: {e}")
            await session.rollback()

        # 更新されたチャット履歴を返す（テーブルが存在しない場合でも静的データを返す）
        # 最新のチャット履歴を取得
        messages = []
        try:
            result = await session.execute(
                select(DeepDiveChatLog)
                .where(DeepDiveChatLog.user_id == current_user.id, DeepDiveChatLog.card_id == card_id)
                .order_by(DeepDiveChatLog.created_at.asc())
            )
            chat_logs = list(result.scalars())
            messages = [
                DeepDiveChatMessage(role=log.role, message=log.message, created_at=log.created_at)
                for log in chat_logs
            ]
        except Exception as e:
            logger.warning(f"チャット履歴の取得に失敗しました: {e}")
            # ユーザーメッセージとAI回答を直接追加（テーブルが存在しない場合）
            if payload.message:
                messages.append(
                    DeepDiveChatMessage(
                        role="user",
                        message=payload.message,
                        created_at=datetime.now(timezone.utc),
                    )
                )
            if ai_response:
                messages.append(
                    DeepDiveChatMessage(
                        role="assistant",
                        message=ai_response,
                        created_at=datetime.now(timezone.utc),
                    )
                )
        
        return DeepDiveChatResponse(
            card_id=card_id,
            card_title=card_info["title"],
            initial_question=card_info["initial_question"],
            messages=messages,
        )
    except Exception as e:
        # エラーを確実にログに出力
        error_msg = f"チャット送信処理に失敗しました: {e}"
        error_trace = traceback.format_exc()
        
        # コンソールに出力（stderrに出力して確実に表示）
        import sys
        print("=" * 60, file=sys.stderr, flush=True)
        print("DEEP DIVE CHAT POST ERROR", file=sys.stderr, flush=True)
        print("=" * 60, file=sys.stderr, flush=True)
        print(f"Error: {error_msg}", file=sys.stderr, flush=True)
        print("Traceback:", file=sys.stderr, flush=True)
        print(error_trace, file=sys.stderr, flush=True)
        print("=" * 60, file=sys.stderr, flush=True)
        
        # traceback.print_exc()も実行（確実に表示）
        traceback.print_exc()
        
        # ログにも出力
        logger.error("============== DEEP DIVE CHAT POST ERROR ==============")
        logger.error(error_msg)
        logger.error(f"Traceback:\n{error_trace}")
        logger.error("=====================================================")
        
        # エラーを再スロー（フロントエンドでエラーハンドリングできるように）
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"チャットメッセージの送信に失敗しました: {str(e)}"
        )


@router.post("/card/{card_id}/complete", response_model=DeepDiveCompleteResponse)
async def complete_deep_dive_card(
    card_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserInfo = Depends(get_current_user),
) -> DeepDiveCompleteResponse:
    """
    カードを完了状態にする
    """
    # カードの軸コードを取得
    axis_code = None
    for ax_code, axis_data in DEEP_DIVE_DATA.items():
        for step_data in axis_data:
            for card_data in step_data["cards"]:
                if card_data["id"] == card_id:
                    axis_code = ax_code
                    break
            if axis_code:
                break
        if axis_code:
            break

    if not axis_code:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    # カード情報を取得
    card_info = None
    for ax_code, axis_data in DEEP_DIVE_DATA.items():
        for step_data in axis_data:
            for card_data in step_data["cards"]:
                if card_data["id"] == card_id:
                    card_info = card_data
                    break
            if card_info:
                break
        if card_info:
            break

    if not card_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    # 進捗を更新（確実にDBに保存）
    try:
        logger.info(f"📝 カード完了処理開始: user_id={current_user.id}, card_id={card_id}")
        
        # 要約は固定文字列を使用（開発ブロックを防ぐ）
        summary_text = "DB保存成功 (仮要約)"
        logger.info(f"📝 固定要約を使用: {summary_text}")

        # 進捗データを取得または作成
        progress_result = await session.execute(
            select(DeepDiveProgress).where(
                DeepDiveProgress.user_id == current_user.id,
                DeepDiveProgress.card_id == card_id,
            )
        )
        progress = progress_result.scalar_one_or_none()

        if not progress:
            # 新規作成
            progress = DeepDiveProgress(
                user_id=current_user.id,
                axis_code=axis_code,
                card_id=card_id,
                status=DeepDiveStatus.COMPLETED,
                summary=summary_text,
            )
            session.add(progress)
            logger.info(f"📝 新規進捗レコードを作成: card_id={card_id}")
        else:
            # 既存レコードを更新
            progress.status = DeepDiveStatus.COMPLETED
            progress.summary = summary_text
            logger.info(f"📝 既存進捗レコードを更新: card_id={card_id}")

        # 確実にDBにコミット
        await session.commit()
        logger.info(f"✅ DBコミット成功: card_id={card_id}")
        
        # コミット後にリフレッシュして最新データを取得
        await session.refresh(progress)
        logger.info(
            f"✅ カード完了処理成功: user_id={current_user.id}, card_id={card_id}, "
            f"status={progress.status.value}, summary={progress.summary}"
        )

        return DeepDiveCompleteResponse(
            card_id=card_id,
            status=progress.status.value,
            summary=progress.summary,
        )
    except Exception as e:
        # エラーを確実にログに出力
        error_msg = f"完了処理に失敗しました: {e}"
        error_trace = traceback.format_exc()
        
        # コンソールに出力（stderrに出力して確実に表示）
        import sys
        print("=" * 60, file=sys.stderr, flush=True)
        print("DEEP DIVE COMPLETE ERROR", file=sys.stderr, flush=True)
        print("=" * 60, file=sys.stderr, flush=True)
        print(f"Error: {error_msg}", file=sys.stderr, flush=True)
        print("Traceback:", file=sys.stderr, flush=True)
        print(error_trace, file=sys.stderr, flush=True)
        print("=" * 60, file=sys.stderr, flush=True)
        
        # traceback.print_exc()も実行（確実に表示）
        traceback.print_exc()
        
        # ログにも出力
        logger.error("============== DEEP DIVE COMPLETE ERROR ==============")
        logger.error(error_msg)
        logger.error(f"Traceback:\n{error_trace}")
        logger.error("=====================================================")
        
        # エラーを再スロー（フロントエンドでエラーハンドリングできるように）
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"カードの完了処理に失敗しました: {str(e)}"
        )

