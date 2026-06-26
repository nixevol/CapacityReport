-- celldata.sector_band_ref：频段特征库（频点区间 + PLMN -> 制式/频段），供 CellData.sql 逆推使用
-- 频点区间为左闭右开 [频点下限, 频点上限)；PLMN 为空表示该频段不分运营商。
-- 仅在该表不存在时由前置检查执行本文件（建表 + 写入下列预设）；
-- 表已存在则完全跳过本文件，保留用户对特征库的自定义，不会被覆盖或重置。
CREATE TABLE IF NOT EXISTS `sector_band_ref` (
  `网络` varchar(8) DEFAULT NULL,
  `频点下限` decimal(10,2) DEFAULT NULL,
  `频点上限` decimal(10,2) DEFAULT NULL,
  `PLMN` varchar(16) DEFAULT NULL,
  `制式` varchar(20) DEFAULT NULL,
  `频段` varchar(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `sector_band_ref` (`网络`,`频点下限`,`频点上限`,`PLMN`,`制式`,`频段`) VALUES
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
