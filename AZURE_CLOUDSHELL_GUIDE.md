# Azure Cloud ShellでSQLを実行する方法

Azure Portalの「データベース」セクションにはクエリエディターが直接提供されていないため、**Azure Cloud Shell**を使います。

## 🚀 手順

### 1. Azure Cloud Shellを開く

1. Azure Portalの**右上**にある**Cloud Shellアイコン**（`>_` のようなアイコン）をクリック
2. 初回の場合は、**Bash**または**PowerShell**を選択（どちらでもOK）
3. Cloud Shellが開くまで待つ（数秒かかります）

### 2. MySQLクライアントをインストール（必要な場合）

Cloud Shellで以下のコマンドを実行：

```bash
# MySQLクライアントをインストール
sudo apt-get update
sudo apt-get install -y mysql-client
```

### 3. データベースに接続

```bash
# 接続コマンド（パスワードを聞かれます）
mysql -h gen10-mysql-dev-01.mysql.database.azure.com \
      -u students \
      -p \
      ksuns
```

パスワードを入力します（画面には表示されませんが、入力はされています）。

### 4. SQLファイルを実行

接続後、以下のコマンドでSQLファイルを実行：

```bash
# Cloud Shellでファイルをアップロードする方法
# 1. Cloud Shellの「ファイルのアップロード」アイコンをクリック
# 2. create_tables.sql を選択
# 3. アップロード後、以下のコマンドで実行

mysql -h gen10-mysql-dev-01.mysql.database.azure.com \
      -u students \
      -p \
      ksuns < create_tables.sql
```

**または、直接SQLを貼り付ける方法：**

1. MySQLに接続（上記の手順3）
2. `create_tables.sql` の内容をコピー
3. Cloud Shellに貼り付け（Ctrl+V）
4. Enterキーを押して実行

---

## 📋 直接SQLを貼り付ける方法（最も簡単）

1. **Azure Cloud Shellを開く**（右上の `>_` アイコン）
2. 以下のコマンドでMySQLに接続：
   ```bash
   mysql -h gen10-mysql-dev-01.mysql.database.azure.com -u students -p ksuns
   ```
3. パスワードを入力
4. **`create_tables.sql`** の内容をコピー＆ペースト
5. Enterキーを押す
6. `exit;` と入力して接続を終了

---

## 🔧 別の方法：MySQL Workbenchを使う

Azure Cloud Shellが使えない場合は、**MySQL Workbench**を使います。

### インストール

1. [MySQL Workbench](https://dev.mysql.com/downloads/workbench/)をダウンロード
2. インストール

### 接続設定

1. MySQL Workbenchを開く
2. **「+」**ボタンをクリックして新しい接続を作成
3. 以下の情報を入力：
   - **Connection Name**: `Azure MySQL`
   - **Hostname**: `gen10-mysql-dev-01.mysql.database.azure.com`
   - **Username**: `students`
   - **Password**: （Azure Portalで確認）
   - **Default Schema**: `ksuns`
4. **「Test Connection」**をクリックして接続をテスト
5. **「OK」**をクリック

### SQLを実行

1. 接続をダブルクリックして接続
2. **「File」→「Open SQL Script」**で`create_tables.sql`を開く
3. **実行ボタン**（⚡アイコン）をクリック

---

## 💡 最も簡単な方法（推奨）

**Azure Cloud Shellで直接SQLを貼り付ける方法**が最も簡単です：

1. Azure Portal右上の**Cloud Shellアイコン**（`>_`）をクリック
2. 以下のコマンドを実行：
   ```bash
   mysql -h gen10-mysql-dev-01.mysql.database.azure.com -u students -p ksuns
   ```
3. パスワードを入力
4. `create_tables.sql`の内容をコピー＆ペースト
5. Enterキーを押す

これで完了です！✅



