SELECT module,COUNT(*) AS defects,
AVG(CASE WHEN stage='Production' THEN 1.0 ELSE 0 END) AS production_detection_share,
AVG(julianday(closed_date)-julianday(date)) AS mean_closed_resolution_days,
SUM(CASE WHEN closed_date IS NULL THEN 1 ELSE 0 END) AS open_at_cutoff
FROM fact GROUP BY module ORDER BY defects DESC;