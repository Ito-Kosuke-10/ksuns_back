# ログ確認手順

## 改善内容

以下の改善を行いました：

1. **詳細なログの追加**
   - `google_callback` 関数の各ステップでログを出力
   - エラー発生時にスタックトレースを記録

2. **エラーハンドリングの強化**
   - すべての例外をキャッチ
   - データベースエラー（IntegrityError, DatabaseError）を適切に処理

3. **ログレベルの変更**
   - `INFO` → `DEBUG` に変更（詳細なログを出力）

## ログの確認方法

### ローカル環境

1. **バックエンドアプリを再起動**
   ```bash
   cd C:\ksuns_back
   python -m uvicorn app.main:app --reload
   ```

2. **Googleログインを試行**
   - ブラウザでGoogleログインを試行
   - ターミナルに詳細なログが表示されます

3. **ログを確認**
   - 以下のようなログが表示されます：
     ```
     INFO: Google callback started
     DEBUG: Callback params: code=..., state=..., allow_create=...
     DEBUG: Token endpoint: https://oauth2.googleapis.com/token
     DEBUG: Redirect URI: http://localhost:8000/auth/google/callback
     INFO: Google token exchange response status: 200
     ...
     ```

### Azure環境

1. **Azure Portalにアクセス**
   - App Serviceリソースを選択
   - **監視** > **ログストリーム** を開く

2. **Googleログインを試行**
   - ブラウザでGoogleログインを試行
   - ログストリームに詳細なログが表示されます

3. **または、App Service ログを確認**
   - **監視** > **App Service ログ** を開く
   - ログファイルをダウンロードして確認

## 確認すべきログメッセージ

### 正常な場合

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
DEBUG: Creating access and refresh tokens
INFO: Google login successful - redirecting to: ...
```

### エラーが発生した場合

#### Google OAuth APIエラーの場合
```
ERROR: Google OAuth token exchange failed. Status: 400, Response: {"error": "redirect_uri_mismatch", ...}
```

#### データベースエラーの場合
```
ERROR: Database integrity error (likely duplicate user): ...
ERROR: Database error: ...
```

#### その他のエラーの場合
```
ERROR: Unexpected error in google_callback: ...
```

## エラーメッセージの見方

### `redirect_uri_mismatch`
- **原因**: リダイレクトURIがGoogle Cloud Consoleで登録されていない
- **解決方法**: Google Cloud ConsoleでリダイレクトURIを追加

### `Database integrity error`
- **原因**: データベースの制約違反（例: 同じgoogle_subやemailが既に存在）
- **解決方法**: データベースの状態を確認

### `Database error`
- **原因**: データベース接続エラー、テーブルが存在しないなど
- **解決方法**: データベース接続とテーブルの存在を確認

### `Unexpected error`
- **原因**: 予期しないエラー
- **解決方法**: ログのスタックトレースを確認

## 次のステップ

1. **バックエンドアプリを再起動**
2. **Googleログインを試行**
3. **ログを確認**して、実際のエラーメッセージを特定
4. **エラーメッセージに基づいて対応**

## 注意事項

- ログレベルを `DEBUG` に変更したため、大量のログが出力される可能性があります
- 本番環境では、必要に応じてログレベルを `INFO` に戻すことを検討してください
- ログには機密情報（トークンなど）が含まれる可能性があるため、注意してください



