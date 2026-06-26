-- celldata.cellinfo：小区基础信息表
-- 正常由 CellData 导入流程自动创建（CREATE TABLE IF NOT EXISTS）；此处为前置兜底，
-- 避免在尚未导入时执行 CellData.sql 的 `UPDATE cellinfo ...` 因缺表报错。
CREATE TABLE IF NOT EXISTS `cellinfo` (
  `CGI` varchar(120) DEFAULT NULL,
  `eNodeBID` int DEFAULT NULL,
  `CellID` int DEFAULT NULL,
  `PLMN` varchar(100) DEFAULT NULL,
  `基站名称` varchar(200) DEFAULT NULL,
  `小区名称` varchar(200) DEFAULT NULL,
  `频点` varchar(50) DEFAULT NULL,
  `带宽` varchar(20) DEFAULT NULL,
  `制式` varchar(50) DEFAULT NULL,
  `功率` varchar(100) DEFAULT NULL,
  `网络` varchar(20) DEFAULT NULL,
  KEY `CGI` (`CGI`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
