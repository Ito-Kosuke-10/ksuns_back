# データベース定義（スキーマ）の場所

## 概要

このプロジェクトでは、**SQLAlchemy ORM** を使用してデータベースのテーブル定義を行っています。

**マイグレーションツール（Alembic）は現在設定されていません。**

## データベース定義の場所

### 基本構造

すべてのデータベース定義は `app/models/` ディレクトリにあります。

```
C:\ksuns_back\app\models\
├── __init__.py          # すべてのモデルをエクスポート
├── base.py              # Baseクラス（すべてのモデルの基底クラス）
├── user.py              # ユーザーテーブル
├── simple_simulation.py # 簡易シミュレーション関連テーブル
├── axis.py              # レーダーチャートの軸関連テーブル
├── detail_question.py  # 詳細質問関連テーブル
├── deep_question.py    # 深掘り質問関連テーブル
├── qa.py                # なんでも質問関連テーブル
├── notes.py             # ノート・ストーリー関連テーブル
├── summaries.py         # サマリー関連テーブル
├── questions.py         # 質問マスターテーブル
├── free_question.py    # 自由質問テーブル
└── business_plan.py    # ビジネスプラン関連テーブル
```

## 各ファイルの役割

### 1. `app/models/base.py`
**すべてのモデルの基底クラス**

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

すべてのテーブル定義はこの `Base` クラスを継承します。

---

### 2. `app/models/user.py`
**ユーザーテーブル**

- **テーブル名**: `users`
- **主なカラム**:
  - `id` (BigInteger, PK)
  - `google_sub` (String(255), UNIQUE)
  - `email` (String(255), UNIQUE)
  - `display_name` (String(255))
  - `created_at`, `updated_at` (DateTime)

---

### 3. `app/models/simple_simulation.py`
**簡易シミュレーション関連テーブル**

#### `simple_simulation_sessions`
- セッション情報
- カラム: `id`, `user_id`, `guest_session_token`, `status`, `started_at`, `completed_at`

#### `simple_simulation_answers`
- 回答データ
- カラム: `id`, `session_id`, `question_code`, `answer_values` (JSON)

#### `simple_simulation_results`
- 結果データ
- カラム: `id`, `session_id`, `axis_scores` (JSON), `funds_comment_category`, `funds_comment_text`, `store_story_text`

---

### 4. `app/models/axis.py`
**レーダーチャートの軸関連テーブル**

#### `planning_axes`
- 軸のマスターデータ
- カラム: `id`, `code`, `name`, `description`, `display_order`

#### `axis_steps`
- 軸のステップ情報
- カラム: `id`, `axis_id`, `level`, `code`, `title`, `description`, `display_order`

#### `axis_answers`
- 軸の回答データ
- カラム: `id`, `user_id`, `axis_id`, `level`, `answers_json` (JSON)

#### `axis_scores`
- 軸のスコア
- カラム: `id`, `user_id`, `axis_id`, `score`, `level1_completion_ratio`, `level2_completion_ratio`, `calculated_at`

---

### 5. `app/models/detail_question.py`
**詳細質問関連テーブル**

#### `detail_question_answers`
- 詳細質問の回答
- カラム: `id`, `user_id`, `question_code`, `answer` (Boolean)

---

### 6. `app/models/deep_question.py`
**深掘り質問関連テーブル**

#### `deep_questions`
- 深掘り質問の履歴
- カラム: `id`, `user_id`, `axis_code`, `question_text`, `answer_text`, `created_at`

#### `deep_answers`
- 深掘り質問の回答（別テーブルとして定義されている可能性）

---

### 7. `app/models/qa.py`
**なんでも質問関連テーブル**

#### `qa_conversations`
- 質問会話のセッション
- カラム: `id`, `user_id`, `context_type`, `axis_code`, `created_at`

#### `qa_messages`
- 質問メッセージ
- カラム: `id`, `conversation_id`, `role`, `text`, `created_at`

---

### 8. `app/models/notes.py`
**ノート・ストーリー関連テーブル**

#### `owner_notes`
- オーナーノート
- カラム: `id`, `user_id`, `content`, `updated_at`

#### `store_stories`
- 店のストーリー
- カラム: `id`, `user_id`, `source`, `content`, `created_at`

---

### 9. `app/models/summaries.py`
**サマリー関連テーブル**

#### `summaries`
- サマリー
- カラム: `id`, `user_id`, `summary_type`, `content`, `created_at`

---

### 10. `app/models/questions.py`
**質問マスターテーブル**

#### `questions`
- 質問のマスターデータ
- カラム: `id`, `axis_id`, `code`, `text`, `display_order`

---

### 11. `app/models/free_question.py`
**自由質問テーブル**

#### `free_questions`
- 自由質問
- カラム: 詳細はファイルを確認

---

### 12. `app/models/business_plan.py`
**ビジネスプラン関連テーブル**

#### `business_plan_drafts`
- ビジネスプランのドラフト
- カラム: 詳細はファイルを確認

---

## テーブル定義の確認方法

### 方法1: モデルファイルを直接確認

各モデルファイルを開いて、`__tablename__` と `mapped_column` を確認：

```python
class User(Base):
    __tablename__ = "users"  # ← テーブル名
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # ← カラム定義
    email: Mapped[str] = mapped_column(String(255), nullable=False)
```

### 方法2: すべてのモデルを一覧表示

`app/models/__init__.py` を確認すると、すべてのモデルクラスがエクスポートされています。

### 方法3: データベースから直接確認

```sql
-- MySQLに接続して実行
USE ksuns_db;
SHOW TABLES;

-- 特定のテーブルの構造を確認
DESCRIBE users;
DESCRIBE simple_simulation_sessions;
```

### 方法4: SQLAlchemyのメタデータから確認

```python
from app.models.base import Base
from app.models import *  # すべてのモデルをインポート

# すべてのテーブル定義を表示
for table_name, table in Base.metadata.tables.items():
    print(f"Table: {table_name}")
    for column in table.columns:
        print(f"  - {column.name}: {column.type}")
```

## テーブル作成方法

現在、マイグレーションツールが設定されていないため、以下の方法でテーブルを作成できます：

### 方法1: SQLAlchemyで自動生成（開発環境のみ）

```python
# create_tables.py を作成
import asyncio
from app.core.db import engine
from app.models.base import Base
from app.models import *  # すべてのモデルをインポート

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables())
```

実行：
```bash
python create_tables.py
```

### 方法2: SQLファイルから手動実行

モデル定義を元にSQLファイルを作成して、MySQLで実行

### 方法3: Alembicを導入（推奨）

マイグレーションツールを導入して、テーブル作成とスキーマ変更を管理

## リレーションシップ（関連）の確認

各モデルファイルで `relationship()` を使用して、テーブル間の関連を定義しています。

例：
```python
# user.py
simulation_sessions = relationship(
    "SimpleSimulationSession",
    back_populates="user",
    cascade="all, delete-orphan",
)
```

## まとめ

- **データベース定義の場所**: `app/models/` ディレクトリ
- **定義方法**: SQLAlchemy ORM（Pythonクラスとして定義）
- **マイグレーションツール**: 現在未設定（Alembicの導入を推奨）
- **テーブル作成**: 手動でスクリプトを実行するか、SQLファイルから実行

新しいテーブルを追加する場合は、`app/models/` に新しいファイルを作成し、`Base` を継承したクラスを定義してください。




