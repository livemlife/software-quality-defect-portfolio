# Power BI Desktop 搭建と検証手順

状態：CSV、DAX、レイアウト仕様を提供。Desktopでの実装・動作検証は未実施。PBIXは同梱しない。

1. 「データを取得 → テキスト/CSV」で data/fact.csv を読み込み、テーブル名を fact にする。UTF-8、カンマ区切り。
2. date は日付、IDと分類と month はテキスト、率と時間は小数、フラグと件数は整数に設定。空欄はnullを保つ。
3. measures.dax の定義を一つずつ新規メジャーとして追加。率はパーセント表示。日付の自動階層ではなく date/month を軸に使う。
4. 16:9ページ。上部にタイトルとデータ種別、期間。次に4枚のKPIカード。中央に推移折れ線、下部に分類別テーブルを置く。HTMLレポートを配置見本とする。
5. 期間・分類スライサーを追加し、全選択時に results/metrics.json と照合する。単一分類、空の期間、複数月の選択で表示を点検する。0除算はBLANKを許容する。
6. 保存後に更新し、PBIXを開き直してCSVの参照先と指標値を検証する。GitHub掲載前に絶対パスを確認する。

Python・SQLの集計は実行済み。DAXの値はDesktopで別途照合が必要。

品質：data/test_exposure.csvもtest_exposure名で読み込む。DimMonth = DISTINCT(test_exposure[month]) を計算テーブルとして作り、DimMonth[month]からfact[month]、test_exposure[month]へ各1対多・単方向のリレーションを作る。月スライサーと軸はDimMonth[month]。テスト密度は全モジュールで表示し、module/severity/stageフィルターからの相互作用を無効にする（テスト数に分類別内訳がないため）。品質カードは件数、本番検出比率、解決中央値、未解決件数。NULL解決日数は中央値から除外。
