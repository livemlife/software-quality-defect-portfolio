# データ辞書

粒度：1行1検出欠陥。別表は1行1か月。

- `defect_id`: 欠陥の一意ID
- `date`: 検出日
- `closed_date`: クローズ日 NULLは2025-12-31時点未解決
- `module`: 架空機能領域
- `severity`: High/Medium/Low
- `stage`: Test/Production 検出段階
- `root_cause`: 仮の原因分類
- `reopened`: 再オープン履歴あり1 なし0
- `month`: 検出月
- `resolution_days`: クローズ日−検出日 暦日。未解決NULL
- `open_at_cutoff`: 2025-12-31時点未解決1
- `age_days_at_cutoff`: 未解決のみ 基準日−検出日
- `executed_tests`: 別表test_exposure.csvの月次実行テスト数

小数の率は0–1。欠損はCSVの空欄。UTF-8 BOM付き。