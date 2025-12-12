# プルリクエスト サマリー

## 概要
SQLAlchemyのMapperエラーとdatetime非推奨警告を修正しました。

## 変更内容

### 1. `app/models/plan.py`
- **リレーション定義の追加**: `PlanningPlan`クラスに`simulation_sessions`リレーションを追加
  - SQLAlchemyのMapperエラー（`Mapper 'Mapper[SimpleSimulationSession]' has no property 'planning_plan'`）を修正
- **datetime非推奨警告の修正**: `datetime.utcnow`を`lambda: datetime.now(timezone.utc)`に変更
  - `created_at`と`updated_at`の`default`および`onupdate`を修正

### 2. `app/models/simple_simulation.py`
- **リレーション定義の修正**: `plan`リレーションを`planning_plan`に変更
  - `PlanningPlan`モデルの`simulation_sessions`リレーションと正しくペアになるように修正
  - `back_populates="simulation_sessions"`を設定

## 修正の詳細

### 問題点
1. `PlanningPlan`モデルに`simulation_sessions`リレーションが定義されていたが、`SimpleSimulationSession`モデル側に`planning_plan`リレーションが存在しなかった
2. `datetime.utcnow`が非推奨となっており、警告が発生していた

### 解決方法
1. `PlanningPlan`モデルに`simulation_sessions`リレーションを追加
2. `SimpleSimulationSession`モデルの`plan`リレーションを`planning_plan`に変更し、`back_populates`を正しく設定
3. `datetime.utcnow`を`lambda: datetime.now(timezone.utc)`に変更

## 影響範囲
- データベースモデルのリレーション定義のみ
- 既存のAPIやビジネスロジックへの影響なし

## テスト
- SQLAlchemyのMapperエラーが解消されることを確認
- datetime非推奨警告が解消されることを確認



