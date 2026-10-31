from pathlib import Path
import pandas as pd
import numpy as np
import sqlite3, json, hashlib, html

P=Path(__file__).resolve().parent
K='03_software_quality'
for folder in ['data','results','charts','powerbi']:(P/folder).mkdir(exist_ok=True)
rng=np.random.default_rng(20261030)

def save(df,name):
    df.to_csv(P/name,index=False,encoding='utf-8-sig',float_format='%.10g')

def chart(name,title,series,percent=False):
    # Portable, dependency-free SVG. All chart series share the same y scale.
    colors=['#2563eb','#f97316','#059669','#9f5de2']
    vals=[float(v) for _,ys in series.values() for v in ys if pd.notna(v)]
    lo=min(vals+[0]);hi=max(vals+[0]);hi=hi if hi>lo else lo+1
    def sy(v):return 310-(float(v)-lo)/(hi-lo)*235
    s=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 400" role="img">',f'<title>{html.escape(title)}</title>','<rect width="900" height="400" fill="white"/>',f'<text x="30" y="32" font-family="sans-serif" font-size="20" fill="#0f172a">{html.escape(title)}</text>']
    for v in np.linspace(lo,hi,5):
        y=sy(v);label=f'{v:.1%}' if percent else f'{v:,.1f}'
        s+=[f'<path d="M85 {y}H860" stroke="#e2e8f0"/>',f'<text x="78" y="{y+4}" text-anchor="end" font-family="sans-serif" font-size="12">{label}</text>']
    for j,(label,(xs,ys)) in enumerate(series.items()):
        pts=' '.join(f'{85+i*775/max(len(xs)-1,1):.1f},{sy(y):.1f}' for i,y in enumerate(ys) if pd.notna(y))
        s+=[f'<polyline fill="none" stroke="{colors[j%4]}" stroke-width="2.5" points="{pts}"/>',f'<text x="{90+j*215}" y="380" fill="{colors[j%4]}" font-family="sans-serif" font-size="13">{html.escape(label)}</text>']
        if j==0:
            for i in sorted(set(np.linspace(0,len(xs)-1,min(6,len(xs))).astype(int))):
                s.append(f'<text x="{85+i*775/max(len(xs)-1,1)}" y="337" text-anchor="middle" font-size="11" font-family="sans-serif">{html.escape(str(xs[i])[:10])}</text>')
    s.append('</svg>');(P/'charts'/name).write_text(''.join(s),encoding='utf-8')

checks=[]
detail=''
def check(name,ok):
    checks.append({'check':name,'passed':bool(ok)})
    if not ok:raise AssertionError(name)

if K.startswith('01'):
    raw=pd.read_csv(P/'data/source_snapshot.csv')
    raw['Date']=pd.to_datetime(raw['Date'],errors='coerce')
    df=raw.loc[raw.Date.between('2000-01-01','2023-06-01'),['Date','SP500']].copy().sort_values('Date')
    check('unique month',not df.Date.duplicated().any())
    check('no missing price',df.SP500.notna().all() and (df.SP500>0).all())
    check('continuous 282 monthly observations',len(df)==282 and len(pd.period_range(df.Date.min(),df.Date.max(),freq='M'))==len(df))
    df.columns=['date','price'];df['month']=df.date.dt.strftime('%Y-%m');df['date']=df.date.dt.strftime('%Y-%m-%d')
    df['monthly_return']=df.price.pct_change(fill_method=None)
    df['index_100']=100*df.price/df.price.iloc[0]
    df['rolling_vol_12m']=df.monthly_return.rolling(12,min_periods=12).std(ddof=1)*np.sqrt(12)
    df['drawdown']=df.price/df.price.cummax()-1
    df['ma_12m']=df.price.rolling(12,min_periods=12).mean()
    n=len(df)-1
    metrics={'observations':len(df),'cumulative_price_return':df.price.iloc[-1]/df.price.iloc[0]-1,'annualized_price_growth':(df.price.iloc[-1]/df.price.iloc[0])**(12/n)-1,'annualized_volatility':df.monthly_return.std(ddof=1)*np.sqrt(12),'max_monthly_drawdown':df.drawdown.min()}
    sql='''-- SQLite 3.25+; returns are ratios, not percentage points.
WITH r AS (SELECT date,price,price/LAG(price) OVER(ORDER BY date)-1 AS monthly_return FROM fact)
SELECT substr(date,1,4) AS year,COUNT(monthly_return) AS return_observations,
AVG(monthly_return) AS mean_monthly_return,MIN(monthly_return) AS worst_month FROM r GROUP BY 1 ORDER BY 1;'''
    chart('market.svg','S&P 500 monthly average price | Jan 2000 = 100',{'Price index':(df.month.tolist(),df.index_100.tolist())})
    chart('risk.svg','Monthly drawdown and trailing annualized volatility',{'Drawdown':(df.month.tolist(),df.drawdown.tolist()),'12m volatility':(df.month.tolist(),df.rolling_vol_12m.tolist())},True)
    findings=f"累積価格リターンは{metrics['cumulative_price_return']:.1%}、年率換算成長率は{metrics['annualized_price_growth']:.1%}。一方、月次観測の最大ドローダウンは{metrics['max_monthly_drawdown']:.1%}であり、成長率だけではリスクを説明できない。"
    limits='2000年1月から2023年6月までの公開月次データ。月平均価格の比較であり、月末終値・日次リスク・配当込み収益ではない。手数料、税、為替を含まない。投資戦略のバックテストや将来予測は実施していない。2023年7月以降はソースの構成が変わるため分析対象外。'
    rec='収益率とドローダウンを同じ画面で確認する。次の検証では配当込み指数と円換算系列を追加し、比較期間を統一する。売買判断の推奨は行わない。'
    dictionary={'date':'月の識別日 YYYY-MM-01。取引日ではない','price':'SP500 月平均価格 指数ポイント','month':'月 YYYY-MM','monthly_return':'当月価格/前月価格−1。初月はNULL','index_100':'初月を100とした価格指数','rolling_vol_12m':'直近12個の月次リターンの標本標準偏差×√12。初期12行NULL','drawdown':'当月価格/対象期間内の過去最高価格−1','ma_12m':'当月を含む12か月平均価格。初期11行NULL'}
    dax='''Cumulative Price Return =
VAR FirstDate = MIN(fact[date])
VAR LastDate = MAX(fact[date])
VAR FirstPrice = CALCULATE(MAX(fact[price]), fact[date] = FirstDate)
VAR LastPrice = CALCULATE(MAX(fact[price]), fact[date] = LastDate)
RETURN IF(ISBLANK(FirstPrice) || ISBLANK(LastPrice), BLANK(), DIVIDE(LastPrice, FirstPrice) - 1)

Annualized Volatility = IF(COUNT(fact[monthly_return]) >= 2, STDEV.S(fact[monthly_return]) * SQRT(12), BLANK())

Max Drawdown Full Baseline = MIN(fact[drawdown])
'''
    worst=df.loc[df.drawdown.idxmin()]
    peak=df.loc[:df.drawdown.idxmin()].sort_values('price').iloc[-1]
    recovery=df.loc[(df.date>worst.date)&(df.price>=peak.price)]
    detail=f'最大下落のピーク月は{peak.month}、ボトム月は{worst.month}。同じ月平均価格を上回る回復月は'+(str(recovery.iloc[0].month) if len(recovery) else '対象期間内になし')+'。開始月より前の最高値は含まないため、期間に依存する。'
    save(df[['date','price','monthly_return','rolling_vol_12m','drawdown']].sort_values('monthly_return').head(10),'results/worst_months.csv')
    title='金融市場の収益とリスク分析'
    hypothesis='長期の価格成長と、保有期間中の下落リスクを分けて可視化できるか。'
elif K.startswith('02'):
    rows=[]
    for m in range(1,13):
        for i in range(240):
            kind=rng.choice(['Standard','Complex'],p=[.72,.28]);team=rng.choice(['A','B','C'])
            post=m>=7;work=float(rng.lognormal(np.log(22 if kind=='Standard' else 52),.32))
            work*=.81 if post else 1
            wait=float(rng.gamma(2,35 if kind=='Complex' else 14))*(.7 if post else 1)
            error=int(rng.random() < ((.13 if kind=='Complex' else .065)*(.65 if post else 1)))
            rows.append([f'T{m:02}{i:04}',f'2025-{m:02}-{int(rng.integers(1,29)):02}',team,kind,'After' if post else 'Before',round(work,2),round(wait,2),error])
    df=pd.DataFrame(rows,columns=['task_id','date','team','complexity','phase','work_minutes','wait_minutes','error'])
    save(df,'data/raw.csv')
    df['month']=df.date.str[:7];df['lead_minutes']=df.work_minutes+df.wait_minutes;df['within_sla']=(df.lead_minutes<=120).astype(int)
    summary=df.groupby('phase').agg(tasks=('task_id','size'),avg_work=('work_minutes','mean'),avg_wait=('wait_minutes','mean'),error_rate=('error','mean'),sla_rate=('within_sla','mean')).reset_index()
    save(summary,'results/phase_summary.csv')
    a=summary.set_index('phase');reduction=1-a.loc['After','avg_work']/a.loc['Before','avg_work']
    metrics={'tasks':len(df),'work_minutes_reduction_ratio':reduction,'before_error_rate':a.loc['Before','error_rate'],'after_error_rate':a.loc['After','error_rate'],'after_sla_rate':a.loc['After','sla_rate']}
    sql='''SELECT phase,complexity,COUNT(*) AS tasks,AVG(work_minutes) AS avg_work_minutes,
AVG(wait_minutes) AS avg_wait_minutes,AVG(error*1.0) AS error_rate,
AVG(CASE WHEN work_minutes+wait_minutes<=120 THEN 1.0 ELSE 0 END) AS sla_rate
FROM fact GROUP BY phase,complexity ORDER BY phase,complexity;'''
    mon=df.groupby('month').agg(work=('work_minutes','mean'),wait=('wait_minutes','mean'),error=('error','mean'),sla=('within_sla','mean'))
    chart('process.svg','Average process time | simulated case',{'Work minutes':(mon.index.tolist(),mon.work.tolist()),'Wait minutes':(mon.index.tolist(),mon.wait.tolist())})
    chart('quality.svg','Error rate and SLA attainment | simulated case',{'Error rate':(mon.index.tolist(),mon.error.tolist()),'SLA attainment':(mon.index.tolist(),mon.sla.tolist())},True)
    findings=f"模擬データ{len(df):,}件で、後半期の平均作業時間は前半期比{reduction:.1%}低い。エラー率は{metrics['before_error_rate']:.1%}から{metrics['after_error_rate']:.1%}。改善を仮定した生成条件が結果に含まれるため、実証された業務効果ではない。"
    limits='完全な模擬ケース。2025年の各月240件の完了タスクのみ。待ち時間は暦上の経過分。未完了案件や稼働人数がないため、バックログや一人当たり生産性は算出しない。Before/Afterは季節・担当者差の影響を排除できず、因果効果とみなせない。'
    rec='Complex案件を優先して受付チェックリストと承認ルールを試行する。実務では件数、複雑度、担当者、流入時刻を記録し、比較対象を置いた小規模パイロットで品質と時間の両面を確認する。'
    dictionary={'task_id':'完了タスクの一意ID','date':'完了日 YYYY-MM-DD','team':'架空チーム A/B/C','complexity':'Standard/Complex 生成時の難易度','phase':'Before 1–6月 / After 7–12月','work_minutes':'作業時間 分 正値','wait_minutes':'待ち時間 分 非負','error':'手戻りあり1 なし0','month':'完了月','lead_minutes':'work_minutes+wait_minutes','within_sla':'lead_minutes<=120なら1'}
    dax='''Tasks = COUNTROWS(fact)
Average Work Minutes = AVERAGE(fact[work_minutes])
Average Wait Minutes = AVERAGE(fact[wait_minutes])
Error Rate = DIVIDE(SUM(fact[error]), [Tasks])
SLA Rate = DIVIDE(SUM(fact[within_sla]), [Tasks])
Work Reduction =
VAR BeforeValue = CALCULATE([Average Work Minutes], REMOVEFILTERS(fact[phase]), fact[phase] = "Before")
VAR AfterValue = CALCULATE([Average Work Minutes], REMOVEFILTERS(fact[phase]), fact[phase] = "After")
RETURN IF(ISBLANK(BeforeValue) || ISBLANK(AfterValue) || BeforeValue = 0, BLANK(), 1 - DIVIDE(AfterValue, BeforeValue))
'''
    strata=df.groupby(['phase','complexity']).agg(tasks=('task_id','size'),avg_work=('work_minutes','mean'),avg_wait=('wait_minutes','mean'),error_rate=('error','mean')).reset_index()
    save(strata,'results/complexity_summary.csv')
    weights=df.loc[df.phase=='Before'].complexity.value_counts(normalize=True)
    standardized={phase:sum(weights[k]*df.loc[(df.phase==phase)&(df.complexity==k),'work_minutes'].mean() for k in weights.index) for phase in ['Before','After']}
    standardized_reduction=1-standardized['After']/standardized['Before']
    boot_rng=np.random.default_rng(314159);draws=[]
    samples={(phase,k):df.loc[(df.phase==phase)&(df.complexity==k),'work_minutes'].to_numpy() for phase in ['Before','After'] for k in weights.index}
    for _ in range(1000):
        means={phase:sum(weights[k]*boot_rng.choice(samples[phase,k],size=len(samples[phase,k]),replace=True).mean() for k in weights.index) for phase in ['Before','After']}
        draws.append(1-means['After']/means['Before'])
    low,high=np.quantile(draws,[.025,.975])
    save(pd.DataFrame([{'standardized_work_reduction':standardized_reduction,'bootstrap_95_low':low,'bootstrap_95_high':high,'bootstrap_draws':1000}]),'results/standardized_comparison.csv')
    detail=f'前半期の難易度構成を固定した平均作業時間の減少率は{standardized_reduction:.1%}。難易度・期内の行を独立に再抽出する1000回のブートストラップ区間は{low:.1%}–{high:.1%}。固定した構成比と独立行という仮定に条件づけた区間であり、日次相関や交絡は評価していない。模擬生成の効果を現実の因果効果へ一般化できない。'
    title='業務KPIと処理プロセスの改善分析'
    hypothesis='作業時間と待ち時間を分解し、難易度別に時間と品質の変化を確認できるか。'
else:
    rows=[];exposure=[]
    for m in range(1,13):
        tests=int(rng.integers(900,1300));exposure.append([f'2025-{m:02}',tests])
        for i in range(int(rng.poisson(80 if m<=6 else 55))):
            module=rng.choice(['Payment','Account','Search'],p=[.48,.30,.22]);severity=rng.choice(['High','Medium','Low'],p=[.22,.48,.30])
            stage=rng.choice(['Test','Production'],p=[.86,.14] if m<=6 else [.93,.07])
            opened=pd.Timestamp(2025,m,int(rng.integers(1,29)))
            days=int(rng.integers(1,35));closed=opened+pd.Timedelta(days=days)
            if rng.random()<.09 or closed>pd.Timestamp('2025-12-31'):closed=pd.NaT
            cause=rng.choice(['Requirement','Implementation','Environment'],p=[.5,.35,.15])
            rows.append([f'D{m:02}{i:04}',opened.strftime('%Y-%m-%d'),None if pd.isna(closed) else closed.strftime('%Y-%m-%d'),module,severity,stage,cause,int(rng.random()<.12)])
    df=pd.DataFrame(rows,columns=['defect_id','date','closed_date','module','severity','stage','root_cause','reopened'])
    save(df,'data/raw.csv');exp=pd.DataFrame(exposure,columns=['month','executed_tests']);save(exp,'data/test_exposure.csv')
    df['month']=df.date.str[:7];df['resolution_days']=(pd.to_datetime(df.closed_date)-pd.to_datetime(df.date)).dt.days
    df['open_at_cutoff']=df.closed_date.isna().astype(int)
    df['age_days_at_cutoff']=np.where(df.closed_date.isna(),(pd.Timestamp('2025-12-31')-pd.to_datetime(df.date)).dt.days,np.nan)
    mon=df.groupby('month').agg(defects=('defect_id','size'),production=('stage',lambda s:(s=='Production').sum()),median_resolution_days=('resolution_days','median')).reset_index().merge(exp,on='month',validate='one_to_one')
    mon['test_defects_per_100_tests']=(mon.defects-mon.production)/mon.executed_tests*100
    save(mon,'results/monthly_quality.csv')
    causes=df.groupby('root_cause').size().sort_values(ascending=False).rename('defects').reset_index();save(causes,'results/root_cause.csv')
    metrics={'defects':len(df),'production_detection_share':float((df.stage=='Production').mean()),'median_closed_resolution_days':float(df.resolution_days.median()),'open_at_cutoff':int(df.open_at_cutoff.sum()),'reopened_share':float(df.reopened.mean())}
    sql='''SELECT module,COUNT(*) AS defects,
AVG(CASE WHEN stage='Production' THEN 1.0 ELSE 0 END) AS production_detection_share,
AVG(julianday(closed_date)-julianday(date)) AS mean_closed_resolution_days,
SUM(CASE WHEN closed_date IS NULL THEN 1 ELSE 0 END) AS open_at_cutoff
FROM fact GROUP BY module ORDER BY defects DESC;'''
    chart('defects.svg','Monthly defect detections | simulated case',{'All detections':(mon.month.tolist(),mon.defects.tolist()),'Production detections':(mon.month.tolist(),mon.production.tolist())})
    chart('exposure.svg','Test detections per 100 executed tests | simulated case',{'Test detection density':(mon.month.tolist(),mon.test_defects_per_100_tests.tolist())})
    findings=f"模擬欠陥{len(df):,}件の本番検出比率は{metrics['production_detection_share']:.1%}、クローズ済み解決日数の中央値は{metrics['median_closed_resolution_days']:.0f}日。最多の記録原因は{causes.iloc[0].root_cause}（{int(causes.iloc[0].defects)}件）。件数だけでなくテスト実行数との比率を併記した。"
    limits='完全な模擬ケースであり、勤務先の記録ではない。本番検出比率の分母は全検出欠陥で、未知の欠陥を含む真の流出率ではない。テスト密度はテスト検出件数/実行テスト数であり製品の真の欠陥密度ではない。クローズ済み期間は未解決案件の打ち切りバイアスを含む。原因は仮の分類ラベルであり、因果関係の証明ではない。'
    rec='要件レビューとPayment領域の回帰テストを優先する仮説を置く。未解決の高重要度案件を年齢別に点検し、テスト範囲・変更規模・リリース別の情報を追加して検証する。'
    dictionary={'defect_id':'欠陥の一意ID','date':'検出日','closed_date':'クローズ日 NULLは2025-12-31時点未解決','module':'架空機能領域','severity':'High/Medium/Low','stage':'Test/Production 検出段階','root_cause':'仮の原因分類','reopened':'再オープン履歴あり1 なし0','month':'検出月','resolution_days':'クローズ日−検出日 暦日。未解決NULL','open_at_cutoff':'2025-12-31時点未解決1','age_days_at_cutoff':'未解決のみ 基準日−検出日','executed_tests':'別表test_exposure.csvの月次実行テスト数'}
    dax='''Defects = COUNTROWS(fact)
Production Share = DIVIDE(CALCULATE([Defects], KEEPFILTERS(fact[stage] = "Production")), [Defects])
Median Closed Resolution Days = MEDIAN(fact[resolution_days])
Open At Cutoff = SUM(fact[open_at_cutoff])
Reopened Share = DIVIDE(SUM(fact[reopened]), [Defects])
Test Detections per 100 Tests =
DIVIDE(CALCULATE([Defects], fact[stage] = "Test"), SUM(test_exposure[executed_tests])) * 100
'''
    backlog=df.loc[df.open_at_cutoff==1].groupby('severity').agg(open_count=('defect_id','size'),median_age_days=('age_days_at_cutoff','median'),max_age_days=('age_days_at_cutoff','max')).reset_index()
    save(backlog,'results/backlog_by_severity.csv')
    phases=mon.assign(phase=np.where(mon.month<='2025-06','Before','After')).groupby('phase')[['defects','production','executed_tests']].sum()
    phases['test_detections_per_100_tests']=(phases.defects-phases.production)/phases.executed_tests*100
    save(phases.reset_index(),'results/phase_quality.csv')
    detail=f'実行テスト数で正規化したテスト検出密度は前半期{phases.loc["Before","test_detections_per_100_tests"]:.2f}件/100テスト、後半期{phases.loc["After","test_detections_per_100_tests"]:.2f}件/100テスト。検出密度の低下は、品質向上だけでなく検出力低下でも生じる。未解決{metrics["open_at_cutoff"]}件を重要度・経過日数で別表にし、クローズ済み中央値の偏りを補足した。'
    title='ソフトウェア品質と欠陥の分析'
    hypothesis='検出件数、テスト規模、本番検出比率、未解決案件を組み合わせて品質上の優先課題を説明できるか。'

check('unique primary key',df.iloc[:,0].is_unique)
check('nonempty fact table',len(df)>0)
if not K.startswith('01'):
    check('required columns not null',df.drop(columns=[c for c in ['closed_date','resolution_days','age_days_at_cutoff'] if c in df]).notna().all().all())
if K.startswith('02'):
    check('valid flags',df.error.isin([0,1]).all())
    check('positive work nonnegative wait',(df.work_minutes>0).all() and (df.wait_minutes>=0).all())
if K.startswith('03'):
    check('valid resolution dates',df.resolution_days.dropna().ge(0).all())
    check('monthly tests unique',exp.month.is_unique and (exp.executed_tests>0).all())
save(df,'data/fact.csv')
conn=sqlite3.connect(P/'results/analysis.sqlite')
df.to_sql('fact',conn,index=False,if_exists='replace')
if K.startswith('03'):exp.to_sql('test_exposure',conn,index=False,if_exists='replace')
(P/'analysis.sql').write_text(sql,encoding='utf-8')
result=pd.read_sql_query(sql,conn);save(result,'results/sql_result.csv')
check('SQL group counts reconcile',int(result['tasks' if K.startswith('02') else 'defects' if K.startswith('03') else 'return_observations'].sum())==len(df)-(1 if K.startswith('01') else 0))
conn.close()
if K.startswith('01'):
    expected=df.groupby(df.date.str[:4]).monthly_return.mean().to_numpy()
    check('Python SQL monthly means match',np.allclose(expected,result.mean_monthly_return.to_numpy(),equal_nan=True))
elif K.startswith('02'):
    expected=df.groupby(['phase','complexity']).work_minutes.mean().to_numpy()
    check('Python SQL work means match',np.allclose(expected,result.avg_work_minutes.to_numpy()))
else:
    expected=df.groupby('module').stage.apply(lambda x:(x=='Production').mean())
    check('Python SQL production ratios match',all(np.isclose(expected[row.module],row.production_detection_share) for row in result.itertuples()))
(P/'results/metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'results/validation.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'data/DICTIONARY.md').write_text('# データ辞書\n\n粒度：'+('1行1か月。' if K.startswith('01') else '1行1完了タスク。' if K.startswith('02') else '1行1検出欠陥。別表は1行1か月。')+'\n\n'+'\n'.join(f'- `{k}`: {v}' for k,v in dictionary.items())+'\n\n小数の率は0–1。欠損はCSVの空欄。UTF-8 BOM付き。',encoding='utf-8')
(P/'powerbi/measures.dax').write_text(dax,encoding='utf-8')
model='''# Power BI Desktop 搭建と検証手順

状態：CSV、DAX、レイアウト仕様を提供。Desktopでの実装・動作検証は未実施。PBIXは同梱しない。

1. 「データを取得 → テキスト/CSV」で data/fact.csv を読み込み、テーブル名を fact にする。UTF-8、カンマ区切り。
2. date は日付、IDと分類と month はテキスト、率と時間は小数、フラグと件数は整数に設定。空欄はnullを保つ。
3. measures.dax の定義を一つずつ新規メジャーとして追加。率はパーセント表示。日付の自動階層ではなく date/month を軸に使う。
4. 16:9ページ。上部にタイトルとデータ種別、期間。次に4枚のKPIカード。中央に推移折れ線、下部に分類別テーブルを置く。HTMLレポートを配置見本とする。
5. 期間・分類スライサーを追加し、全選択時に results/metrics.json と照合する。単一分類、空の期間、複数月の選択で表示を点検する。0除算はBLANKを許容する。
6. 保存後に更新し、PBIXを開き直してCSVの参照先と指標値を検証する。GitHub掲載前に絶対パスを確認する。

Python・SQLの集計は実行済み。DAXの値はDesktopで別途照合が必要。
'''
if K.startswith('01'):
    model+='\n金融：価格リターンは選択範囲の最初と最後の月平均価格から計算。Volatilityは選択された行の保存済みリターンを使用し、最初の選択月の直前月価格も反映する。drawdown/rolling_vol_12m は2000年1月からの固定基準・固定窓で事前計算済み。スライサーでピークを再計算しないため「Full Baseline」と表示する。chartの指数も固定初月100。\n'
elif K.startswith('02'):
    model+='\n業務：カードは Tasks、Average Work Minutes、Error Rate、SLA Rate。complexity/teamで絞り込み、Before/Afterを列にしたマトリクスで比較する。Work Reduction はphaseフィルターのみを外す。dateを片方の期だけに絞ると比較対象が空になるので比較ページの期間は通年に固定する。\n'
else:
    model+='\n品質：data/test_exposure.csvもtest_exposure名で読み込む。DimMonth = DISTINCT(test_exposure[month]) を計算テーブルとして作り、DimMonth[month]からfact[month]、test_exposure[month]へ各1対多・単方向のリレーションを作る。月スライサーと軸はDimMonth[month]。テスト密度は全モジュールで表示し、module/severity/stageフィルターからの相互作用を無効にする（テスト数に分類別内訳がないため）。品質カードは件数、本番検出比率、解決中央値、未解決件数。NULL解決日数は中央値から除外。\n'
(P/'powerbi/BUILD.md').write_text(model,encoding='utf-8')
status='公開歴史データ' if K.startswith('01') else '模擬データ 個人学習プロジェクト'
readme=f'''# {title}

{status}。企業の実績や勤務先のデータを示すものではありません。

## 課題
{hypothesis}

## 分析方法
データ型・一意性・欠損・時系列を確認し、Pythonで指標を算出。SQLiteで別集計し、件数と主要指標を照合しました。処理結果は results/validation.json に記録しています。

## 主な結果
{findings}

## 改善提案
{rec}

## 追加の検証と解釈
{detail}

## 解釈上の制約
{limits}

## 再現手順
Python 3.11以降で `python -m pip install -r requirements.txt` を実行後、`python analyze.py`。ダウンロード不要で同梱データから再現できます。固定seed=20261030。出力先は本フォルダー。分析処理は入力データを変更しません（模擬ケースのraw.csvは生成し直します）。

## 成果物
- report.html：ブラウザーで閲覧可能な分析レポート
- data/fact.csv と DICTIONARY.md：分析用データと定義
- analyze.py：生成・加工・分析・検証の実行コード
- analysis.sql と results/analysis.sqlite：実行済みSQLとDB
- charts/：SVGグラフ
- powerbi/：DAXとDesktop構築仕様（PBIX未作成）

使用技術：Python、Pandas、NumPy、SQLite、SVG。Power BIは設計のみで、実装済みスキルとしては記載していません。
'''
(P/'README.md').write_text(readme,encoding='utf-8')

labels={'observations':'観測月数','cumulative_price_return':'累積価格リターン','annualized_price_growth':'年率換算成長率','annualized_volatility':'年率換算ボラティリティ','max_monthly_drawdown':'月次最大ドローダウン','tasks':'完了タスク件数','work_minutes_reduction_ratio':'平均作業時間の減少率','before_error_rate':'前半期エラー率','after_error_rate':'後半期エラー率','after_sla_rate':'後半期SLA達成率','defects':'検出欠陥数','production_detection_share':'本番検出比率','median_closed_resolution_days':'解決日数の中央値','open_at_cutoff':'基準日時点の未解決件数','reopened_share':'再オープン比率'}
counts={'observations','tasks','defects','open_at_cutoff','median_closed_resolution_days'}
cards=''.join(f'<div class="card"><small>{labels[k]}</small><strong>{format(v,",.0f") if k in counts else format(v,".1%")}</strong></div>' for k,v in metrics.items())
imgs=''.join(f'<figure><img src="charts/{p.name}" alt="{p.stem} analysis chart"/></figure>' for p in sorted((P/'charts').glob('*.svg')))
page=f'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title><style>
body{{font-family:"Yu Gothic",Meiryo,sans-serif;color:#172337;background:#f1f5f9;margin:0}}main{{max-width:1120px;margin:auto;padding:48px 24px}}header{{padding:32px;background:#102441;color:white;border-radius:18px}}h1{{font-size:32px;line-height:1.4}}.tag{{color:#93c5fd}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:24px 0}}.card,section,figure{{background:white;border-radius:14px;padding:22px;margin:14px 0;box-shadow:0 2px 8px #10244108}}.card strong{{display:block;font-size:25px;margin-top:12px}}small{{overflow-wrap:anywhere}}img{{width:100%}}p{{line-height:1.9}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{border:1px solid #dbe3ec;padding:10px;text-align:left}}th{{background:#edf2f7}}a{{color:#2563eb}}.table{{overflow:auto}}footer{{padding:22px;color:#64748b}}@media print{{body{{background:white}}main{{padding:0}}section,figure{{break-inside:avoid}}}}
</style><main><header><div class="tag">DATA ANALYTICS PORTFOLIO / {status}</div><h1>{title}</h1><p>{hypothesis}</p></header><div class="cards">{cards}</div><section><h2>主要な発見</h2><p>{findings}</p><p>{detail}</p><p>率はパーセント表示。解決日数は暦日。定義はデータ辞書とREADMEを参照。</p></section>{imgs}<section><h2>SQLによる検証結果</h2><div class="table">{result.to_html(index=False,border=0,float_format=lambda x:f'{x:.4f}')}</div></section><section><h2>意思決定への提案</h2><p>{rec}</p><h2>解釈の範囲</h2><p>{limits}</p></section><section><h2>再現と成果物</h2><p><a href="README.md">README</a> · <a href="data/fact.csv">CSV</a> · <a href="data/DICTIONARY.md">データ辞書</a> · <a href="analyze.py">Python</a> · <a href="analysis.sql">SQL</a> · <a href="powerbi/BUILD.md">Power BI仕様</a></p><p>検証 {len(checks)} 件すべて成功。Power BI Desktopの検証および実際の業務効果の検証は未実施。</p></section><footer>個人ポートフォリオ · 2026-10-30 · データと前提を明示した再現可能な分析</footer></main></html>'''
(P/'report.html').write_text(page,encoding='utf-8')
print(K,json.dumps(metrics),f'{len(checks)} checks passed')
