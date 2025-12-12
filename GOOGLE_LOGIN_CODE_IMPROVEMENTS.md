# Googleログインのコード改善案

## 改善できる点

コード側を改善することで、以下が可能になります：

1. **エラーの詳細が分かるようになる**
   - どこでエラーが発生しているか特定できる
   - エラーメッセージが詳細になる

2. **一部の問題が解決する**
   - データベースエラーの適切な処理
   - より分かりやすいエラーメッセージ

3. **デバッグがしやすくなる**
   - ログで問題を追跡できる

ただし、**根本的な原因（リダイレクトURIの不一致など）はコード修正だけでは解決しません**。

## 改善案

### 改善1: エラーハンドリングの強化

現在の問題：
- `ValueError` しかキャッチしていない
- データベースエラーがキャッチされていない
- 予期しない例外がInternal Server Errorになる

改善後：
- すべての例外をキャッチ
- データベースエラーを適切に処理
- 詳細なエラーメッセージを返す

### 改善2: ログの追加

現在の問題：
- エラーが発生してもログに記録されない
- どこでエラーが発生しているか分からない

改善後：
- 各ステップでログを出力
- エラー発生時にスタックトレースを記録

### 改善3: Google OAuth APIエラーの詳細表示

現在の問題：
- Google APIのエラーレスポンスの詳細が失われる

改善後：
- エラーレスポンスの内容をログに記録
- より詳細なエラーメッセージを返す

### 改善4: データベースエラーの適切な処理

現在の問題：
- データベースエラーがキャッチされていない
- テーブルが存在しない場合のエラーが分からない

改善後：
- データベースエラーをキャッチ
- 適切なエラーメッセージを返す

## 実装例

### 改善後のコード（例）

```python
import logging
from sqlalchemy.exc import IntegrityError, DatabaseError

logger = logging.getLogger(__name__)

@router.get("/google/callback")
async def google_callback(
    code: str,
    response: Response,
    state: str | None = None,
    allow_create: bool = False,
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    logger.info("Google callback started")
    
    try:
        # Google OAuth API呼び出し
        token_endpoint = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=10) as client:
            token_res = await client.post(token_endpoint, data=payload)
        
        if token_res.status_code != 200:
            error_detail = token_res.text
            logger.error(f"Google OAuth token exchange failed: {error_detail}")
            redirect_url = f"{settings.frontend_url}/login?error=oauth_failed"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

        token_data = token_res.json()
        id_token = token_data.get("id_token")
        if not id_token:
            logger.error("Missing id_token from Google response")
            redirect_url = f"{settings.frontend_url}/login?error=missing_token"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

        # JWTデコード
        decoded = jwt.decode(id_token, options={"verify_signature": False, "verify_aud": False})
        sub = decoded.get("sub")
        email = decoded.get("email")
        name = decoded.get("name") or email

        if not sub or not email:
            logger.error("Invalid Google token payload")
            redirect_url = f"{settings.frontend_url}/login?error=invalid_token"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

        allow_create_flag = allow_create
        if state and state.startswith("allow_create:"):
            allow_create_flag = state.split("allow_create:")[1].lower() == "true"

        # ユーザー取得/作成
        try:
            user = await get_or_create_user(
                session=session,
                google_sub=sub,
                email=email,
                display_name=name,
                allow_create=allow_create_flag,
            )
            logger.info(f"User found/created: {user.id}")
        except ValueError as e:
            logger.warning(f"User creation not allowed: {e}")
            redirect_url = f"{settings.frontend_url}/login?error=signup_not_allowed"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
        except IntegrityError as e:
            logger.error(f"Database integrity error: {e}", exc_info=True)
            redirect_url = f"{settings.frontend_url}/login?error=database_error"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
        except DatabaseError as e:
            logger.error(f"Database error: {e}", exc_info=True)
            redirect_url = f"{settings.frontend_url}/login?error=database_error"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

        # トークン生成
        access_expires = timedelta(minutes=settings.access_token_ttl_min)
        refresh_expires = timedelta(days=settings.refresh_token_ttl_day)

        access_token = create_access_token(
            subject=str(user.id),
            secret=settings.jwt_secret,
            expires_delta=access_expires,
        )
        refresh_token = create_refresh_token(
            subject=str(user.id),
            secret=settings.jwt_secret,
            expires_delta=refresh_expires,
        )

        set_refresh_cookie(response, refresh_token, settings)
        redirect_url = f"{settings.frontend_url}/dashboard?access_token={access_token}"
        logger.info(f"Google login successful for user {user.id}")
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Unexpected error in google_callback: {e}", exc_info=True)
        redirect_url = f"{settings.frontend_url}/login?error=internal_error"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
```

## 改善の効果

### 改善前
- エラーが発生しても詳細が分からない
- Internal Server Errorが表示される
- ログに何も記録されない

### 改善後
- エラーの詳細がログに記録される
- ユーザーに分かりやすいエラーメッセージが表示される
- 問題の特定がしやすくなる

## 注意点

コード改善だけでは解決しない問題：

1. **リダイレクトURIの不一致**
   - Google Cloud Consoleでの設定が必要
   - コード修正だけでは解決しない

2. **環境変数の設定ミス**
   - `.env` ファイルの設定が必要
   - コード修正だけでは解決しない

3. **データベーステーブルの不存在**
   - テーブル作成が必要
   - コード修正だけでは解決しない（ただし、エラーメッセージで分かるようになる）

## 推奨される対応

1. **まずコードを改善**して、エラーの詳細を確認できるようにする
2. **ログを確認**して、実際のエラーメッセージを特定
3. **根本原因を解決**（リダイレクトURIの設定、テーブル作成など）

コード改善により、問題の特定がしやすくなり、適切な対応が取れるようになります。



