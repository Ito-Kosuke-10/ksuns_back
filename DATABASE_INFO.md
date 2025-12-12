# データベース情報

## データベースの種類

このアプリケーションは **MySQL** を使用しています。

- **データベースエンジン**: MySQL
- **接続方式**: SQLAlchemy（非同期）
- **ドライバ**: `asyncmy` (MySQL用の非同期ドライバ)

## データの格納場所

データは **MySQLサーバー** に格納されます。ローカル環境では、以下のいずれかになります：

1. **ローカルのMySQLサーバー**（`localhost` にインストールされている場合）
2. **Dockerコンテナ**（MySQLをDockerで実行している場合）
3. **リモートのMySQLサーバー**（Azure Database for MySQL など）

## 接続情報の設定

接続情報は `.env` ファイルで管理されています。

### 必要な環境変数

`C:\ksuns_back\.env` ファイルに以下の設定が必要です：

```env
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=ksuns_db
```

### 接続URLの形式

アプリケーションは以下の形式でMySQLに接続します：

```
mysql+asyncmy://{user}:{password}@{host}:{port}/{database_name}
```

例：
```
mysql+asyncmy://root:password@localhost:3306/ksuns_db
```

## データベースのテーブル構造

以下のテーブルが定義されています（`app/models/` 配下のモデルファイル参照）：

### 主要なテーブル

1. **users** - ユーザー情報
   - `id`, `google_sub`, `email`, `display_name`, `created_at`, `updated_at`

2. **simple_simulation_sessions** - 簡易シミュレーションのセッション
   - `id`, `user_id`, `guest_session_token`, `status`, `started_at`, `completed_at`

3. **simple_simulation_answers** - 簡易シミュレーションの回答
   - `id`, `session_id`, `question_code`, `answer_values`

4. **simple_simulation_results** - 簡易シミュレーションの結果
   - `id`, `session_id`, `axis_scores`, `funds_comment_category`, `store_story_text`

5. **planning_axes** - レーダーチャートの軸情報
   - `id`, `code`, `name`, `description`

6. **axis_scores** - 軸のスコア
   - `id`, `user_id`, `axis_id`, `score`, `level1_completion_ratio`, `level2_completion_ratio`

7. **detail_question_answers** - 詳細質問の回答
   - `id`, `user_id`, `question_code`, `answer`

8. **deep_questions** - 深掘り質問
   - `id`, `user_id`, `axis_code`, `question_text`, `answer_text`

9. **qa_conversations** - なんでも質問の会話
   - `id`, `user_id`, `context_type`, `axis_code`, `question_text`, `answer_text`

10. **owner_notes** - オーナーノート
    - `id`, `user_id`, `content`

11. **store_stories** - 店のストーリー
    - `id`, `user_id`, `source`, `content`

12. **summaries** - サマリー
    - `id`, `user_id`, `summary_type`, `content`

## ローカル環境でのデータベースセットアップ

### 1. MySQLのインストール（未インストールの場合）

#### Windowsの場合

1. **MySQL公式サイトからダウンロード**
   - https://dev.mysql.com/downloads/mysql/
   - MySQL Installer for Windows をダウンロード

2. **インストール**
   - インストーラーを実行
   - 開発環境用の設定を選択
   - rootパスワードを設定

3. **MySQLサービスの起動**
   - Windowsのサービスから「MySQL」を起動

#### Dockerを使用する場合（推奨）

```bash
# MySQLコンテナを起動
docker run --name ksuns-mysql \
  -e MYSQL_ROOT_PASSWORD=your_password \
  -e MYSQL_DATABASE=ksuns_db \
  -e MYSQL_USER=ksuns_user \
  -e MYSQL_PASSWORD=ksuns_password \
  -p 3306:3306 \
  -d mysql:8.0
```

### 2. データベースの作成

MySQLに接続してデータベースを作成：

```sql
CREATE DATABASE ksuns_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ksuns_user'@'localhost' IDENTIFIED BY 'ksuns_password';
GRANT ALL PRIVILEGES ON ksuns_db.* TO 'ksuns_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 環境変数の設定

`C:\ksuns_back\.env` ファイルを作成：

```env
DB_USER=ksuns_user
DB_PASSWORD=ksuns_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=ksuns_db
```

### 4. テーブルの作成

現在、マイグレーションツール（Alembic）は設定されていないようです。

#### 方法1: SQLAlchemyで自動生成（開発環境のみ）

```python
# 一時的なスクリプトを作成
from app.core.db import engine
from app.models.base import Base
from app.models import *  # すべてのモデルをインポート

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 実行
import asyncio
asyncio.run(create_tables())
```

#### 方法2: SQLファイルから手動実行

モデル定義を元にSQLファイルを作成して実行

#### 方法3: Alembicを導入（推奨）

マイグレーションツールを導入して、テーブル作成とスキーマ変更を管理

## データの確認方法

### MySQLコマンドラインから確認

```bash
# MySQLに接続
mysql -u ksuns_user -p ksuns_db

# テーブル一覧を表示
SHOW TABLES;

# 特定のテーブルのデータを確認
SELECT * FROM users;
SELECT * FROM simple_simulation_sessions;
```

### データベース管理ツールを使用

- **MySQL Workbench**（公式ツール）
- **phpMyAdmin**（Webベース）
- **DBeaver**（クロスプラットフォーム）
- **TablePlus**（Mac/Windows）

接続情報：
- Host: `localhost`
- Port: `3306`
- User: `.env` の `DB_USER`
- Password: `.env` の `DB_PASSWORD`
- Database: `.env` の `DB_NAME`

## 現在のデータベース状態の確認

### 接続確認

バックエンドアプリケーションを起動して、エラーが出ないか確認：

```bash
cd C:\ksuns_back
python -m uvicorn app.main:app --reload
```

エラーが出る場合：
- データベースサーバーが起動しているか確認
- `.env` ファイルの設定が正しいか確認
- データベースが作成されているか確認

### テーブルの存在確認

```sql
-- MySQLに接続して実行
USE ksuns_db;
SHOW TABLES;
```

テーブルが存在しない場合、テーブルを作成する必要があります。

## トラブルシューティング

### 接続エラーが出る場合

1. **MySQLサーバーが起動しているか確認**
   ```bash
   # Windowsの場合
   net start MySQL
   
   # またはサービスから確認
   services.msc
   ```

2. **接続情報を確認**
   - `.env` ファイルの設定が正しいか
   - ユーザー名・パスワードが正しいか
   - ホスト・ポートが正しいか

3. **ファイアウォールの確認**
   - ローカルホストの場合は通常問題なし
   - リモートサーバーの場合はポート3306が開いているか確認

### テーブルが存在しない場合

- テーブル作成スクリプトを実行
- または、Alembicなどのマイグレーションツールを導入

## 次のステップ

1. **マイグレーションツールの導入**（推奨）
   - Alembicを導入して、テーブル作成とスキーマ変更を管理

2. **初期データの投入**
   - `planning_axes` テーブルに軸データを投入
   - その他のマスターデータを投入

3. **バックアップ戦略**
   - 定期的なバックアップ設定
   - 本番環境でのバックアップ方法の確立




