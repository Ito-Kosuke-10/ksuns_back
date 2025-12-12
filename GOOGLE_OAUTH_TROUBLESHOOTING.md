# Google OAuth トークン交換エラーのトラブルシューティング

## エラーメッセージ
`{"detail":"Failed to exchange code with Google"}`

## 考えられる原因

### 1. Google OAuth設定の問題

#### 確認すべき項目：
- **Client ID**: 正しく設定されているか
- **Client Secret**: 正しく設定されているか
- **Redirect URI**: Google Cloud Consoleで登録されているURIと一致しているか

#### 確認方法：
1. `.env` ファイルまたはAzureの環境変数を確認
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI`

2. Google Cloud Consoleで確認
   - [Google Cloud Console](https://console.cloud.google.com/)にログイン
   - 「APIとサービス」→「認証情報」を開く
   - OAuth 2.0 クライアント IDを確認
   - 「承認済みのリダイレクト URI」に `GOOGLE_REDIRECT_URI` が登録されているか確認

### 2. リダイレクトURIの不一致

#### よくある問題：
- ローカル: `http://localhost:8000/auth/google/callback`
- Azure: `https://your-app.azurewebsites.net/auth/google/callback`
- Google Cloud Consoleに登録されているURIと一致していない

#### 解決方法：
1. Google Cloud Consoleで、使用している環境（ローカルまたはAzure）のリダイレクトURIを追加
2. `.env` ファイルまたはAzureの環境変数で `GOOGLE_REDIRECT_URI` を正しく設定

### 3. 認証コードの有効期限切れ

#### 原因：
- Google OAuthの認証コードは一度しか使用できず、有効期限が短い（通常数分）
- ページをリロードしたり、時間が経過すると無効になる

#### 解決方法：
- エラーが発生したら、最初からGoogleログインを再度試行

### 4. ネットワークエラー

#### 原因：
- Google OAuth APIへの接続がタイムアウトまたは失敗

#### 解決方法：
- ネットワーク接続を確認
- ファイアウォールやプロキシの設定を確認

## デバッグ手順

### ステップ1: 環境変数を確認

**ローカル環境**:
```bash
cd C:\ksuns_back
# .env ファイルを確認
cat .env | grep GOOGLE
```

**Azure環境**:
1. Azure Portalにログイン
2. App Service（バックエンド）を開く
3. 「構成」→「アプリケーション設定」を開く
4. `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` を確認

### ステップ2: Google Cloud Consoleで設定を確認

1. [Google Cloud Console](https://console.cloud.google.com/)にログイン
2. プロジェクトを選択
3. 「APIとサービス」→「認証情報」を開く
4. OAuth 2.0 クライアント IDをクリック
5. 「承認済みのリダイレクト URI」を確認
   - ローカル: `http://localhost:8000/auth/google/callback`
   - Azure: `https://your-app.azurewebsites.net/auth/google/callback`

### ステップ3: ログを確認

**ローカル環境**:
- ターミナルでuvicornを起動したウィンドウを確認
- 以下のようなログが表示されます：
  ```
  ERROR: Google OAuth token exchange failed. Status: 400, Response: {"error": "invalid_grant", ...}
  ```

**Azure環境**:
1. Azure Portalにログイン
2. App Service（バックエンド）を開く
3. 「ログストリーム」または「ログ」を開く
4. リアルタイムでログを確認

### ステップ4: エラーの詳細を確認

開発者ツール（F12）のNetworkタブで：
1. `/auth/google/callback` リクエストを選択
2. 「Response」タブでエラーの詳細を確認
3. エラーメッセージに含まれる詳細情報を確認

## よくあるエラーパターン

### パターン1: `invalid_grant`
- **原因**: 認証コードが無効または期限切れ
- **解決方法**: 最初からGoogleログインを再度試行

### パターン2: `redirect_uri_mismatch`
- **原因**: リダイレクトURIが一致していない
- **解決方法**: Google Cloud ConsoleでリダイレクトURIを確認・修正

### パターン3: `invalid_client`
- **原因**: Client IDまたはClient Secretが間違っている
- **解決方法**: 環境変数を確認・修正

### パターン4: `unauthorized_client`
- **原因**: このクライアントIDはこのリダイレクトURIを使用できない
- **解決方法**: Google Cloud ConsoleでリダイレクトURIを追加

## 修正後の動作

修正後、エラーメッセージに詳細な情報が含まれるようになりました：
- Googleからのエラーレスポンスの詳細
- ネットワークエラーの詳細
- タイムアウトエラーの詳細

これにより、問題の原因をより簡単に特定できるようになります。



