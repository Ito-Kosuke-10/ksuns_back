# ログ確認のための改善完了

## 実施した改善

### 1. 詳細なログの追加

**`app/api/auth.py`** の `google_callback` 関数に以下を追加：
- 各ステップでのログ出力
- エラー発生時のスタックトレース記録
- Google OAuth APIのエラーレスポンスの詳細記録

### 2. エラーハンドリングの強化

**`app/api/auth.py`** で以下を追加：
- `IntegrityError`（データベース制約違反）のキャッチ
- `DatabaseError`（データベース接続エラー）のキャッチ
- すべての例外をキャッチしてログに記録

**`app/services/auth.py`** で以下を追加：
- データベース操作時のログ出力
- エラー発生時のロールバック処理
- 詳細なエラーログ

### 3. ログレベルの変更

**`app/core/logging_config.py`** で：
- ログレベルを `INFO` → `DEBUG` に変更
- より詳細なログを出力

### 4. グローバル例外ハンドラーの追加

**`app/main.py`** で：
- すべての未処理の例外をキャッチ
- 詳細なログを記録

## 次のステップ

### 1. バックエンドアプリを再起動

```bash
cd C:\ksuns_back
python -m uvicorn app.main:app --reload
```

### 2. Googleログインを試行

ブラウザでGoogleログインを試行してください。

### 3. ログを確認

ターミナルに以下のようなログが表示されます：

#### 正常な場合
```
INFO: Google callback started
DEBUG: Callback params: code=..., state=..., allow_create=...
DEBUG: Token endpoint: https://oauth2.googleapis.com/token
DEBUG: Redirect URI: http://localhost:8000/auth/google/callback
INFO: Google token exchange response status: 200
DEBUG: ID token received: True
DEBUG: Decoded token - sub: ..., email: ...
INFO: Attempting to get or create user - google_sub: ..., email: ..., allow_create: ...
INFO: User found/created successfully - user_id: ..., email: ...
INFO: Google login successful - redirecting to: ...
```

#### エラーが発生した場合
```
ERROR: Google OAuth token exchange failed. Status: 400, Response: {"error": "redirect_uri_mismatch", ...}
# または
ERROR: Database integrity error (likely duplicate user): ...
# または
ERROR: Database error: ...
# または
ERROR: Unexpected error in google_callback: ...
```

## 確認すべきポイント

### 1. `/auth/google/callback` へのリクエストが記録されているか

ログに `INFO: Google callback started` が表示されていれば、リクエストは到達しています。

### 2. どのステップでエラーが発生しているか

ログの最後のメッセージを確認：
- `Google token exchange response status: 200` → Google API呼び出しは成功
- `Attempting to get or create user` → データベース操作を試行中
- `Database error` → データベースエラーが発生

### 3. エラーメッセージの内容

エラーメッセージから原因を特定：
- `redirect_uri_mismatch` → リダイレクトURIの不一致
- `Database integrity error` → データベース制約違反
- `Database error` → データベース接続エラー

## よくあるエラーと対処法

### `redirect_uri_mismatch`
- **原因**: Google Cloud ConsoleでリダイレクトURIが登録されていない
- **対処**: Google Cloud ConsoleでリダイレクトURIを追加

### `Database integrity error`
- **原因**: 同じ `google_sub` や `email` が既に存在
- **対処**: データベースの状態を確認

### `Database error` または `Table doesn't exist`
- **原因**: テーブルが存在しない、またはデータベース接続エラー
- **対処**: テーブルを作成、またはデータベース接続を確認

## ログの出力例

### ケース1: リダイレクトURIの不一致
```
INFO: Google callback started
DEBUG: Token endpoint: https://oauth2.googleapis.com/token
DEBUG: Redirect URI: http://localhost:8000/auth/google/callback
INFO: Google token exchange response status: 400
ERROR: Google OAuth token exchange failed. Status: 400, Response: {"error": "redirect_uri_mismatch", "error_description": "The redirect URI in the request does not match the ones authorized for the OAuth client."}
```

### ケース2: データベーステーブルが存在しない
```
INFO: Google callback started
...
INFO: Attempting to get or create user - google_sub: ..., email: ...
ERROR: Database error: (pymysql.err.ProgrammingError) (1146, "Table 'ksuns_db.users' doesn't exist")
```

### ケース3: データベース接続エラー
```
INFO: Google callback started
...
INFO: Attempting to get or create user - google_sub: ..., email: ...
ERROR: Database error: (pymysql.err.OperationalError) (2003, "Can't connect to MySQL server")
```

## まとめ

- 詳細なログが出力されるようになりました
- エラーの詳細が分かるようになりました
- 問題の特定がしやすくなりました

**次のステップ**: バックエンドアプリを再起動して、Googleログインを試行し、ログを確認してください。



