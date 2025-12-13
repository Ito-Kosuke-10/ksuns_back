"""
ローカルDocker環境のテーブルを確認するスクリプト
"""
import asyncio
import logging
import sys
from pathlib import Path

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
    from app.models import Base
except ImportError as e:
    logger.error(f"❌ モジュールのインポートに失敗しました: {e}")
    sys.exit(1)


async def verify_tables():
    """テーブルの存在を確認"""
    settings = get_settings()
    logger.info("🔍 テーブル確認を開始します...")
    logger.info(f"データベース: {settings.db_host}:{settings.db_port}/{settings.db_name}")

    try:
        async with engine.begin() as conn:
            # すべてのテーブルを取得
            result = await conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]
            
            logger.info(f"\n📊 データベース '{settings.db_name}' のテーブル一覧:")
            logger.info(f"合計: {len(tables)} 個のテーブル\n")
            
            # カテゴリ別に分類
            categories = {
                "ユーザー管理": ["users"],
                "軸関連": ["planning_axes", "axis_steps", "axis_answers", "axis_scores"],
                "Deep Questions (8軸)": [
                    "concept_answers",
                    "revenue_forecast_answers",
                    "funding_plan_answers",
                    "operation_answers",
                    "location_answers",
                    "interior_exterior_answers",
                    "marketing_answers",
                    "menu_answers",
                ],
                "その他": [
                    "detail_question_answers",
                    "deep_questions",
                    "deep_answers",
                    "free_questions",
                    "business_plan_drafts",
                    "owner_notes",
                    "store_stories",
                    "summaries",
                    "qa_conversations",
                    "qa_messages",
                    "questions",
                    "simple_simulation_sessions",
                    "simple_simulation_answers",
                    "simple_simulation_results",
                ],
            }
            
            for category, expected_tables in categories.items():
                logger.info(f"【{category}】")
                for table in expected_tables:
                    if table in tables:
                        logger.info(f"  ✅ {table}")
                    else:
                        logger.warning(f"  ❌ {table} (見つかりません)")
                logger.info("")
            
            # 予期しないテーブルがある場合
            all_expected = set()
            for tables_list in categories.values():
                all_expected.update(tables_list)
            
            unexpected = set(tables) - all_expected
            if unexpected:
                logger.info("【その他のテーブル】")
                for table in sorted(unexpected):
                    logger.info(f"  ⚠️  {table}")
                logger.info("")
            
            # 各テーブルのレコード数を確認
            logger.info("📈 テーブル別レコード数:")
            for table in sorted(tables):
                try:
                    result = await conn.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
                    count = result.scalar()
                    logger.info(f"  {table}: {count} 件")
                except Exception as e:
                    logger.warning(f"  {table}: 確認失敗 ({e})")
            
        logger.info("\n✅ テーブル確認が完了しました")
        
    except Exception as e:
        logger.error(f"❌ データベース接続エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(verify_tables())
    except KeyboardInterrupt:
        logger.info("\n中断されました")
    except Exception as e:
        logger.error(f"\nエラーが発生しました: {e}")
        sys.exit(1)

