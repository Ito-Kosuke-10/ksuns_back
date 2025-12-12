# データベース接続先の確認方法

## 重要なポイント

**はい、ローカルで動かしているアプリでも、リモートのAzure Database for MySQLに接続することは可能です！**

接続先は `.env` ファイルの設定で決まります。

## 確認方法

### 1. `.env` ファイルを確認

`C:\ksuns_back\.env` ファイルを開いて、以下の設定を確認してください：

```env
DB_HOST=localhost          # ← これが接続先
DB_PORT=3306
DB_NAME=ksuns_db
DB_USER=your_user
DB_PASSWORD=your_password
```

### 2. `DB_HOST` の値で判断

#### ローカルのMySQLの場合
```env
DB_HOST=localhost
# または
DB_HOST=127.0.0.1
```
→ **ローカルのMySQLサーバー**に接続しています

#### リモートのAzure Database for MySQLの場合
```env
DB_HOST=your-server.mysql.database.azure.com
# または
DB_HOST=xxx.xxx.xxx.xxx  # IPアドレスの場合
```
→ **Azure Database for MySQL**に接続しています

### 3. 実際の接続を確認する方法

#### 方法1: バックエンドアプリのログを確認

バックエンドアプリを起動したときのログを確認：

```bash
cd C:\ksuns_back
python -m uvicorn app.main:app --reload
```

エラーメッセージや接続情報が表示される場合があります。

#### 方法2: データベースに直接接続してみる

```bash
# ローカルの場合
mysql -u your_user -p -h localhost ksuns_db

# リモート（Azure）の場合
mysql -u your_user -p -h your-server.mysql.database.azure.com ksuns_db
```

接続できれば、そのデータベースが使用されています。

#### 方法3: コードで確認

一時的に以下のコードを実行して、接続URLを表示：

```python
from app.core.config import get_settings

settings = get_settings()
print(f"Database URL: {settings.database_url}")
# 出力例:
# mysql+asyncmy://user:pass@localhost:3306/ksuns_db  ← ローカル
# mysql+asyncmy://user:pass@xxx.mysql.database.azure.com:3306/ksuns_db  ← Azure
```

## よくあるシナリオ

### シナリオ1: ローカルのMySQLを使用

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=ksuns_db
DB_USER=root
DB_PASSWORD=local_password
```

- データは **ローカルのMySQLサーバー** に保存されます
- ローカルにMySQLがインストールされている必要があります
- データは自分のPC内に保存されます

### シナリオ2: Azure Database for MySQLを使用（ローカル開発）

```env
DB_HOST=your-app.mysql.database.azure.com
DB_PORT=3306
DB_NAME=ksuns_db
DB_USER=admin_user@your-app
DB_PASSWORD=azure_password
SSL_CA_PATH=/path/to/ca-cert.pem  # Azureの場合、SSL証明書が必要な場合あり
```

- データは **Azure Database for MySQL** に保存されます
- ローカルで動かしていても、データはクラウドに保存されます
- インターネット接続が必要です
- 本番環境と同じデータベースを使うことができます

### シナリオ3: DockerコンテナのMySQLを使用

```env
DB_HOST=localhost  # または 127.0.0.1
DB_PORT=3306
DB_NAME=ksuns_db
DB_USER=docker_user
DB_PASSWORD=docker_password
```

- データは **Dockerコンテナ内のMySQL** に保存されます
- コンテナを削除するとデータも消えます
- データの永続化にはボリュームマウントが必要です

## どちらを使うべきか？

### ローカルのMySQLを使う場合
- ✅ 開発中はローカルで完結したい
- ✅ インターネット接続が不安定
- ✅ データをローカルに保持したい
- ✅ 開発用のテストデータを使いたい

### Azure Database for MySQLを使う場合
- ✅ 本番環境と同じデータベースでテストしたい
- ✅ チームで同じデータベースを共有したい
- ✅ ローカルにMySQLをインストールしたくない
- ✅ データのバックアップが自動で取られる

## 現在の設定を確認する手順

1. **`.env` ファイルを開く**
   ```
   C:\ksuns_back\.env
   ```

2. **`DB_HOST` の値を確認**
   - `localhost` または `127.0.0.1` → ローカル
   - `xxx.mysql.database.azure.com` → Azure

3. **実際に接続してみる**
   ```bash
   mysql -u {DB_USER} -p -h {DB_HOST} {DB_NAME}
   ```

## トラブルシューティング

### ローカルのMySQLに接続できない場合

1. MySQLサーバーが起動しているか確認
   ```bash
   # Windowsの場合
   net start MySQL
   ```

2. ユーザー名・パスワードが正しいか確認

3. データベースが作成されているか確認
   ```sql
   SHOW DATABASES;
   ```

### Azure Database for MySQLに接続できない場合

1. ファイアウォール設定を確認
   - Azure Portalで、自分のIPアドレスが許可されているか確認

2. SSL証明書が必要な場合
   - `SSL_CA_PATH` を設定する必要がある場合があります

3. 接続文字列が正しいか確認
   - Azure Portalの「接続文字列」を確認

## まとめ

- **ローカルで動かしていても、リモートのAzure Database for MySQLに接続することは可能です**
- 接続先は `.env` ファイルの `DB_HOST` で決まります
- `localhost` ならローカル、`xxx.mysql.database.azure.com` ならAzureです




