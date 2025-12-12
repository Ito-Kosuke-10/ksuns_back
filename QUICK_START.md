# テーブル作成のクイックスタート

## 🚀 最も簡単な方法（推奨）：MySQL Workbenchを使う

Azure PortalでクエリエディターやCloud Shellが見つからない場合は、**MySQL Workbench**を使うのが最も簡単で確実です。

### 手順

1. **MySQL Workbenchをインストール**（まだの場合）
   - [MySQL Workbench ダウンロード](https://dev.mysql.com/downloads/workbench/)
   - Windows版をダウンロードしてインストール

2. **Azure MySQLに接続**
   - MySQL Workbenchを起動
   - **「+」**ボタンをクリックして新しい接続を作成
   - 以下の情報を入力：
     ```
     Connection Name: Azure MySQL
     Hostname: gen10-mysql-dev-01.mysql.database.azure.com
     Username: students
     Password: （Azure Portalで確認）
     Default Schema: ksuns
     ```
   - **「Test Connection」**をクリックして接続を確認
   - **「OK」**をクリック

3. **SQLを実行**
   - 作成した接続を**ダブルクリック**して接続
   - **「File」→「Open SQL Script」**をクリック
   - **`create_tables.sql`** ファイルを選択して開く
   - **実行ボタン**（⚡アイコン、またはF5キー）をクリック

これで完了です！✅

**詳細は `SIMPLE_SQL_EXECUTION.md` を参照してください。**

---

## テーブル作成SQL（コピー用）

```sql
-- deep_dive_progress テーブル
CREATE TABLE IF NOT EXISTS deep_dive_progress (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    axis_code VARCHAR(64) NOT NULL,
    card_id VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'not_started',
    summary TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_card (user_id, card_id),
    INDEX idx_user_axis (user_id, axis_code),
    INDEX idx_card_id (card_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- deep_dive_chat_logs テーブル
CREATE TABLE IF NOT EXISTS deep_dive_chat_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    card_id VARCHAR(128) NOT NULL,
    role VARCHAR(16) NOT NULL COMMENT 'user or assistant',
    message TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_card (user_id, card_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## エラーが出た場合

### Pythonスクリプトで接続エラーが出る場合

→ **SQLファイルを直接実行**してください（上記の手順）

### その他のエラー

- `Table already exists`: テーブルは既に作成されています。問題ありません。
- `Access denied`: データベースのユーザー権限を確認してください。
- `Connection refused`: ファイアウォール設定を確認してください（Azure PortalでIPアドレスを許可）。

