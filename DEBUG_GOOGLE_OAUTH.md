# Google OAuth エラーデバッグ手順

## Internal Server Error が発生する場合の確認事項

### 1. 環境変数が正しく読み込まれているか確認

#### ローカル環境
```bash
cd C:\ksuns_back
python -c "from app.core.config import get_settings; s = get_settings(); print(f'Client ID: {s.google_client_id[:20]}...'); print(f'Redirect URI: {s.google_redirect_uri}')"
```

#### 確認すべき項目
- `GOOGLE_CLIENT_ID` が正しく設定されているか
- `GOOGLE_CLIENT_SECRET` が正しく設定されているか
- `GOOGLE_REDIRECT_URI` が正しく設定されているか

### 2. リダイレクトURIの一致を確認

#### ローカル環境
- `.env` の `GOOGLE_REDIRECT_URI`: `http://localhost:8000/auth/google/callback`
- Google Cloud Consoleの「承認済みのリダイレクト URI」にも同じURIが登録されているか

#### Azure環境
- Azure Portalの環境変数 `GOOGLE_REDIRECT_URI`: `https://your-app-backend.azurewebsites.net/auth/google/callback`
- Google Cloud Consoleの「承認済みのリダイレクト URI」にも同じURIが登録されているか

**重要**: 完全に一致している必要があります（プロトコル、ホスト名、パス、末尾のスラッシュなど）

### 3. バックエンドを再起動

#### ローカル環境
```bash
cd C:\ksuns_back
# 現在のプロセスを停止（Ctrl+C）
python -m uvicorn app.main:app --reload
```

#### Azure環境
1. Azure Portal → App Service（バックエンド）を開く
2. 「概要」→「再起動」をクリック

### 4. ログを確認

#### ローカル環境
- ターミナルでuvicornを起動したウィンドウを確認
- エラーメッセージとスタックトレースを確認

#### Azure環境
1. Azure Portal → App Service（バックエンド）を開く
2. 「ログストリーム」または「ログ」を開く
3. リアルタイムでログを確認

### 5. 開発者ツールでエラーを確認

1. ブラウザでF12キーを押して開発者ツールを開く
2. 「Network」タブを開く
3. Googleログインを試行
4. `/auth/google/callback` リクエストを選択
5. 「Response」タブでエラーの詳細を確認

### 6. よくあるエラーと対処法

#### エラー: `redirect_uri_mismatch`
- **原因**: Google Cloud Consoleで設定したリダイレクトURIと、環境変数の`GOOGLE_REDIRECT_URI`が一致していない
- **対処**: 
  1. Google Cloud ConsoleでリダイレクトURIを確認
  2. 環境変数の`GOOGLE_REDIRECT_URI`を確認
  3. 完全に一致していることを確認

#### エラー: `invalid_client`
- **原因**: Client IDまたはClient Secretが間違っている
- **対処**: 
  1. Google Cloud ConsoleでクライアントIDとシークレットを確認
  2. 環境変数を再設定
  3. バックエンドを再起動

#### エラー: `Failed to exchange code with Google`
- **原因**: Google OAuthのトークン交換に失敗
- **対処**: 
  1. 開発者ツールのNetworkタブでエラーの詳細を確認
  2. Google Cloud Consoleで設定を確認
  3. ログを確認して詳細なエラーメッセージを確認

### 7. 設定チェックリスト

- [ ] Google Cloud Consoleでプロジェクトを作成
- [ ] OAuth同意画面を設定
- [ ] OAuth 2.0 クライアント IDを作成
- [ ] リダイレクトURIをGoogle Cloud Consoleに追加
- [ ] ローカル環境の`.env`ファイルに環境変数を設定
- [ ] Azure環境の環境変数を設定
- [ ] リダイレクトURIが完全に一致していることを確認
- [ ] バックエンドを再起動
- [ ] Googleログインを試行
- [ ] ログを確認



