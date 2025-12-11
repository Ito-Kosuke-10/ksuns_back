"""
コンセプト軸の質問カード回答テーブルを作成するスクリプト
バックエンドアプリケーション経由でテーブルを作成するので、ファイアウォールの問題を回避できます
"""
import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from sqlalchemy import text
    from app.core.db import engine
    from app.models.concept_answer import ConceptAnswer
except ImportError as e:
    logger.error(f"❌ モジュールのインポートに失敗しました: {e}")
    logger.error("")
    logger.error("仮想環境をアクティブにしてください:")
    logger.error("  .venv\\Scripts\\Activate.ps1")
    sys.exit(1)


async def create_table():
    """concept_answersテーブルを作成"""
    logger.info("📝 concept_answersテーブル作成を開始します...")

    try:
        async with engine.begin() as conn:
            # concept_answers テーブル
            try:
                result = await conn.execute(
                    text("SHOW TABLES LIKE 'concept_answers'")
                )
                if result.fetchone():
                    logger.info("✅ テーブル 'concept_answers' は既に存在します")
                else:
                    logger.info("📝 テーブル 'concept_answers' を作成します...")
                    await conn.run_sync(ConceptAnswer.__table__.create)
                    logger.info("✅ テーブル 'concept_answers' を作成しました")
            except Exception as e:
                logger.error(f"❌ テーブル 'concept_answers' の作成中にエラー: {e}")
                raise

        logger.info("🎉 テーブル作成処理が完了しました")
    except Exception as e:
        logger.error(f"❌ データベース接続エラー: {e}")
        logger.error("")
        logger.error("⚠️  データベースへの接続に失敗しました。")
        logger.error("")
        logger.error("確認事項:")
        logger.error("1. バックエンドアプリケーションが正常に動作しているか確認")
        logger.error("2. .envファイルの設定を確認")
        logger.error("3. データベースが起動しているか確認")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(create_table())
    except KeyboardInterrupt:
        logger.info("\n中断されました")
    except Exception as e:
        logger.error(f"\nエラーが発生しました: {e}")
        sys.exit(1)

