-- =============================================================================
-- CellData 数据处理脚本（在 celldata 库执行）
-- 1) 规范化 cellinfo.带宽
-- 2) 由 cellinfo 逆推 sector（扇区/物理站/制式/频段/带宽/站型/网络）
--    —— 不清空 sector，仅补充缺失 CGI，已有行（含人工修正）保留不覆盖
-- 依赖的结构表（cellinfo / sector / 频段特征库 sector_band_ref）由程序前置检查
-- （app/db_init.py + db_init/ 目录）保证存在，缺表会自动按预设建好；sector_band_ref
-- 一经创建即持久保留，可在数据库中自行增改频段规则，本脚本不再重建以免冲掉自定义。
-- 逆推规则与准确率见 docs/sector_inference_research.md
-- =============================================================================

-- 1. 带宽规范化：空值补 0M，统一大写并以 M 结尾（如 20M）
UPDATE cellinfo SET `带宽` = IF(`带宽` IS NULL OR `带宽` = '', '0M', CONCAT(REPLACE(UPPER(`带宽`),'M',''), 'M'));

-- 2. 逆推暂存表：预处理小区名称（全角括号->半角、【】->()、去空格/制表符）
DROP TABLE IF EXISTS _sector_infer;
CREATE TABLE _sector_infer AS
SELECT
  c.CGI, c.`网络`, c.`带宽`, c.PLMN, c.`频点`, c.`制式` AS ci_zs,
  REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
    c.`小区名称`,' ',''),CHAR(9),''),'　',''),'（','('),'）',')'),'【','('),'】',')') AS name1
FROM cellinfo c;

ALTER TABLE _sector_infer
  ADD COLUMN `制式` varchar(20),
  ADD COLUMN `频段` varchar(20),
  ADD COLUMN `站型` varchar(10),
  ADD COLUMN numstr varchar(20),
  ADD COLUMN base varchar(220),
  ADD COLUMN `物理站` varchar(200),
  ADD COLUMN `扇区` varchar(210);

-- 2.1 设备码（[频率前缀]-Z[xx]-[扇区号]）剥离得到 base；尾部数字串；站型判定
--     站型：设备码尾字母 W=室分；名称含"微小"=微站；其余=宏站
UPDATE _sector_infer SET
  base = REGEXP_REPLACE(name1,'[A-Z0-9]+-Z[A-Z0-9]{2}-[0-9]+$',''),
  numstr = REGEXP_SUBSTR(name1,'[0-9]+$'),
  `站型` = CASE
    WHEN name1 REGEXP 'Z[A-Z]W-[0-9]+$' THEN '室分'
    WHEN name1 LIKE '%微小%' THEN '微站'
    ELSE '宏站' END;

-- 2.2 制式/频段：按特征库匹配；未命中回落 cellinfo 原制式
UPDATE _sector_infer t
JOIN sector_band_ref r
  ON r.`网络` = t.`网络`
 AND CAST(NULLIF(t.`频点`,'') AS DECIMAL(10,2)) >= r.`频点下限`
 AND CAST(NULLIF(t.`频点`,'') AS DECIMAL(10,2)) <  r.`频点上限`
 AND (r.`PLMN` IS NULL OR r.`PLMN` = t.PLMN)
SET t.`制式` = r.`制式`, t.`频段` = r.`频段`;
UPDATE _sector_infer SET `制式` = ci_zs, `频段` = ci_zs WHERE `制式` IS NULL;

-- 2.3 物理站（非 700M/广电）：去码后删全部括号注记，保留(微小X)并回贴；
--     再去掉不闭合的悬空开括号与孤立右括号
UPDATE _sector_infer SET `物理站` = CONCAT(
  TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
    base,'\\([^()]*\\)',''),'\\([^()]*\\)',''),'\\([^()]*\\)',''),'\\([^()]*$',''),'[)]+$',''),'^[)]+','')),
  IFNULL(REGEXP_SUBSTR(name1,'[(]微小[A-Z]?[)]'),''))
WHERE `制式` IS NULL OR `制式` NOT IN ('700M','广电');

-- 2.4 物理站（700M/广电）：取以"(江门"开头的括号内容为真实站址；
--     无则取外层（去 CBN- 前缀与注记）。括号内容以"共"开头属共建标注，归外层
UPDATE _sector_infer SET `物理站` =
  CASE WHEN REGEXP_SUBSTR(base,'\\(江门[^()]*') <> ''
       THEN TRIM(SUBSTRING(REGEXP_SUBSTR(base,'\\(江门[^()]*'),2))
       ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(base,'\\(.*$',''),'^CBN-?','')) END
WHERE `制式` IN ('700M','广电');

-- 2.5 扇区 = 物理站 + 扇区号（700M/广电取末位数字；其余取数字串 % 100）
UPDATE _sector_infer SET `扇区` = CONCAT(`物理站`,
  CASE WHEN numstr IS NULL OR numstr = '' THEN ''
       WHEN `制式` IN ('700M','广电') THEN RIGHT(numstr,1)
       ELSE CAST(CAST(numstr AS UNSIGNED) % 100 AS CHAR) END);

-- 3. 补缺写回 sector：仅插入 sector 中尚不存在的 CGI
--    已存在的 CGI 一律保留，避免人工修正（如 3DMM、人工纠正的物理站/带宽）被覆盖
INSERT INTO sector (CGI,`扇区`,`物理站`,`制式`,`频段`,`带宽`,`站型`,`网络`)
SELECT i.CGI, i.`扇区`, i.`物理站`, i.`制式`, i.`频段`, i.`带宽`, i.`站型`, i.`网络`
FROM _sector_infer i
LEFT JOIN sector s ON s.CGI = i.CGI
WHERE s.CGI IS NULL;

DROP TABLE _sector_infer;
