-- =============================================================================
-- CellData 数据处理脚本（在 celldata 库执行）
-- 1) 规范化 cellinfo.带宽
-- 2) 重建频段特征库 sector_band_ref（频点/PLMN -> 制式/频段 对应表）
-- 3) 由 cellinfo 逆推 sector（扇区/物理站/制式/频段/带宽/站型/网络）
--    —— 不清空 sector，仅补充缺失 CGI，已有行（含人工修正）保留不覆盖
-- 逆推规则与准确率见 docs/sector_inference_research.md
-- =============================================================================

-- 1. 带宽规范化：空值补 0M，统一大写并以 M 结尾（如 20M）
UPDATE cellinfo SET `带宽` = IF(`带宽` IS NULL OR `带宽` = '', '0M', CONCAT(REPLACE(UPPER(`带宽`),'M',''), 'M'));

-- 2. 频段特征库：网络 + 频点区间(+PLMN) -> 制式/频段
--    700M 与 广电 同频点 763.25，由 PLMN 区分（460-00=移动700M，460-15=中国广电）
--    D频 与 3DMM 同频点同 PLMN 同带宽，cellinfo 无法区分，统一判 D频（3DMM 为天线属性）
DROP TABLE IF EXISTS sector_band_ref;
CREATE TABLE sector_band_ref (
  `网络` varchar(8),
  f_lo decimal(10,2),
  f_hi decimal(10,2),
  plmn varchar(16) NULL,
  `制式` varchar(20),
  `频段` varchar(20)
);
INSERT INTO sector_band_ref (`网络`,f_lo,f_hi,plmn,`制式`,`频段`) VALUES
('5G',4000,99999,NULL,'4.9G','4.9G'),
('5G',700,800,'460-00','700M','700M'),
('5G',700,800,'460-15','广电','广电'),
('5G',2000,3000,NULL,'2.6G','2.6G'),
('4G',900,1000,NULL,'FDD','FDD900'),
('4G',1000,1880,NULL,'FDD','FDD1800'),
('4G',1880,1920,NULL,'TDD','F频'),
('4G',1920,2110,NULL,'TDD','A频'),
('4G',2300,2400,NULL,'TDD','E频'),
('4G',2400,2700,NULL,'TDD','D频');

-- 3. 逆推暂存表：预处理小区名称（全角括号->半角、【】->()、去空格/制表符）
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

-- 3.1 设备码（[频率前缀]-Z[xx]-[扇区号]）剥离得到 base；尾部数字串；站型判定
--     站型：设备码尾字母 W=室分；名称含"微小"=微站；其余=宏站
UPDATE _sector_infer SET
  base = REGEXP_REPLACE(name1,'[A-Z0-9]+-Z[A-Z0-9]{2}-[0-9]+$',''),
  numstr = REGEXP_SUBSTR(name1,'[0-9]+$'),
  `站型` = CASE
    WHEN name1 REGEXP 'Z[A-Z]W-[0-9]+$' THEN '室分'
    WHEN name1 LIKE '%微小%' THEN '微站'
    ELSE '宏站' END;

-- 3.2 制式/频段：按特征库匹配；未命中回落 cellinfo 原制式
UPDATE _sector_infer t
JOIN sector_band_ref r
  ON r.`网络` = t.`网络`
 AND CAST(NULLIF(t.`频点`,'') AS DECIMAL(10,2)) >= r.f_lo
 AND CAST(NULLIF(t.`频点`,'') AS DECIMAL(10,2)) <  r.f_hi
 AND (r.plmn IS NULL OR r.plmn = t.PLMN)
SET t.`制式` = r.`制式`, t.`频段` = r.`频段`;
UPDATE _sector_infer SET `制式` = ci_zs, `频段` = ci_zs WHERE `制式` IS NULL;

-- 3.3 物理站（非 700M/广电）：去码后删全部括号注记，保留(微小X)并回贴；
--     再去掉不闭合的悬空开括号与孤立右括号
UPDATE _sector_infer SET `物理站` = CONCAT(
  TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
    base,'\\([^()]*\\)',''),'\\([^()]*\\)',''),'\\([^()]*\\)',''),'\\([^()]*$',''),'[)]+$',''),'^[)]+','')),
  IFNULL(REGEXP_SUBSTR(name1,'[(]微小[A-Z]?[)]'),''))
WHERE `制式` IS NULL OR `制式` NOT IN ('700M','广电');

-- 3.4 物理站（700M/广电）：取以"(江门"开头的括号内容为真实站址；
--     无则取外层（去 CBN- 前缀与注记）。括号内容以"共"开头属共建标注，归外层
UPDATE _sector_infer SET `物理站` =
  CASE WHEN REGEXP_SUBSTR(base,'\\(江门[^()]*') <> ''
       THEN TRIM(SUBSTRING(REGEXP_SUBSTR(base,'\\(江门[^()]*'),2))
       ELSE TRIM(REGEXP_REPLACE(REGEXP_REPLACE(base,'\\(.*$',''),'^CBN-?','')) END
WHERE `制式` IN ('700M','广电');

-- 3.5 扇区 = 物理站 + 扇区号（700M/广电取末位数字；其余取数字串 % 100）
UPDATE _sector_infer SET `扇区` = CONCAT(`物理站`,
  CASE WHEN numstr IS NULL OR numstr = '' THEN ''
       WHEN `制式` IN ('700M','广电') THEN RIGHT(numstr,1)
       ELSE CAST(CAST(numstr AS UNSIGNED) % 100 AS CHAR) END);

-- 4. 补缺写回 sector：仅插入 sector 中尚不存在的 CGI（区域留空，不参与逆推）
--    已存在的 CGI 一律保留，避免人工修正（如 3DMM、人工纠正的物理站/带宽）被覆盖
INSERT INTO sector (CGI,`扇区`,`物理站`,`区域`,`制式`,`频段`,`带宽`,`站型`,`网络`)
SELECT i.CGI, i.`扇区`, i.`物理站`, NULL, i.`制式`, i.`频段`, i.`带宽`, i.`站型`, i.`网络`
FROM _sector_infer i
LEFT JOIN sector s ON s.CGI = i.CGI
WHERE s.CGI IS NULL;

DROP TABLE _sector_infer;
