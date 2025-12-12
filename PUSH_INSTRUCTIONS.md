# Git Push 手順

## 現在のブランチを確認
```bash
cd C:\ksuns_back
git branch
```

## 変更をステージング
```bash
# 修正したファイルをステージング
git add app/models/plan.py
git add app/models/simple_simulation.py

# または、すべての変更をステージング
git add .
```

## コミット
```bash
git commit -m "fix: SQLAlchemy Mapperエラーとdatetime非推奨警告を修正

- PlanningPlanモデルにsimulation_sessionsリレーションを追加
- SimpleSimulationSessionモデルのplanリレーションをplanning_planに変更
- datetime.utcnowをdatetime.now(timezone.utc)に変更"
```

## ブランチを作成してPush（推奨）
```bash
# 新しいブランチを作成
git checkout -b fix/sqlalchemy-mapper-error

# リモートにPush
git push -u origin fix/sqlalchemy-mapper-error
```

## または、mainブランチに直接Push（注意）
```bash
# mainブランチに直接Push（通常は推奨されません）
git push origin main
```

## プルリクエストの作成
1. GitHubのリポジトリページにアクセス
2. 「Compare & pull request」をクリック
3. タイトルと説明を入力（`PR_SUMMARY.md`の内容を参考に）
4. プルリクエストを作成

## コミットメッセージの例

### 短いバージョン
```
fix: SQLAlchemy Mapperエラーとdatetime非推奨警告を修正
```

### 詳細バージョン
```
fix: SQLAlchemy Mapperエラーとdatetime非推奨警告を修正

- PlanningPlanモデルにsimulation_sessionsリレーションを追加
  - SQLAlchemyのMapperエラーを修正
- SimpleSimulationSessionモデルのplanリレーションをplanning_planに変更
  - back_populatesを正しく設定
- datetime.utcnowをdatetime.now(timezone.utc)に変更
  - 非推奨警告を解消
```



