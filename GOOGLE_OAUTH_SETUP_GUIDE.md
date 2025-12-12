# Google OAuth 設定ガイド

## 概要
このガイドでは、Google Cloud ConsoleでGoogle OAuth認証を設定する手順を説明します。

## ステップ1: Google Cloud Consoleでプロジェクトを作成

### 1.1 Google Cloud Consoleにアクセス
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. Googleアカウントでログイン

### 1.2 プロジェクトを作成
1. 画面上部のプロジェクト選択ドロップダウンをクリック
2. 「新しいプロジェクト」をクリック
3. プロジェクト名を入力（例：`ksuns-app`）
4. 「作成」をクリック
5. プロジェクトが作成されたら、そのプロジェクトを選択

## ステップ2: OAuth同意画面を設定

### 2.1 OAuth同意画面にアクセス
1. 左メニューから「APIとサービス」→「OAuth同意画面」を選択

### 2.2 ユーザータイプを選択
- **外部**を選択（一般ユーザーが使用する場合）
- **内部**を選択（Google Workspace内のみで使用する場合）
- 「作成」をクリック

### 2.3 アプリ情報を入力
- **アプリ名**: アプリケーション名（例：`KSUNS`）
- **ユーザーサポートメール**: あなたのメールアドレス
- **アプリのロゴ**: 任意（オプション）
- **アプリのホームページ**: アプリのURL（例：`https://your-app.azurewebsites.net`）
- **アプリのプライバシーポリシーへのリンク**: プライバシーポリシーのURL（任意）
- **アプリの利用規約へのリンク**: 利用規約のURL（任意）
- **承認済みのドメイン**: 任意（オプション）

### 2.4 スコープを設定
- 「スコープを追加または削除」をクリック
- 以下のスコープを追加：
  - `openid`
  - `https://www.googleapis.com/auth/userinfo.email`
  - `https://www.googleapis.com/auth/userinfo.profile`
- 「更新」→「保存して次へ」をクリック

### 2.5 テストユーザーを追加（外部の場合）
- 「テストユーザー」セクションで「+ ADD USERS」をクリック
- テスト用のGoogleアカウントのメールアドレスを追加
- 「保存して次へ」をクリック

### 2.6 概要を確認
- 設定内容を確認
- 「ダッシュボードに戻る」をクリック

## ステップ3: OAuth 2.0 クライアント IDを作成

### 3.1 認証情報ページにアクセス
1. 左メニューから「APIとサービス」→「認証情報」を選択

### 3.2 OAuth 2.0 クライアント IDを作成
1. 画面上部の「+ 認証情報を作成」をクリック
2. 「OAuth クライアント ID」を選択

### 3.3 アプリケーションの種類を選択
- **アプリケーションの種類**: 「ウェブアプリケーション」を選択

### 3.4 名前を設定
- **名前**: クライアントIDの名前（例：`KSUNS Web Client`）

### 3.5 承認済みのリダイレクト URIを追加

#### ローカル環境用
```
http://localhost:8000/auth/google/callback
```

#### Azure環境用
```
https://your-app-backend.azurewebsites.net/auth/google/callback
```
※ `your-app-backend` は実際のAzure App Service名に置き換えてください

#### 両方追加する場合
両方のURIを追加してください（複数追加可能）

### 3.6 作成
1. 「作成」をクリック
2. **クライアント ID**と**クライアント シークレット**が表示されます
3. **必ずこの情報をコピーして保存してください**（シークレットは後で表示できません）

## ステップ4: 環境変数を設定

### 4.1 ローカル環境（.envファイル）

`C:\ksuns_back\.env` ファイルを開き、以下の環境変数を設定：

```env
GOOGLE_CLIENT_ID=あなたのクライアントID
GOOGLE_CLIENT_SECRET=あなたのクライアントシークレット
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

### 4.2 Azure環境

1. [Azure Portal](https://portal.azure.com/)にログイン
2. App Service（バックエンド）を開く
3. 左メニューから「構成」を選択
4. 「アプリケーション設定」タブを開く
5. 以下の環境変数を追加/更新：
   - `GOOGLE_CLIENT_ID`: あなたのクライアントID
   - `GOOGLE_CLIENT_SECRET`: あなたのクライアントシークレット
   - `GOOGLE_REDIRECT_URI`: `https://your-app-backend.azurewebsites.net/auth/google/callback`
6. 「保存」をクリック
7. App Serviceを再起動（「概要」→「再起動」）

## ステップ5: 動作確認

### 5.1 ローカル環境で確認
1. バックエンドを起動
   ```bash
   cd C:\ksuns_back
   python -m uvicorn app.main:app --reload
   ```
2. フロントエンドを起動
   ```bash
   cd C:\ksuns_front
   npm run dev
   ```
3. ブラウザでログインページを開く
4. 「Google でログイン」をクリック
5. Googleの認証画面が表示され、ログインできることを確認

### 5.2 Azure環境で確認
1. Azure PortalでApp Serviceを再起動
2. フロントエンドからGoogleログインを試行
3. 正常にログインできることを確認

## トラブルシューティング

### エラー: `redirect_uri_mismatch`
- **原因**: Google Cloud Consoleで設定したリダイレクトURIと、環境変数の`GOOGLE_REDIRECT_URI`が一致していない
- **解決方法**: 
  1. Google Cloud ConsoleでリダイレクトURIを確認
  2. 環境変数の`GOOGLE_REDIRECT_URI`を確認
  3. 完全に一致していることを確認（末尾のスラッシュ、プロトコルなど）

### エラー: `invalid_client`
- **原因**: Client IDまたはClient Secretが間違っている
- **解決方法**: 
  1. Google Cloud ConsoleでクライアントIDとシークレットを確認
  2. 環境変数を再設定
  3. バックエンドを再起動

### エラー: `access_denied`
- **原因**: テストユーザーが追加されていない（外部アプリの場合）
- **解決方法**: OAuth同意画面でテストユーザーを追加

### エラー: `unauthorized_client`
- **原因**: このクライアントIDはこのリダイレクトURIを使用できない
- **解決方法**: Google Cloud ConsoleでリダイレクトURIを追加

## 重要な注意事項

1. **クライアントシークレットの管理**
   - クライアントシークレットは機密情報です
   - コードに直接書かないでください
   - 環境変数として管理してください
   - GitHubなどにコミットしないでください

2. **リダイレクトURIの一致**
   - Google Cloud Consoleで設定したリダイレクトURIと、環境変数の`GOOGLE_REDIRECT_URI`が完全に一致している必要があります
   - プロトコル（http/https）、ホスト名、パス、末尾のスラッシュなど、すべて一致させる必要があります

3. **本番環境と開発環境**
   - 本番環境（Azure）と開発環境（ローカル）で異なるリダイレクトURIを使用する場合、Google Cloud Consoleで両方を追加してください
   - 環境変数も環境ごとに適切に設定してください

## 参考リンク

- [Google Cloud Console](https://console.cloud.google.com/)
- [OAuth 2.0 for Client-side Web Applications](https://developers.google.com/identity/protocols/oauth2/javascript-implicit-flow)
- [Google Identity Platform](https://developers.google.com/identity)



