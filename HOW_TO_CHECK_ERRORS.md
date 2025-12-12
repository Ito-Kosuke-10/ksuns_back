# エラーメッセージの確認方法

## エラーメッセージが表示される場所

### 1. ブラウザの画面（フロントエンド）
- ログインページでエラーが発生した場合、画面上にエラーメッセージが表示されます
- 例：「ログインがキャンセルされました。もう一度お試しください。」

### 2. バックエンドのターミナル（最も重要！）
- **uvicornを起動したターミナルウィンドウ**にエラーの詳細が表示されます
- エラーの詳細情報（スタックトレースなど）はここに表示されます

### 3. ブラウザの開発者ツール（F12）
- F12キーを押して開発者ツールを開く
- 「Console」タブでJavaScriptエラーを確認
- 「Network」タブでAPIリクエスト/レスポンスを確認

## エラーログの確認手順

### ステップ1: バックエンドを起動
```bash
cd C:\ksuns_back
python -m uvicorn app.main:app --reload
```

### ステップ2: ターミナルウィンドウを確認
- このターミナルウィンドウに以下のようなログが表示されます：

**正常な場合**:
```
INFO: Google callback started
DEBUG: Callback params: code=present, error=None, ...
INFO: Google token exchange response status: 200
INFO: User found/created successfully - user_id: 1, email: example@example.com
INFO: Google login successful - redirecting to: ...
```

**エラーが発生した場合**:
```
ERROR: Unhandled exception: ...
Traceback (most recent call last):
  File "...", line ..., in google_callback
    ...
Error: エラーの詳細
```

### ステップ3: エラーの種類を確認

#### 1. Google OAuthエラー
```
ERROR: Google OAuth error: redirect_uri_mismatch
```
→ Google OAuthの設定（リダイレクトURI）が正しくない可能性があります

#### 2. データベースエラー
```
ERROR: Database error: ...
```
→ データベース接続またはテーブルが存在しない可能性があります

#### 3. トークンエラー
```
ERROR: Missing id_token from Google response
```
→ Googleからのレスポンスに問題がある可能性があります

#### 4. その他のエラー
```
ERROR: Unhandled exception: ...
```
→ スタックトレースを確認して、どの行でエラーが発生しているか確認してください

## よくあるエラーと対処法

### 1. `{"detail":[{"type":"missing","loc":["query","code"],"msg":"Field required"}]}`
- **原因**: Googleログインをキャンセルした場合に発生
- **対処**: これは正常な動作です。エラーメッセージが画面に表示されます

### 2. `Internal server Error`
- **原因**: バックエンドで予期しないエラーが発生
- **対処**: ターミナルのログを確認して、エラーの詳細を特定してください

### 3. `redirect_uri_mismatch`
- **原因**: Google OAuthの設定でリダイレクトURIが一致していない
- **対処**: Google Cloud ConsoleでリダイレクトURIを確認・修正してください

## ログレベルの確認

現在のログレベルは `DEBUG` に設定されているため、詳細な情報が表示されます。

ログの形式:
```
2024-01-01 12:00:00 [DEBUG] app.api.auth - Callback params: code=present, error=None, ...
2024-01-01 12:00:01 [INFO] app.api.auth - Google callback started
2024-01-01 12:00:02 [ERROR] app.api.auth - Google OAuth error: ...
```

## トラブルシューティング

### ログが表示されない場合
1. バックエンドが起動しているか確認
2. 正しいターミナルウィンドウを見ているか確認
3. ログレベルが `DEBUG` に設定されているか確認（`app/core/logging_config.py`）

### エラーの詳細がわからない場合
1. ターミナルのログをスクリーンショットで保存
2. エラーが発生した時刻を記録
3. どの操作を行ったときにエラーが発生したか記録



