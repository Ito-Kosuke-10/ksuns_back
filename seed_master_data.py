"""
マスタデータを投入するスクリプト
planning_axes テーブルに8つの軸の初期データを投入します
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
    from app.models.axis import PlanningAxis
except ImportError as e:
    logger.error(f"❌ モジュールのインポートに失敗しました: {e}")
    logger.error("")
    logger.error("仮想環境をアクティブにしてください:")
    logger.error("  .venv\\Scripts\\Activate.ps1  (Windows)")
    logger.error("  source .venv/bin/activate  (Linux/Mac)")
    sys.exit(1)


# 8つの軸のマスタデータ
AXES_DATA = [
    {
        "code": "concept",
        "name": "コンセプト",
        "description": "お店のコンセプト、世界観、ターゲット、コア価値などを定義します",
        "display_order": 1,
    },
    {
        "code": "revenue_forecast",
        "name": "収支予測",
        "description": "売上予測、コスト構造、損益分岐点などを分析します",
        "display_order": 2,
    },
    {
        "code": "funds",
        "name": "資金計画",
        "description": "初期投資、運転資金、資金調達方法などを計画します",
        "display_order": 3,
    },
    {
        "code": "location",
        "name": "立地",
        "description": "店舗の立地条件、エリア分析、競合店舗の調査などを実施します",
        "display_order": 4,
    },
    {
        "code": "interior_exterior",
        "name": "内装外装",
        "description": "店舗の内装・外装デザイン、設備計画などを検討します",
        "display_order": 5,
    },
    {
        "code": "menu",
        "name": "メニュー",
        "description": "提供するメニュー、価格設定、原価率などを決定します",
        "display_order": 6,
    },
    {
        "code": "operation",
        "name": "オペレーション",
        "description": "営業時間、人員配置、業務フロー、システム導入などを計画します",
        "display_order": 7,
    },
    {
        "code": "marketing",
        "name": "販促",
        "description": "集客施策、SNS運用、プロモーション計画などを立案します",
        "display_order": 8,
    },
]


async def seed_master_data():
    """マスタデータを投入"""
    settings = get_settings()
    logger.info("📝 マスタデータの投入を開始します...")
    logger.info(f"データベース: {settings.db_host}:{settings.db_port}/{settings.db_name}")

    try:
        async with engine.begin() as conn:
            # 既存のデータを確認
            result = await conn.execute(text("SELECT COUNT(*) FROM planning_axes"))
            existing_count = result.scalar()
            logger.info(f"既存のレコード数: {existing_count}")

            if existing_count > 0:
                logger.warning("⚠️  planning_axes テーブルに既にデータが存在します")
                logger.warning("既存データを確認してください。必要に応じて手動で削除してから再実行してください。")
                response = input("既存データを削除して続行しますか？ (yes/no): ")
                if response.lower() != "yes":
                    logger.info("処理を中断しました")
                    return
                await conn.execute(text("DELETE FROM planning_axes"))
                logger.info("既存データを削除しました")

            # マスタデータを投入
            logger.info(f"📝 {len(AXES_DATA)} 件の軸データを投入します...")
            
            for axis_data in AXES_DATA:
                # INSERT文を実行
                await conn.execute(
                    text("""
                        INSERT INTO planning_axes (code, name, description, display_order)
                        VALUES (:code, :name, :description, :display_order)
                    """),
                    {
                        "code": axis_data["code"],
                        "name": axis_data["name"],
                        "description": axis_data["description"],
                        "display_order": axis_data["display_order"],
                    }
                )
                logger.info(f"  ✅ {axis_data['name']} ({axis_data['code']})")

            # 投入結果を確認
            result = await conn.execute(text("SELECT COUNT(*) FROM planning_axes"))
            final_count = result.scalar()
            logger.info(f"\n🎉 マスタデータの投入が完了しました")
            logger.info(f"投入後のレコード数: {final_count}")

            # 投入されたデータを表示
            result = await conn.execute(
                text("SELECT id, code, name, display_order FROM planning_axes ORDER BY display_order")
            )
            logger.info("\n📊 投入されたデータ:")
            for row in result.fetchall():
                logger.info(f"  ID: {row[0]}, Code: {row[1]}, Name: {row[2]}, Order: {row[3]}")

    except Exception as e:
        logger.error(f"❌ マスタデータ投入中にエラー: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    try:
        asyncio.run(seed_master_data())
    except KeyboardInterrupt:
        logger.info("\n中断されました")
    except Exception as e:
        logger.error(f"\nエラーが発生しました: {e}")
        sys.exit(1)

