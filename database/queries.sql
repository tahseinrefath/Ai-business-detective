-- Reusable analysis queries (PostgreSQL). Replace :dataset_id with a value.

-- 1. Monthly KPIs
SELECT date_trunc('month', order_date)::date AS month,
       SUM(sales) AS sales, SUM(profit) AS profit,
       ROUND(100 * SUM(profit) / NULLIF(SUM(sales), 0), 2) AS margin_pct,
       COUNT(*) AS orders
FROM sales WHERE dataset_id = :dataset_id
GROUP BY 1 ORDER BY 1;

-- 2. Which category/product/region moved profit between two months?
WITH m AS (
  SELECT product, region,
         SUM(profit) FILTER (WHERE date_trunc('month', order_date) = DATE '2026-09-01') AS prev_profit,
         SUM(profit) FILTER (WHERE date_trunc('month', order_date) = DATE '2026-10-01') AS curr_profit
  FROM sales WHERE dataset_id = :dataset_id GROUP BY product, region)
SELECT product, region, COALESCE(prev_profit,0) AS prev_profit, COALESCE(curr_profit,0) AS curr_profit,
       COALESCE(curr_profit,0) - COALESCE(prev_profit,0) AS delta
FROM m ORDER BY delta ASC LIMIT 10;

-- 3. Top products by profit
SELECT product, SUM(sales) AS sales, SUM(profit) AS profit
FROM sales WHERE dataset_id = :dataset_id GROUP BY product ORDER BY profit DESC;

-- 4. Do discounts eat profit? (average margin by discount band)
SELECT CASE WHEN discount_pct < 5 THEN '<5%' WHEN discount_pct < 10 THEN '5-10%' ELSE '10%+' END AS band,
       ROUND(100 * SUM(profit) / NULLIF(SUM(sales),0), 2) AS margin_pct, COUNT(*) AS orders
FROM sales WHERE dataset_id = :dataset_id GROUP BY 1 ORDER BY 1;
