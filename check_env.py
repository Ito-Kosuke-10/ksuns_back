#!/usr/bin/env python3
"""
環境変数の確認スクリプト
Google OAuth設定が正しく読み込まれているか確認します
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込む
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

print("=" * 60)
print("環境変数の確認")
print("=" * 60)

# Google OAuth関連の環境変数を確認
google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

print(f"\nGOOGLE_CLIENT_ID: {google_client_id[:20] + '...' if google_client_id and len(google_client_id) > 20 else google_client_id}")
print(f"GOOGLE_CLIENT_SECRET: {'***' if google_client_secret else 'MISSING'}")
print(f"GOOGLE_REDIRECT_URI: {google_redirect_uri}")

# Settingsクラスで読み込めるか確認
try:
    from app.core.config import get_settings
    settings = get_settings()
    print("\n" + "=" * 60)
    print("Settingsクラスから読み込んだ値")
    print("=" * 60)
    print(f"google_client_id: {settings.google_client_id[:20] + '...' if len(settings.google_client_id) > 20 else settings.google_client_id}")
    print(f"google_client_secret: {'***' if settings.google_client_secret else 'MISSING'}")
    print(f"google_redirect_uri: {settings.google_redirect_uri}")
    print("\n✅ 環境変数は正しく読み込まれています")
except Exception as e:
    print(f"\n❌ エラー: {e}")
    import traceback
    traceback.print_exc()



