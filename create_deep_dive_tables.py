"""
深掘り機能（Deep Dive）のテーブルを作成するスクリプト
"""
import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 依存関係のチェック
try:
    from sqlalchemy import text
    from app.core.config import get_settings
    from app.core.db import engine
    from app.models.deep_dive import DeepDiveChatLog, DeepDiveProgress
except ImportError as e:
    logger.error(f"❌ モジュールのインポートに失敗しました: {e}")
    logger.error("")
    logger.error("以下のいずれかを試してください:")
    logger.error("1. 仮想環境をアクティブにする:")
    logger.error("   Windows: .venv\\Scripts\\activate")
    logger.error("   Linux/Mac: source .venv/bin/activate")
    logger.error("")
    logger.error("2. 依存関係をインストールする:")
    logger.error("   pip install -r requirements.txt")
    logger.error("")
    logger.error("3. SQLを直接実行する方法（推奨）:")
    logger.error("   create_tables.sql ファイルを開いて、MySQLで直接実行してください")
    logger.error("   または CREATE_TABLES.md を参照してください")
    sys.exit(1)


async def create_tables():
    """深掘り機能のテーブルを作成"""
    settings = get_settings()
    db_name = settings.database_url.split("/")[-1].split("?")[0] if "/" in settings.database_url else "***"
    logger.info(f"データベース: {db_name}")

    try:
        async with engine.begin() as conn:
        # テーブルが存在するか確認してから作成
        try:
            # deep_dive_progress テーブル
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
            logger.error(f"❌ テーブル 'deep_dive_progress' の確認/作成中にエラー: {e}", exc_info=True)
            # エラーでも続行（テーブルが既に存在する可能性）

        try:
            # deep_dive_chat_logs テーブル
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
            logger.error(f"❌ テーブル 'deep_dive_chat_logs' の確認/作成中にエラー: {e}", exc_info=True)
            # エラーでも続行（テーブルが既に存在する可能性）

        logger.info("🎉 テーブル作成処理が完了しました")
    except Exception as e:
        logger.error(f"❌ データベース接続エラー: {e}")
        logger.error("")
        logger.error("⚠️  Azure MySQLへの接続に失敗しました。")
        logger.error("")
        logger.error("💡 解決方法:")
        logger.error("   以下のSQLファイルを直接MySQLで実行してください:")
        logger.error("   → create_tables.sql")
        logger.error("")
        logger.error("   手順:")
        logger.error("   1. create_tables.sql ファイルを開く")
        logger.error("   2. Azure MySQLに接続（Azure Portal、MySQL Workbench、コマンドラインなど）")
        logger.error("   3. SQLファイルの内容をコピー＆ペーストして実行")
        logger.error("")
        logger.error("   または、以下のコマンドで実行:")
        logger.error("   mysql -h [ホスト名] -u [ユーザー名] -p [データベース名] < create_tables.sql")
        raise


if __name__ == "__main__":
    asyncio.run(create_tables())

