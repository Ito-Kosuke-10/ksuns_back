# 深掘り機能（Deep Dive）のテーブル作成方法

## ⚠️ 重要: 仮想環境のアクティベーション

スクリプトを実行する前に、**仮想環境をアクティブにする必要があります**。

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1

# または
venv\Scripts\activate
```

仮想環境がない場合は、まず作成してください：
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 方法1: Pythonスクリプトで作成（推奨）

```powershell
cd C:\ksuns_back
# 仮想環境をアクティブにする
.venv\Scripts\Activate.ps1
# スクリプトを実行
python create_deep_dive_tables.py
```

## 方法2: 直接SQLで作成（最も簡単・確実）⭐ 推奨

**この方法が最も確実です！** 接続エラーや仮想環境の問題を回避できます。

### オプションA: Azure Portalから実行（最も簡単）

1. **Azure Portal**にログイン
2. **Azure Database for MySQL**のリソースを開く
3. **クエリエディター**（または**ワークベンチ**）を開く
4. `create_tables.sql` ファイルを開く
5. SQLの内容をコピー＆ペースト
6. **実行**ボタンをクリック

### オプションB: MySQL Workbenchで実行

1. **MySQL Workbench**を開く
2. Azure MySQLに接続
3. `create_tables.sql` ファイルを開く（File → Open SQL Script）
4. **実行**ボタンをクリック（⚡アイコン）

### オプションC: コマンドラインから実行

```powershell
# MySQLクライアントがインストールされている場合
mysql -h gen10-mysql-dev-01.mysql.database.azure.com -u [ユーザー名] -p [データベース名] < create_tables.sql
```

### オプションD: 手動でコピー＆ペースト

1. `create_tables.sql` ファイルを開く
2. 内容をすべてコピー
3. 任意のMySQLクライアント（Azure Portal、Workbench、phpMyAdminなど）に接続
4. SQLをペーストして実行

## 方法3: SQLAlchemyで作成

Pythonインタラクティブシェルで実行：

```python
import asyncio
from app.core.db import engine
from app.models.deep_dive import DeepDiveProgress, DeepDiveChatLog

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(DeepDiveProgress.__table__.create)
        await conn.run_sync(DeepDiveChatLog.__table__.create)
    print("テーブル作成完了")

asyncio.run(create())
```

