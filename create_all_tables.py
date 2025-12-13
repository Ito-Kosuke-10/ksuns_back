"""
すべてのテーブルを一括作成するスクリプト
SQLAlchemyのモデルから自動生成します
"""
import asyncio
import logging
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from sqlalchemy import text
    from app.core.config import get_settings
    from app.core.db import engine
    # すべてのモデルをインポート（Base.metadataに登録される）
    from app.models import (
        Base,
        User,
        PlanningAxis,
        AxisStep,
        AxisAnswer,
        AxisScore,
        ConceptAnswer,
        RevenueForecastAnswer,
        FundingPlanAnswer,
        OperationAnswer,
        LocationAnswer,
        InteriorExteriorAnswer,
        MarketingAnswer,
        MenuAnswer,
        DetailQuestionAnswer,
        DeepQuestion,
        DeepAnswer,
        FreeQuestion,
        BusinessPlanDraft,
        OwnerNote,
        StoreStory,
        Summary,
        QAConversation,
        QAMessage,
        Question,
        SimpleSimulationSession,
        SimpleSimulationAnswer,
        SimpleSimulationResult,
    )
except ImportError as e:
    logger.error(f"❌ モジュールのインポートに失敗しました: {e}")
    logger.error("")
    logger.error("仮想環境をアクティブにしてください:")
    logger.error("  .venv\\Scripts\\Activate.ps1  (Windows)")
    logger.error("  source .venv/bin/activate  (Linux/Mac)")
    sys.exit(1)


async def create_all_tables():
    """すべてのテーブルを作成"""
    settings = get_settings()
    logger.info("📝 テーブル作成を開始します...")
    logger.info(f"データベース: {settings.db_host}:{settings.db_port}/{settings.db_name}")

    try:
        async with engine.begin() as conn:
            # 既存のテーブル一覧を取得
            result = await conn.execute(text("SHOW TABLES"))
            existing_tables = {row[0] for row in result.fetchall()}
            logger.info(f"既存のテーブル数: {len(existing_tables)}")

            # すべてのテーブルを作成（既存のものはスキップされる）
            logger.info("📝 テーブルを作成します...")
            await conn.run_sync(Base.metadata.create_all)
            
            # 作成されたテーブルを確認
            result = await conn.execute(text("SHOW TABLES"))
            created_tables = {row[0] for row in result.fetchall()}
            new_tables = created_tables - existing_tables
            
            if new_tables:
                logger.info(f"✅ 新規作成されたテーブル ({len(new_tables)}個):")
                for table in sorted(new_tables):
                    logger.info(f"  - {table}")
            else:
                logger.info("✅ すべてのテーブルは既に存在しています")

        logger.info("🎉 テーブル作成処理が完了しました")
        
    except Exception as e:
        logger.error(f"❌ データベース接続エラー: {e}")
        logger.error("")
        logger.error("確認事項:")
        logger.error("1. Dockerコンテナが起動しているか確認: docker ps")
        logger.error("2. .envファイルの設定を確認")
        logger.error("3. データベース接続情報が正しいか確認")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(create_all_tables())
    except KeyboardInterrupt:
        logger.info("\n中断されました")
    except Exception as e:
        logger.error(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

