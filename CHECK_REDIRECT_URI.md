# リダイレクトURI確認チェックリスト

## 現在の設定

### ローカル環境
- `.env` の `GOOGLE_REDIRECT_URI`: `http://localhost:8000/auth/google/callback`

### Azure環境
- Azure Portal の環境変数 `GOOGLE_REDIRECT_URI`: `https://ksuns-app-backend-a6gng2g8g3dqbfg3.canadacentral-01.azurewebsites.net/auth/google/callback`

## 確認すべき項目

### 1. Google Cloud ConsoleでリダイレクトURIを確認

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. プロジェクトを選択
3. 「APIとサービス」→「認証情報」を開く
4. OAuth 2.0 クライアント IDをクリック
5. 「承認済みのリダイレクト URI」を確認

**重要**: 以下のURIが**両方とも**登録されている必要があります：

- `http://localhost:8000/auth/google/callback` （ローカル用）
- `https://ksuns-app-backend-a6gng2g8g3dqbfg3.canadacentral-01.azurewebsites.net/auth/google/callback` （Azure用）

### 2. 完全一致の確認

リダイレクトURIは**完全に一致**している必要があります：

- ✅ プロトコル: `http://` または `https://`
- ✅ ホスト名: `localhost:8000` または `ksuns-app-backend-a6gng2g8g3dqbfg3.canadacentral-01.azurewebsites.net`
- ✅ パス: `/auth/google/callback`
- ✅ 末尾のスラッシュ: なし（`/auth/google/callback/` ではない）

### 3. よくある間違い

- ❌ `http://localhost:8000/auth/google/callback/` （末尾にスラッシュがある）
- ❌ `https://localhost:8000/auth/google/callback` （ローカルでhttpsを使っている）
- ❌ `http://ksuns-app-backend.../auth/google/callback` （Azureでhttpを使っている）
- ❌ `/auth/google/callback` （プロトコルとホスト名がない）

## 次のステップ

1. Google Cloud ConsoleでリダイレクトURIを確認
2. 必要に応じてリダイレクトURIを追加
3. バックエンドを再起動
4. Googleログインを再試行



