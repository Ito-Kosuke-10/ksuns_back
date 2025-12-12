# 環境変数設定手順

## 概要

このドキュメントでは、ローカル環境とAzure環境での環境変数の設定方法を説明します。

---

## バックエンド環境変数

### ローカル環境

1. **`.env` ファイルを作成**
   ```bash
   cd C:\ksuns_back
   cp .env.example .env  # もし .env.example があれば
   ```

2. **必要な環境変数を設定**

   ```env
   # アプリケーション設定
   APP_NAME=ksuns
   FRONTEND_URL=http://localhost:3000

   # データベース設定
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=ksuns_db

   # JWT設定
   JWT_SECRET=your_jwt_secret_key_here
   ACCESS_TOKEN_TTL_MIN=15
   REFRESH_TOKEN_TTL_DAY=14

   # Google認証設定
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

   # Azure OpenAI設定
   TARGET_URI=https://your-resource-name.openai.azure.com/
   AI_FOUNDARY_KEY=your_azure_openai_api_key

   # CORS設定（カンマ区切り）
   CORS_ORIGINS=http://localhost:3000,http://localhost:3001
   ```

3. **`.env` ファイルを `.gitignore` に追加（既に追加されているはず）**

### Azure環境

Azure環境では、環境変数は **App Service の設定** または **環境変数** として設定します。

#### App Service の場合

1. Azure Portal にログイン
2. App Service リソースを選択
3. **設定** > **構成** > **アプリケーション設定** を開く
4. 以下の環境変数を追加：

   | 名前 | 値 | 説明 |
   |------|-----|------|
   | `APP_NAME` | `ksuns` | アプリケーション名 |
   | `FRONTEND_URL` | `https://your-frontend-domain.com` | フロントエンドのURL |
   | `DB_USER` | `your_db_user` | データベースユーザー名 |
   | `DB_PASSWORD` | `your_db_password` | データベースパスワード |
   | `DB_HOST` | `your_db_host.mysql.database.azure.com` | データベースホスト |
   | `DB_PORT` | `3306` | データベースポート |
   | `DB_NAME` | `ksuns_db` | データベース名 |
   | `JWT_SECRET` | `your_jwt_secret` | JWT秘密鍵 |
   | `GOOGLE_CLIENT_ID` | `your_google_client_id` | Google OAuth Client ID |
   | `GOOGLE_CLIENT_SECRET` | `your_google_client_secret` | Google OAuth Client Secret |
   | `GOOGLE_REDIRECT_URI` | `https://your-backend-domain.com/auth/google/callback` | Google OAuth リダイレクトURI |
   | `TARGET_URI` | `https://your-resource-name.openai.azure.com/` | Azure OpenAI エンドポイント |
   | `AI_FOUNDARY_KEY` | `your_azure_openai_api_key` | Azure OpenAI API キー |
   | `CORS_ORIGINS` | `https://your-frontend-domain.com` | CORS許可オリジン（カンマ区切り） |

5. **保存** をクリック（再起動が必要な場合あり）

#### Azure OpenAI の設定方法

1. **Azure Portal** で **Azure OpenAI** リソースを作成
2. **キーとエンドポイント** を開く
3. **エンドポイント** を `TARGET_URI` に設定
4. **キー1** または **キー2** を `AI_FOUNDARY_KEY` に設定
5. **デプロイメント** でモデル（例: `gpt-4`）をデプロイ
6. モデル名を `app/services/ai_client.py` の `MODEL_NAME` に設定

---

## フロントエンド環境変数

### ローカル環境

1. **`.env.local` ファイルを作成**
   ```bash
   cd C:\ksuns_front
   ```

2. **必要な環境変数を設定**

   ```env
   # バックエンドAPIのエンドポイント
   NEXT_PUBLIC_API_ENDPOINT=http://localhost:8000
   ```

3. **`.env.local` は `.gitignore` に追加されているはず**

### Azure環境（Vercel/その他）

#### Vercel の場合

1. Vercel ダッシュボードにログイン
2. プロジェクトを選択
3. **Settings** > **Environment Variables** を開く
4. 以下の環境変数を追加：

   | 名前 | 値 | 環境 |
   |------|-----|------|
   | `NEXT_PUBLIC_API_ENDPOINT` | `https://your-backend-domain.com` | Production, Preview, Development |

#### その他のホスティングサービスの場合

各サービスの環境変数設定方法に従って、`NEXT_PUBLIC_API_ENDPOINT` を設定してください。

---

## 環境変数の説明

### バックエンド

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `DB_USER` | ✅ | データベースユーザー名 |
| `DB_PASSWORD` | ✅ | データベースパスワード |
| `DB_HOST` | ✅ | データベースホスト |
| `DB_NAME` | ✅ | データベース名 |
| `JWT_SECRET` | ✅ | JWTトークンの秘密鍵（ランダムな文字列） |
| `GOOGLE_CLIENT_ID` | ✅ | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | ✅ | Google OAuth Client Secret |
| `GOOGLE_REDIRECT_URI` | ✅ | Google OAuth リダイレクトURI |
| `TARGET_URI` | ✅ | Azure OpenAI エンドポイント |
| `AI_FOUNDARY_KEY` | ✅ | Azure OpenAI API キー |
| `FRONTEND_URL` | ⚠️ | フロントエンドURL（デフォルト: `http://localhost:3000`） |
| `CORS_ORIGINS` | ⚠️ | CORS許可オリジン（カンマ区切り、デフォルト: 空） |

### フロントエンド

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `NEXT_PUBLIC_API_ENDPOINT` | ⚠️ | バックエンドAPIのエンドポイント（デフォルト: `http://localhost:8000`） |

**注意**: `NEXT_PUBLIC_` プレフィックスが付いた環境変数は、クライアント側のコードからもアクセス可能です。

---

## トラブルシューティング

### バックエンドが起動しない

1. `.env` ファイルが正しい場所にあるか確認（`C:\ksuns_back\.env`）
2. 必須の環境変数がすべて設定されているか確認
3. データベース接続情報が正しいか確認

### Azure OpenAI が動作しない

1. `TARGET_URI` が正しいエンドポイントか確認（末尾に `/` が付いているか）
2. `AI_FOUNDARY_KEY` が正しいAPIキーか確認
3. モデルがデプロイされているか確認
4. `app/services/ai_client.py` の `MODEL_NAME` が正しいか確認

### フロントエンドがAPIに接続できない

1. `NEXT_PUBLIC_API_ENDPOINT` が正しく設定されているか確認
2. CORS設定が正しいか確認（バックエンドの `CORS_ORIGINS`）
3. ブラウザのコンソールでエラーを確認

---

## セキュリティ注意事項

⚠️ **重要**: 
- `.env` ファイルは **絶対に** コミットしないでください
- `.gitignore` に `.env` が含まれているか確認してください
- 本番環境のAPIキーや秘密鍵は、環境変数として設定し、コードに直接書かないでください





