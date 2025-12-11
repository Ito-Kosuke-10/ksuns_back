"""
アプリ起動時にテーブルを作成する方法
バックエンドアプリが動作している場合、この方法が最も確実です
"""
import logging

from sqlalchemy import text

from app.core.db import engine
from app.models.deep_dive import DeepDiveChatLog, DeepDiveProgress

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables_on_startup():
    """アプリ起動時にテーブルを作成"""
    logger.info("📝 深掘り機能のテーブルを確認・作成します...")

    try:
        async with engine.begin() as conn:
            # deep_dive_progress テーブル
            try:
                result = await conn.execute(
                    text("SHOW TABLES LIKE 'deep_dive_progress'")
                )
                if result.fetchone():
                    logger.info("✅ テーブル 'deep_dive_progress' は既に存在します")
                else:
                    logger.info("📝 テーブル 'deep_dive_progress' を作成します...")
                    await conn.run_sync(DeepDiveProgress.__table__.create)
                    logger.info("✅ テーブル 'deep_dive_progress' を作成しました")
            except Exception as e:
                logger.warning(f"⚠️  テーブル 'deep_dive_progress' の確認/作成中にエラー: {e}")

            # deep_dive_chat_logs テーブル
            try:
                result = await conn.execute(
                    text("SHOW TABLES LIKE 'deep_dive_chat_logs'")
                )
                if result.fetchone():
                    logger.info("✅ テーブル 'deep_dive_chat_logs' は既に存在します")
                else:
                    logger.info("📝 テーブル 'deep_dive_chat_logs' を作成します...")
                    await conn.run_sync(DeepDiveChatLog.__table__.create)
                    logger.info("✅ テーブル 'deep_dive_chat_logs' を作成しました")
            except Exception as e:
                logger.warning(f"⚠️  テーブル 'deep_dive_chat_logs' の確認/作成中にエラー: {e}")

        logger.info("🎉 テーブル確認・作成処理が完了しました")
    except Exception as e:
        logger.error(f"❌ テーブル作成中にエラー: {e}")
        logger.warning("⚠️  データベース接続に失敗しましたが、アプリケーションは起動を続けます。")
        logger.warning("⚠️  テーブルは既に存在する可能性があります。API呼び出し時に自動的に作成されます。")
        # エラーでもアプリは起動を続ける

