# Google OAuth設定の確認とセットアップ

## 問題の可能性

他の人のGoogle API（OAuth Client ID/Secret）を使っている場合、以下の問題が発生する可能性があります：

1. **リダイレクトURIが登録されていない**
   - 他の人のGoogle Cloud Consoleで、あなたのリダイレクトURIが登録されていない
   - Googleがリダイレクトを拒否する

2. **APIキーの所有者が異なる**
   - 他の人のアカウントで作成されたAPIキー
   - アクセス権限の問題

3. **APIが有効化されていない**
   - 必要なAPI（Google+ API、OAuth 2.0）が有効になっていない

## 確認方法

### 1. `.env` ファイルの確認

`C:\ksuns_back\.env` を開いて、以下の設定を確認：

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=...
```

これらの値が設定されているか、正しいか確認してください。

### 2. Google Cloud Consoleでの確認

現在使用しているGoogle OAuth設定が、あなたのアカウントで作成されたものか確認：

1. **Google Cloud Console** にアクセス: https://console.cloud.google.com/
2. プロジェクトを選択（または新規作成）
3. **APIとサービス** > **認証情報** を開く
4. **OAuth 2.0 クライアント ID** を確認
   - `.env` の `GOOGLE_CLIENT_ID` と一致するか
   - このクライアントIDがあなたのアカウントで作成されたものか

### 3. リダイレクトURIの確認

Google Cloud Consoleで、リダイレクトURIが正しく登録されているか確認：

1. **OAuth 2.0 クライアント ID** をクリック
2. **承認済みのリダイレクト URI** を確認
3. 以下のURIが登録されているか確認：

**ローカル環境の場合**:
```
http://localhost:8000/auth/google/callback
```

**Azure環境の場合**:
```
https://your-backend-domain.com/auth/google/callback
```

`.env` の `GOOGLE_REDIRECT_URI` と一致している必要があります。

## 解決方法

### 方法1: 自分のGoogleアカウントでAPIを作成（推奨）

1. **Google Cloud Console** にアクセス: https://console.cloud.google.com/
2. 新しいプロジェクトを作成（または既存のプロジェクトを選択）
3. **APIとサービス** > **有効なAPI** で以下を有効化：
   - Google+ API（またはGoogle Identity API）
   - OAuth 2.0 API
4. **認証情報** > **認証情報を作成** > **OAuth 2.0 クライアント ID**
5. アプリケーションの種類を選択（**ウェブアプリケーション**）
6. **承認済みのリダイレクト URI** に以下を追加：
   - ローカル: `http://localhost:8000/auth/google/callback`
   - Azure: `https://your-backend-domain.com/auth/google/callback`
7. **作成** をクリック
8. **クライアント ID** と **クライアント シークレット** をコピー
9. `.env` ファイルに設定：

```env
GOOGLE_CLIENT_ID=あなたのクライアントID
GOOGLE_CLIENT_SECRET=あなたのクライアントシークレット
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback  # ローカルの場合
# または
GOOGLE_REDIRECT_URI=https://your-backend-domain.com/auth/google/callback  # Azureの場合
```

### 方法2: 既存のAPIキーを使用する場合

他の人のAPIキーを使い続ける場合：

1. **リダイレクトURIを追加してもらう**
   - Google Cloud Consoleの所有者に依頼
   - あなたのリダイレクトURIを追加してもらう

2. **権限を確認**
   - あなたがそのプロジェクトにアクセスできるか確認
   - 必要に応じて、プロジェクトへのアクセス権限を付与してもらう

## 必要なAPIの有効化

Google OAuthを使用するには、以下のAPIが有効になっている必要があります：

1. **Google+ API** または **Google Identity API**
2. **OAuth 2.0 API**

有効化方法：
1. Google Cloud Console > **APIとサービス** > **ライブラリ**
2. 上記のAPIを検索
3. **有効にする** をクリック

## 設定の確認手順

### ステップ1: `.env` ファイルの確認

```bash
# C:\ksuns_back\.env を開く
notepad C:\ksuns_back\.env
```

以下の設定が正しいか確認：
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

### ステップ2: Google Cloud Consoleでの確認

1. https://console.cloud.google.com/ にアクセス
2. プロジェクトを選択
3. **APIとサービス** > **認証情報**
4. OAuth 2.0 クライアント IDを確認
5. リダイレクトURIが正しく登録されているか確認

### ステップ3: テスト

1. バックエンドアプリを起動
2. ブラウザで `/auth/google/url` にアクセス
3. 返されたURLでGoogleログインを試行
4. エラーが発生するか確認

## よくあるエラー

### `redirect_uri_mismatch`

**原因**: リダイレクトURIが登録されていない、または一致していない

**解決方法**:
- Google Cloud ConsoleでリダイレクトURIを追加
- `.env` の `GOOGLE_REDIRECT_URI` と一致させる

### `invalid_client`

**原因**: クライアントIDまたはシークレットが間違っている

**解決方法**:
- `.env` の設定を確認
- Google Cloud Consoleで正しい値を確認

### `access_denied`

**原因**: ユーザーが認証を拒否した、またはAPIが有効化されていない

**解決方法**:
- 必要なAPIが有効化されているか確認
- ユーザーが認証を許可したか確認

## まとめ

- **自分のGoogleアカウントでAPIを作成することを強く推奨**
- リダイレクトURIが正しく登録されているか確認
- 必要なAPIが有効化されているか確認
- `.env` ファイルの設定が正しいか確認



