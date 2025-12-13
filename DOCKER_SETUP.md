# Docker MySQL セットアップガイド

このガイドでは、ローカル開発環境でDocker上のMySQLに接続して開発を進める手順を説明します。

## 📋 前提条件

- Docker Desktopがインストールされ、起動していること
- Python 3.11以上がインストールされていること
- 仮想環境（venv）が作成されていること

## 🚀 セットアップ手順

### 1. Dockerコンテナの起動

```bash
cd c:\ksuns_back
docker-compose up -d
```

コンテナが起動したことを確認：

```bash
docker ps
```

`ksuns_mysql` コンテナが `Up` 状態になっていることを確認してください。

### 2. .envファイルの設定

`.env.example` を参考に、`.env` ファイルを作成または更新してください。

**重要**: 以下の設定を確認してください：

```env
# Docker MySQL用の設定
DB_HOST=localhost
DB_PORT=3307
DB_USER=ksuns_user
DB_PASSWORD=ksuns_password
DB_NAME=ksuns

# DB接続をスキップする設定は無効化（コメントアウトまたは削除）
# ENV=LOCAL_DEV_SKIP_AUTH  ← この行を削除またはコメントアウト
```

### 3. 仮想環境のアクティブ化

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat

# Linux/Mac
source .venv/bin/activate
```

### 4. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 5. テーブルの作成

すべてのテーブルを一括作成します：

```bash
python create_all_tables.py
```

このスクリプトは、SQLAlchemyのモデル定義から自動的にすべてのテーブルを作成します。

**作成されるテーブル**:
- ユーザー管理: `users`
- 軸関連: `planning_axes`, `axis_steps`, `axis_answers`, `axis_scores`
- Deep Questions (8軸): `concept_answers`, `revenue_forecast_answers`, `funding_plan_answers`, `operation_answers`, `location_answers`, `interior_exterior_answers`, `marketing_answers`, `menu_answers`
- その他: `business_plan_drafts`, `simple_simulation_sessions`, など

### 6. テーブルの確認

テーブルが正しく作成されたか確認します：

```bash
python verify_tables_local.py
```

このスクリプトは、以下の情報を表示します：
- データベース内のすべてのテーブル一覧
- カテゴリ別のテーブル存在確認
- 各テーブルのレコード数

## 🔍 トラブルシューティング

### コンテナが起動しない場合

```bash
# コンテナのログを確認
docker-compose logs mysql

# コンテナを再起動
docker-compose restart mysql
```

### データベース接続エラーの場合

1. `.env` ファイルの設定を確認（`DB_PORT=3307`になっているか）
2. Dockerコンテナが起動しているか確認: `docker ps`
3. ポート3307が使用されていないか確認

### テーブル作成エラーの場合

```bash
# データベースに直接接続して確認
docker exec -it ksuns_mysql mysql -u ksuns_user -pksuns_password ksuns

# MySQL内でテーブル一覧を確認
SHOW TABLES;
```

## 📝 データベースの永続化

`docker-compose.yml` で `mysql_data` ボリュームを設定しているため、コンテナを削除してもデータは保持されます。

データを完全に削除する場合：

```bash
docker-compose down -v
```

## 🔄 日常的な操作

### コンテナの起動
```bash
docker-compose up -d
```

### コンテナの停止
```bash
docker-compose down
```

### コンテナの再起動
```bash
docker-compose restart mysql
```

### データベースのバックアップ
```bash
docker exec ksuns_mysql mysqldump -u ksuns_user -pksuns_password ksuns > backup.sql
```

### データベースのリストア
```bash
docker exec -i ksuns_mysql mysql -u ksuns_user -pksuns_password ksuns < backup.sql
```

## ✅ 確認チェックリスト

- [ ] Docker Desktopが起動している
- [ ] `docker-compose up -d` でコンテナが起動した
- [ ] `.env` ファイルが正しく設定されている
- [ ] `ENV=LOCAL_DEV_SKIP_AUTH` が設定されていない（またはコメントアウトされている）
- [ ] `python create_all_tables.py` が正常に完了した
- [ ] `python verify_tables_local.py` でテーブルが確認できた
- [ ] バックエンドアプリケーションが正常に起動する

## 📚 参考情報

- MySQL 8.0 ドキュメント: https://dev.mysql.com/doc/refman/8.0/en/
- Docker Compose ドキュメント: https://docs.docker.com/compose/
- SQLAlchemy ドキュメント: https://docs.sqlalchemy.org/

