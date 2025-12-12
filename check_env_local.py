"""
ローカル環境変数の確認スクリプト
.envファイルが正しく読み込まれているか確認します
"""
import os
from pathlib import Path

# .envファイルのパス
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"

print("=" * 60)
print("環境変数チェック")
print("=" * 60)
print(f"\n.envファイルのパス: {env_path}")
print(f".envファイルが存在するか: {env_path.exists()}")

if env_path.exists():
    print(f"\n.envファイルの内容（最初の10行）:")
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()[:10]
        for i, line in enumerate(lines, 1):
            # パスワードやシークレットは一部のみ表示
            if "PASSWORD" in line or "SECRET" in line or "KEY" in line:
                parts = line.split("=", 1)
                if len(parts) == 2:
                    key = parts[0]
                    value = parts[1].strip()
                    if value:
                        masked = value[:4] + "..." if len(value) > 4 else "***"
                        print(f"  {i}: {key}={masked}")
                    else:
                        print(f"  {i}: {key}=(空)")
                else:
                    print(f"  {i}: {line.strip()}")
            else:
                print(f"  {i}: {line.strip()}")
else:
    print("\n⚠️  .envファイルが見つかりません！")
    print("Azure Portalから環境変数をコピーして、.envファイルを作成してください。")

print("\n" + "=" * 60)
print("必須環境変数の確認")
print("=" * 60)

required_vars = [
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "JWT_SECRET",
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_NAME",
    "FRONTEND_URL",
]

missing_vars = []
for var in required_vars:
    value = os.getenv(var)
    if value:
        if "SECRET" in var or "PASSWORD" in var or "KEY" in var:
            print(f"✅ {var}: {value[:10]}... (設定済み)")
        else:
            print(f"✅ {var}: {value} (設定済み)")
    else:
        print(f"❌ {var}: 設定されていません")
        missing_vars.append(var)

print("\n" + "=" * 60)
if missing_vars:
    print(f"⚠️  未設定の環境変数: {len(missing_vars)}個")
    print("以下の環境変数を設定してください:")
    for var in missing_vars:
        print(f"  - {var}")
else:
    print("✅ すべての必須環境変数が設定されています")
print("=" * 60)



