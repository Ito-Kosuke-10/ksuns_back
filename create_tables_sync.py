"""
同期版のテーブル作成スクリプト
Windows環境でのasyncmyの問題を回避するため、同期接続を使用
"""
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from sqlalchemy import create_engine, text
    from app.core.config import get_settings
    from app.models.deep_dive import DeepDiveChatLog, DeepDiveProgress
except ImportError as e:
    logger.error(f"❌ モジュールのインポートに失敗しました: {e}")
    logger.error("")
    logger.error("仮想環境をアクティブにしてください:")
    logger.error("  .venv\\Scripts\\Activate.ps1")
    sys.exit(1)


def create_tables():
    """深掘り機能のテーブルを作成（同期版）"""
    settings = get_settings()
    
    # データベースURLを同期版に変換（mysql+asyncmy → mysql+pymysql）
    sync_url = settings.database_url.replace("mysql+asyncmy://", "mysql+pymysql://")
    
    logger.info("📝 テーブル作成を開始します...")
    logger.info(f"データベース: {sync_url.split('@')[1] if '@' in sync_url else '***'}")

    try:
        # 同期エンジンを作成
        engine = create_engine(
            sync_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        with engine.begin() as conn:
            # deep_dive_progress テーブル
            try:
                result = conn.execute(
                    text("SHOW TABLES LIKE 'deep_dive_progress'")
                )
                if result.fetchone():
                    logger.info("✅ テーブル 'deep_dive_progress' は既に存在します")
                else:
                    logger.info("📝 テーブル 'deep_dive_progress' を作成します...")
                    DeepDiveProgress.__table__.create(engine)
                    logger.info("✅ テーブル 'deep_dive_progress' を作成しました")
            except Exception as e:
                logger.error(f"❌ テーブル 'deep_dive_progress' の作成中にエラー: {e}")
                # エラーでも続行

            # deep_dive_chat_logs テーブル
            try:
                result = conn.execute(
                    text("SHOW TABLES LIKE 'deep_dive_chat_logs'")
                )
                if result.fetchone():
                    logger.info("✅ テーブル 'deep_dive_chat_logs' は既に存在します")
                else:
                    logger.info("📝 テーブル 'deep_dive_chat_logs' を作成します...")
                    DeepDiveChatLog.__table__.create(engine)
                    logger.info("✅ テーブル 'deep_dive_chat_logs' を作成しました")
            except Exception as e:
                logger.error(f"❌ テーブル 'deep_dive_chat_logs' の作成中にエラー: {e}")
                # エラーでも続行

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
        logger.error("4. ファイアウォール設定を確認（Azure Portal）")
        logger.error("")
        logger.error("💡 別の方法:")
        logger.error("   バックエンドアプリが動作している場合、")
        logger.error("   アプリの起動時にテーブルを自動作成する設定を追加することもできます。")
        raise


if __name__ == "__main__":
    try:
        create_tables()
    except KeyboardInterrupt:
        logger.info("\n中断されました")
    except Exception as e:
        logger.error(f"\nエラーが発生しました: {e}")
        sys.exit(1)



