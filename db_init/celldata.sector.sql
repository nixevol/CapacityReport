-- celldata.sector：扇区表（CellData.sql 逆推写入的目标表）
-- 不会被任何导入流程自动创建，缺表会导致 CellData.sql 的 `INSERT INTO sector ...` 报错，
-- 因此必须前置建好结构。已有数据（含人工修正）由 CellData.sql「仅补缺不覆盖」保护。
CREATE TABLE IF NOT EXISTS `sector` (
  `CGI` varchar(120) DEFAULT NULL,
  `扇区` varchar(200) DEFAULT NULL,
  `物理站` varchar(200) DEFAULT NULL,
  `制式` varchar(50) DEFAULT NULL,
  `频段` varchar(50) DEFAULT NULL,
  `带宽` varchar(20) DEFAULT NULL,
  `站型` varchar(50) DEFAULT NULL,
  `网络` varchar(20) DEFAULT NULL,
  KEY `CGI` (`CGI`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
