# Internal Server Error トラブルシューティング手順

## 現在の状況
- ✅ 環境変数は正しく読み込まれている
- ❌ ローカルでもAzureでもInternal Server Errorが発生

## 確認すべき項目

### 1. リダイレクトURIの確認（最重要）

#### 問題の可能性
現在、`.env`ファイルには**AzureのリダイレクトURI**が設定されています：
```
GOOGLE_REDIRECT_URI=https://ksuns-app-backend-a6gng2g8g3dqbfg3.canadacentral-01.azurewebsites.net/auth/google/callback
```

しかし、**ローカル環境**では以下のリダイレクトURIが必要です：
```
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

#### 解決方法

**ローカル環境用の.envファイルを確認・修正**：
1. `C:\ksuns_back\.env` を開く
2. `GOOGLE_REDIRECT_URI` を以下に変更：
   ```env
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
   ```
3. バックエンドを再起動

**Google Cloud Consoleで両方のURIを登録**：
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. プロジェクトを選択
3. 「APIとサービス」→「認証情報」を開く
4. OAuth 2.0 クライアント IDをクリック
5. 「承認済みのリダイレクト URI」に以下を**両方とも**追加：
   - `http://localhost:8000/auth/google/callback`
   - `https://ksuns-app-backend-a6gng2g8g3dqbfg3.canadacentral-01.azurewebsites.net/auth/google/callback`
6. 「保存」をクリック

### 2. エラーログの確認

#### ローカル環境
1. バックエンドを起動したターミナルウィンドウを確認
2. Googleログインを試行
3. 以下のようなログが表示されます：
   ```
   ERROR: Google OAuth token exchange failed. Status: 400, Response: {"error": "redirect_uri_mismatch", ...}
   ```
   または
   ```
   ERROR: Unhandled exception: ...
   Traceback (most recent call last):
     ...
   ```

#### Azure環境
1. Azure Portal → App Service（バックエンド）を開く
2. 「ログストリーム」または「ログ」を開く
3. Googleログインを試行
4. エラーログを確認

### 3. 開発者ツールでエラーを確認

1. ブラウザでF12キーを押して開発者ツールを開く
2. 「Network」タブを開く
3. Googleログインを試行
4. `/auth/google/callback` リクエストを選択
5. 「Response」タブでエラーの詳細を確認

### 4. よくあるエラーパターン

#### パターン1: `redirect_uri_mismatch`
```
{"error": "redirect_uri_mismatch", "error_description": "..."}
```
- **原因**: Google Cloud Consoleで設定したリダイレクトURIと、環境変数の`GOOGLE_REDIRECT_URI`が一致していない
- **解決方法**: 
  1. Google Cloud ConsoleでリダイレクトURIを確認
  2. 環境変数の`GOOGLE_REDIRECT_URI`を確認
  3. 完全に一致していることを確認

#### パターン2: `invalid_client`
```
{"error": "invalid_client", "error_description": "..."}
```
- **原因**: Client IDまたはClient Secretが間違っている
- **解決方法**: 
  1. Google Cloud ConsoleでクライアントIDとシークレットを確認
  2. 環境変数を再設定
  3. バックエンドを再起動

#### パターン3: `invalid_grant`
```
{"error": "invalid_grant", "error_description": "..."}
```
- **原因**: 認証コードが無効または期限切れ
- **解決方法**: 最初からGoogleログインを再度試行

### 5. 即座に試すべきこと

1. **ローカル環境の.envファイルを確認**
   ```bash
   cd C:\ksuns_back
   # .envファイルを開いて確認
   ```

2. **ローカル環境のリダイレクトURIを修正**
   ```env
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
   ```

3. **Google Cloud ConsoleでリダイレクトURIを確認・追加**
   - 両方のURIが登録されているか確認

4. **バックエンドを再起動**
   ```bash
   cd C:\ksuns_back
   python -m uvicorn app.main:app --reload
   ```

5. **Googleログインを再試行**
   - ローカル環境で試行
   - ターミナルのログを確認

## 次のステップ

1. 上記の手順を実行
2. エラーログの内容を確認
3. エラーメッセージを共有していただければ、より具体的な解決策を提案できます



