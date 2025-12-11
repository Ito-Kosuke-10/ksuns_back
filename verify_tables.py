"""
テーブルが正しく作成されているか確認するスクリプト
"""
import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from sqlalchemy import text
    from app.core.db import engine
except ImportError as e:
    logger.error(f"❌ モジュールのインポートに失敗しました: {e}")
    sys.exit(1)


async def verify_tables():
    """テーブルの存在と構造を確認"""
    logger.info("📋 テーブルの確認を開始します...")

    try:
        async with engine.begin() as conn:
            # deep_dive_progress テーブル
            result = await conn.execute(
                text("SHOW TABLES LIKE 'deep_dive_progress'")
            )
            if result.fetchone():
                logger.info("✅ テーブル 'deep_dive_progress' が存在します")
                
                # テーブル構造を確認
                result = await conn.execute(
                    text("DESCRIBE deep_dive_progress")
                )
                columns = result.fetchall()
                logger.info(f"   カラム数: {len(columns)}")
                for col in columns:
                    logger.info(f"   - {col[0]} ({col[1]})")
            else:
                logger.error("❌ テーブル 'deep_dive_progress' が存在しません")

            # deep_dive_chat_logs テーブル
            result = await conn.execute(
                text("SHOW TABLES LIKE 'deep_dive_chat_logs'")
            )
            if result.fetchone():
                logger.info("✅ テーブル 'deep_dive_chat_logs' が存在します")
                
                # テーブル構造を確認
                result = await conn.execute(
                    text("DESCRIBE deep_dive_chat_logs")
                )
                columns = result.fetchall()
                logger.info(f"   カラム数: {len(columns)}")
                for col in columns:
                    logger.info(f"   - {col[0]} ({col[1]})")
            else:
                logger.error("❌ テーブル 'deep_dive_chat_logs' が存在しません")

        logger.info("🎉 テーブル確認が完了しました")
    except Exception as e:
        logger.error(f"❌ エラーが発生しました: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(verify_tables())
    except KeyboardInterrupt:
        logger.info("\n中断されました")
    except Exception as e:
        logger.error(f"\nエラーが発生しました: {e}")
        sys.exit(1)



