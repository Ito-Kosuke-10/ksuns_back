# Googleログイン Internal Server Error の診断結果

## ログ分析結果

提供されたログを確認したところ、**`/auth/google/callback` へのリクエストが全く記録されていません**。

これは以下の可能性を示しています：

### 可能性1: リクエストが到達していない（最も可能性が高い）

**症状**: `/auth/google/callback` へのリクエストがログに表示されない

**考えられる原因**:
1. **リダイレクトURIの不一致**
   - Google OAuth Consoleで登録されているリダイレクトURIと、実際のコールバックURLが一致していない
   - 例: 登録が `http://localhost:8000/auth/google/callback` なのに、実際は `https://your-domain.com/auth/google/callback`

2. **リクエストパラメータの欠落**
   - `code` パラメータが欠落している
   - FastAPIがバリデーションエラーを返しているが、ログに記録されていない

### 可能性2: リクエスト到達前にエラーが発生

**症状**: リクエストログが出力される前にエラーが発生

**考えられる原因**:
1. **依存関係のエラー**
   - `get_session()` 依存関係でデータベース接続エラー
   - 環境変数の読み込みエラー

2. **FastAPIの起動時エラー**
   - ルーターの登録時にエラーが発生

## 確認すべきポイント

### 1. リダイレクトURIの確認

Google OAuth Consoleで登録されているリダイレクトURIを確認：

**ローカル環境の場合**:
```
http://localhost:8000/auth/google/callback
```

**Azure環境の場合**:
```
https://your-backend-domain.com/auth/google/callback
```

`.env` ファイルの `GOOGLE_REDIRECT_URI` がこれと一致しているか確認してください。

### 2. ブラウザの開発者ツールで確認

1. F12で開発者ツールを開く
2. **Network** タブを開く
3. Googleログインを試行
4. `/auth/google/callback` へのリクエストを確認
   - リクエストが存在するか
   - ステータスコードは何か（500, 404, 400など）
   - レスポンスの内容は何か

### 3. エラーログの詳細確認

現在のログレベルが `INFO` なので、エラーの詳細が表示されない可能性があります。

**確認方法**:
- ブラウザのコンソールでエラーメッセージを確認
- Azure Portalのログストリームでエラーを確認
- 一時的にログレベルを `DEBUG` に変更

## 最も可能性が高い原因

### 1. リダイレクトURIの不一致（80%の確率）

Google OAuth Consoleで登録されているリダイレクトURIと、実際のコールバックURLが一致していない可能性が高いです。

**確認方法**:
1. Google Cloud Consoleにログイン
2. **APIとサービス** > **認証情報** を開く
3. OAuth 2.0 クライアントIDを選択
4. **承認済みのリダイレクト URI** を確認
5. `.env` の `GOOGLE_REDIRECT_URI` と一致しているか確認

**不一致の例**:
- 登録: `http://localhost:8000/auth/google/callback`
- 実際: `https://your-domain.com/auth/google/callback`
- → Googleがリダイレクトしない、またはエラーを返す

### 2. データベース接続エラー（15%の確率）

`get_session()` 依存関係でデータベース接続エラーが発生している可能性。

**確認方法**:
```bash
# データベース接続をテスト
python -c "from app.core.db import get_session; import asyncio; asyncio.run(get_session().__anext__())"
```

### 3. 環境変数の読み込みエラー（5%の確率）

環境変数が正しく読み込まれていない可能性。

**確認方法**:
```python
from app.core.config import get_settings
settings = get_settings()
print(f"GOOGLE_CLIENT_ID: {settings.google_client_id[:10]}...")
print(f"GOOGLE_REDIRECT_URI: {settings.google_redirect_uri}")
```

## 次のステップ

### ステップ1: ブラウザの開発者ツールで確認

1. F12で開発者ツールを開く
2. **Network** タブを開く
3. Googleログインを試行
4. `/auth/google/callback` へのリクエストを確認
   - リクエストが存在するか
   - ステータスコード
   - レスポンスの内容

### ステップ2: Google OAuth Consoleで確認

1. リダイレクトURIが正しく登録されているか確認
2. `.env` の `GOOGLE_REDIRECT_URI` と一致しているか確認

### ステップ3: 詳細ログを追加（必要に応じて）

エラーの詳細を確認するために、一時的にログを追加：

```python
import logging

logger = logging.getLogger(__name__)

@router.get("/google/callback")
async def google_callback(...):
    logger.info("Google callback started")
    try:
        # ... 既存のコード ...
    except Exception as e:
        logger.error(f"Error in google_callback: {e}", exc_info=True)
        raise
```

## 確認チェックリスト

- [ ] ブラウザの開発者ツール（Networkタブ）で `/auth/google/callback` へのリクエストを確認
- [ ] Google OAuth ConsoleでリダイレクトURIが正しく登録されているか確認
- [ ] `.env` の `GOOGLE_REDIRECT_URI` が正しいか確認
- [ ] データベース接続が正常に動作するか確認
- [ ] Azure Portalのログストリームでエラーを確認

## 予想されるエラーメッセージ

もしリダイレクトURIが不一致の場合、Googleから以下のようなエラーが返される可能性があります：

```
error=redirect_uri_mismatch
error_description=The redirect URI in the request does not match the ones authorized for the OAuth client.
```

このエラーは、ブラウザのURLバーや開発者ツールで確認できる可能性があります。



