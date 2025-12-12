# Googleログイン Internal Server Error の原因分析

## エラーの発生箇所

Googleログインのコールバック処理は `app/api/auth.py` の `google_callback` 関数で行われています。

## 考えられる原因

### 1. データベースエラー（最も可能性が高い）

**問題箇所**: `app/services/auth.py` の `get_or_create_user` 関数

```python
# 38-41行目
new_user = User(google_sub=google_sub, email=email, display_name=display_name or email)
session.add(new_user)
await session.commit()  # ← ここでエラーが発生する可能性
await session.refresh(new_user)
```

**考えられる原因**:
- データベース接続エラー
- テーブルが存在しない（`users` テーブルが作成されていない）
- 制約違反（`google_sub` や `email` のUNIQUE制約）
- トランザクションエラー

**確認方法**:
```sql
-- MySQLに接続して確認
SHOW TABLES LIKE 'users';
DESCRIBE users;
```

### 2. 環境変数の設定ミス

**問題箇所**: `app/core/config.py`

必要な環境変数が設定されていない、または間違っている可能性：

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=...
JWT_SECRET=...
```

**確認方法**:
- `.env` ファイルを確認
- Azure App Serviceの環境変数設定を確認

### 3. Google OAuth API のレスポンスエラー

**問題箇所**: `app/api/auth.py` の67-73行目

```python
async with httpx.AsyncClient(timeout=10) as client:
    token_res = await client.post(token_endpoint, data=payload)
if token_res.status_code != 200:
    raise HTTPException(...)  # ← 400エラーになるが、詳細が不明
```

**考えられる原因**:
- `client_id` または `client_secret` が間違っている
- `redirect_uri` がGoogle Consoleで登録されているものと一致しない
- 認証コードが無効または期限切れ

### 4. JWTトークン生成エラー

**問題箇所**: `app/api/auth.py` の115-124行目

```python
access_token = create_access_token(
    subject=str(user.id),
    secret=settings.jwt_secret,
    expires_delta=access_expires,
)
```

**考えられる原因**:
- `JWT_SECRET` が設定されていない
- `user.id` が `None` の場合（データベースから取得できなかった）

### 5. エラーハンドリングの不備

**問題箇所**: `app/api/auth.py` の `google_callback` 関数

現在、以下の例外しかキャッチしていません：
- `ValueError` (107行目) - ユーザー作成が許可されていない場合のみ

**キャッチされていない例外**:
- データベース接続エラー
- SQLAlchemyの例外
- その他の予期しない例外

これらが発生すると、FastAPIがInternal Server Error (500)を返します。

## エラーの詳細を確認する方法

### 方法1: ログを確認

#### ローカル環境の場合

バックエンドアプリを起動したターミナルのログを確認：

```bash
cd C:\ksuns_back
python -m uvicorn app.main:app --reload
```

エラーが発生すると、スタックトレースが表示されます。

#### Azure環境の場合

1. Azure Portalにログイン
2. App Serviceリソースを選択
3. **監視** > **ログストリーム** を開く
4. または **監視** > **App Service ログ** でログファイルを確認

### 方法2: エラーレスポンスを確認

ブラウザの開発者ツール（F12）で以下を確認：

1. **Network** タブを開く
2. Googleログインを試行
3. `/auth/google/callback` のリクエストを確認
4. レスポンスの詳細を確認

### 方法3: 一時的にログを追加

`app/api/auth.py` の `google_callback` 関数にログを追加：

```python
import logging

logger = logging.getLogger(__name__)

@router.get("/google/callback")
async def google_callback(...):
    try:
        logger.info("Google callback started")
        # ... 既存のコード ...
        logger.info(f"User created/found: {user.id}")
    except Exception as e:
        logger.error(f"Error in google_callback: {e}", exc_info=True)
        raise
```

## 最も可能性が高い原因

### 1. データベーステーブルが存在しない

**確認方法**:
```sql
USE ksuns_db;
SHOW TABLES;
```

`users` テーブルが存在しない場合、エラーが発生します。

**解決方法**:
テーブルを作成する必要があります（マイグレーションツールが設定されていないため）。

### 2. データベース接続エラー

**確認方法**:
- `.env` ファイルの `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` が正しいか
- Azure Database for MySQLに接続できるか

### 3. ユーザー作成時の制約違反

**確認方法**:
同じ `google_sub` や `email` で既にユーザーが存在する場合、UNIQUE制約違反が発生する可能性があります。

## 推奨される修正（まだ実装しない）

### 1. エラーハンドリングの改善

```python
@router.get("/google/callback")
async def google_callback(...):
    try:
        # ... 既存のコード ...
    except ValueError as e:
        # 既存の処理
        redirect_url = f"{settings.frontend_url}/login?error=signup_not_allowed"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except Exception as e:
        # 新しいエラーハンドリング
        logger.error(f"Unexpected error in google_callback: {e}", exc_info=True)
        redirect_url = f"{settings.frontend_url}/login?error=internal_error"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
```

### 2. ログの追加

各ステップでログを出力して、どこでエラーが発生しているか特定できるようにする。

### 3. データベースエラーの詳細確認

`get_or_create_user` 関数でデータベースエラーをキャッチして、詳細なエラーメッセージを返す。

## 次のステップ

1. **ログを確認**して、実際のエラーメッセージを特定
2. **データベースの状態を確認**（テーブルの存在、接続）
3. **環境変数を確認**（Google OAuth設定、データベース接続情報）
4. エラーの詳細が分かったら、適切な修正を実施

## 確認チェックリスト

- [ ] バックエンドのログを確認（ローカル/Azure）
- [ ] データベースに `users` テーブルが存在するか確認
- [ ] `.env` ファイルの環境変数が正しく設定されているか確認
- [ ] Google OAuth設定（Client ID, Secret, Redirect URI）が正しいか確認
- [ ] データベース接続が正常に動作するか確認
- [ ] ブラウザの開発者ツールでエラーレスポンスを確認



