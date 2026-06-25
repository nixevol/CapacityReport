# Update: 2026/06/25 15:33:00

SET GLOBAL wait_timeout = 86400;
SET GLOBAL innodb_buffer_pool_size = 1073741824;
DROP TABLE IF EXISTS `4G`;
DROP TABLE IF EXISTS `5G`;
DROP TABLE IF EXISTS `4G_Date`;
DROP TABLE IF EXISTS `4G_MAX`;
DROP TABLE IF EXISTS `CCE_MAX`;
DROP TABLE IF EXISTS `ULPRB_MAX`;
DROP TABLE IF EXISTS `DLPRB_MAX`;
DROP TABLE IF EXISTS `4G_MAX_IDX`;
DROP TABLE IF EXISTS `CCE_MAX_IDX`;
DROP TABLE IF EXISTS `ULPRB_MAX_IDX`;
DROP TABLE IF EXISTS `DLPRB_MAX_IDX`;
DROP TABLE IF EXISTS `日流量`;
DROP TABLE IF EXISTS `4G日均流量`;
DROP TABLE IF EXISTS `4G_结果表`;

DROP TABLE IF EXISTS `5G_Date`;
DROP TABLE IF EXISTS `5G_MAX`;
DROP TABLE IF EXISTS `5G_MAX_IDX`;
DROP TABLE IF EXISTS `5G日均流量`;
DROP TABLE IF EXISTS `5G_结果表`;
DROP TABLE IF EXISTS `_rj_yd`;
DROP TABLE IF EXISTS `_rj_gd`;
DROP TABLE IF EXISTS `rj`;

UPDATE `4G_UD` SET
	`上下行总流量_GB` = IFNULL(`上下行总流量_GB`,0),
	`ERAB流量` = IFNULL(`ERAB流量`,0),
	`上行流量_GB` = IFNULL(`上行流量_GB`,0),
	`下行流量_GB` = IFNULL(`下行流量_GB`,0),
	`用户面平均激活UE数` = IFNULL(`用户面平均激活UE数`,0),
	`RRC连接建立最大用户数` = IFNULL(`RRC连接建立最大用户数`,0),
	`上行PUSCH利用率` = IFNULL(`上行PUSCH利用率`,0),
	`下行PDSCH利用率` = IFNULL(`下行PDSCH利用率`,0),
	`PDCCH资源利用率` = IFNULL(`PDCCH资源利用率`,0),
	`用户面最大激活UE数` = IFNULL(`用户面最大激活UE数`,0);

UPDATE `5G_UD` SET
	`5G上下行总流量_GB` = IFNULL(`5G上下行总流量_GB`,0),
	`5G上行流量_GB` = IFNULL(`5G上行流量_GB`,0),
	`5G下行流量_GB` = IFNULL(`5G下行流量_GB`,0),
	`小区平均激活UE数` = IFNULL(`小区平均激活UE数`,0),
	`RRC连接最大连接用户数` = IFNULL(`RRC连接最大连接用户数`,0),
	`RRC连接平均连接用户数` = IFNULL(`RRC连接平均连接用户数`,0),
	`小区最大激活UE数` = IFNULL(`小区最大激活UE数`,0),
	`上行PRB平均利用率` = IFNULL(`上行PRB平均利用率`,0),
	`下行PRB平均利用率` = IFNULL(`下行PRB平均利用率`,0),
	`小区下行RLC_SDU字节数_MByte` = IFNULL(`小区下行RLC_SDU字节数_MByte`,0),
	`小区上行RLC_SDU字节数_MByte` = IFNULL(`小区上行RLC_SDU字节数_MByte`,0),
	`PDCCH信道动态CCE占用率` = IFNULL(`PDCCH信道动态CCE占用率`,0),
	`平均单Flow流量_MB` = IFNULL(`平均单Flow流量_MB`,0);

CREATE TABLE `4G` AS SELECT * FROM `4G_UD`;
CREATE TABLE `5G` AS SELECT * FROM `5G_UD`;

ALTER TABLE `4G`
ADD COLUMN `日期` date NULL FIRST,
MODIFY COLUMN `日期时间` datetime,
ADD COLUMN `CGI` varchar(100) NULL AFTER `日期时间`,
MODIFY COLUMN `网元ID` int,
MODIFY COLUMN `基站名称` varchar(200),
MODIFY COLUMN `小区名称` varchar(200),
MODIFY COLUMN `cellLocalId` int,
MODIFY COLUMN `eNodeBId` int,
MODIFY COLUMN `上下行总流量_GB` float,
MODIFY COLUMN `ERAB流量` float,
MODIFY COLUMN `上行流量_GB` float,
MODIFY COLUMN `下行流量_GB` float,
MODIFY COLUMN `用户面平均激活UE数` float,
MODIFY COLUMN `RRC连接建立最大用户数` int,
MODIFY COLUMN `上行PUSCH利用率` float,
MODIFY COLUMN `下行PDSCH利用率` float,
MODIFY COLUMN `PDCCH资源利用率` float,
MODIFY COLUMN `用户面最大激活UE数` int;

ALTER TABLE `5G`
ADD COLUMN `日期` date NULL FIRST,
MODIFY COLUMN `日期时间` datetime,
ADD COLUMN `NCGI` varchar(100) NULL AFTER `日期时间`,
MODIFY COLUMN `网元ID` int,
MODIFY COLUMN `CU小区配置名称` varchar(200),
MODIFY COLUMN `cellLocalId` int,
MODIFY COLUMN `gNBId` int,
MODIFY COLUMN `gNBplmn` varchar(200),
MODIFY COLUMN `5G上下行总流量_GB` float,
MODIFY COLUMN `5G上行流量_GB` float,
MODIFY COLUMN `5G下行流量_GB` float,
MODIFY COLUMN `小区平均激活UE数` float,
MODIFY COLUMN `RRC连接最大连接用户数` int,
MODIFY COLUMN `RRC连接平均连接用户数` float,
MODIFY COLUMN `小区最大激活UE数` float,
MODIFY COLUMN `上行PRB平均利用率` float,
MODIFY COLUMN `下行PRB平均利用率` float,
MODIFY COLUMN `小区下行RLC_SDU字节数_MByte` float,
MODIFY COLUMN `小区上行RLC_SDU字节数_MByte` float,
MODIFY COLUMN `PDCCH信道动态CCE占用率` float,
MODIFY COLUMN `平均单Flow流量_MB` float;

UPDATE `4G` SET `日期` = DATE_FORMAT(`日期时间`, '%Y-%m-%d'), `CGI` = CONCAT("460-00-",`eNodeBId`,"-",`cellLocalId`);
UPDATE `5G` SET `gNBplmn` = "460-00" WHERE `gNBplmn` IS NULL;
UPDATE `5G` SET `日期` = DATE_FORMAT(`日期时间`, '%Y-%m-%d'), `NCGI` = CONCAT(`gNBplmn`,"-",`gNBId`,"-",`cellLocalId`);

ALTER TABLE `4G`
ADD INDEX(`日期`),
ADD INDEX(`日期时间`),
ADD INDEX(`CGI`),
ADD INDEX `TC`(`日期时间`, `CGI`),
ADD INDEX `DC`(`日期`, `CGI`);

ALTER TABLE `5G`
ADD INDEX(`日期`),
ADD INDEX(`日期时间`),
ADD INDEX(`NCGI`),
ADD INDEX `TC`(`日期时间`, `NCGI`),
ADD INDEX `DC`(`日期`, `NCGI`);


CREATE TEMPORARY TABLE IF NOT EXISTS `CCE_MAX_IDX`(
	SELECT
		`日期`,
		`CGI`,
		MAX(`PDCCH资源利用率`) AS `PDCCH资源利用率_忙时`
	FROM `4G`
	GROUP BY `日期`, `CGI`
);

ALTER TABLE `CCE_MAX_IDX`
ADD COLUMN `日期时间` datetime,
ADD INDEX `DC`(`日期`, `CGI`, `PDCCH资源利用率_忙时`),
ADD INDEX `TC`(`日期时间`, `CGI`);

UPDATE `CCE_MAX_IDX` INNER JOIN `4G`
ON
	`CCE_MAX_IDX`.`日期` = `4G`.`日期` AND
	`CCE_MAX_IDX`.`CGI` = `4G`.`CGI` AND
	`CCE_MAX_IDX`.`PDCCH资源利用率_忙时` = `4G`.`PDCCH资源利用率`
SET
	`CCE_MAX_IDX`.`日期时间` = `4G`.`日期时间`;


CREATE TEMPORARY TABLE IF NOT EXISTS `CCE_MAX` (
	SELECT `4G`.*
	FROM `CCE_MAX_IDX` LEFT JOIN `4G`
	ON `CCE_MAX_IDX`.`CGI` = `4G`.`CGI` AND
		`CCE_MAX_IDX`.`日期时间` = `4G`.`日期时间`
);

DROP TABLE IF EXISTS `CCE_MAX_IDX`;

CREATE TEMPORARY TABLE IF NOT EXISTS `ULPRB_MAX_IDX`(
	SELECT
		`日期`,
		`CGI`,
		MAX(`上行PUSCH利用率`) AS `上行PUSCH利用率_忙时`
	FROM `4G`
	GROUP BY `日期`, `CGI`
);

ALTER TABLE `ULPRB_MAX_IDX`
ADD COLUMN `日期时间` datetime,
ADD INDEX `DC`(`日期`, `CGI`, `上行PUSCH利用率_忙时`),
ADD INDEX `TC`(`日期时间`, `CGI`);

UPDATE `ULPRB_MAX_IDX` INNER JOIN `4G`
ON
	`ULPRB_MAX_IDX`.`日期` = `4G`.`日期` AND
	`ULPRB_MAX_IDX`.`CGI` = `4G`.`CGI` AND
	`ULPRB_MAX_IDX`.`上行PUSCH利用率_忙时` = `4G`.`上行PUSCH利用率`
SET
	`ULPRB_MAX_IDX`.`日期时间` = `4G`.`日期时间`;

CREATE TABLE IF NOT EXISTS `ULPRB_MAX` (
	SELECT `4G`.*
	FROM `ULPRB_MAX_IDX` LEFT JOIN `4G`
	ON `ULPRB_MAX_IDX`.`CGI` = `4G`.`CGI` AND
		`ULPRB_MAX_IDX`.`日期时间` = `4G`.`日期时间`
);

DROP TABLE IF EXISTS `ULPRB_MAX_IDX`;

CREATE TEMPORARY TABLE IF NOT EXISTS `DLPRB_MAX_IDX`(
	SELECT `日期`, `CGI`, MAX(`下行PDSCH利用率`) AS `下行PDSCH利用率_忙时`
	FROM `4G` GROUP BY `日期`, `CGI`
);

ALTER TABLE `DLPRB_MAX_IDX`
ADD COLUMN `日期时间` datetime,
ADD INDEX `DC`(`日期`, `CGI`, `下行PDSCH利用率_忙时`),
ADD INDEX `TC`(`日期时间`, `CGI`);

UPDATE `DLPRB_MAX_IDX` INNER JOIN `4G`
ON
	`DLPRB_MAX_IDX`.`日期` = `4G`.`日期` AND
	`DLPRB_MAX_IDX`.`CGI` = `4G`.`CGI` AND
	`DLPRB_MAX_IDX`.`下行PDSCH利用率_忙时` = `4G`.`下行PDSCH利用率`
SET
	`DLPRB_MAX_IDX`.`日期时间` = `4G`.`日期时间`;

CREATE TEMPORARY TABLE IF NOT EXISTS `DLPRB_MAX` (
	SELECT `4G`.*
	FROM `DLPRB_MAX_IDX` LEFT JOIN `4G`
	ON `DLPRB_MAX_IDX`.`CGI` = `4G`.`CGI` AND
		`DLPRB_MAX_IDX`.`日期时间` = `4G`.`日期时间`
);

DROP TABLE IF EXISTS `DLPRB_MAX_IDX`;

ALTER TABLE `CCE_MAX` ADD INDEX `DC`(`日期`, `CGI`);
ALTER TABLE `DLPRB_MAX` ADD INDEX `DC`(`日期`, `CGI`);
ALTER TABLE `ULPRB_MAX` ADD INDEX `DC`(`日期`, `CGI`);


CREATE TEMPORARY TABLE IF NOT EXISTS `4G_Date` (SELECT `日期`, `CGI` FROM `4G` GROUP BY `日期`, `CGI`);
ALTER TABLE `4G_Date` ADD INDEX `DC`(`日期`, `CGI`);


CREATE TEMPORARY TABLE IF NOT EXISTS `4G_MAX_IDX` (
	SELECT
		`4G_Date`.`日期`,
		`4G_Date`.`CGI`,
		GREATEST(`ULPRB_MAX`.`上行PUSCH利用率`, `DLPRB_MAX`.`下行PDSCH利用率`, `CCE_MAX`.`PDCCH资源利用率`) AS `最大值`
	FROM
		`4G_Date`
	INNER JOIN
		`DLPRB_MAX`
	ON
		`4G_Date`.`日期` = `DLPRB_MAX`.`日期` AND
		`4G_Date`.`CGI` = `DLPRB_MAX`.`CGI`
	INNER JOIN
		`CCE_MAX`
	ON
		`4G_Date`.`日期` = `CCE_MAX`.`日期` AND
		`4G_Date`.`CGI` = `CCE_MAX`.`CGI`
	INNER JOIN
		`ULPRB_MAX`
	ON
		`4G_Date`.`日期` = `ULPRB_MAX`.`日期` AND
		`4G_Date`.`CGI` = `ULPRB_MAX`.`CGI`
);
DROP TABLE IF EXISTS `4G_Date`;
ALTER TABLE `4G_MAX_IDX` ADD INDEX `DC`(`日期`, `CGI`), ADD INDEX (`最大值`);

CREATE TABLE IF NOT EXISTS `4G_MAX` (
	SELECT * FROM `4G` LIMIT 0
);

ALTER TABLE `4G_MAX` ADD INDEX (`日期`), ADD INDEX (`CGI`), ADD INDEX `DC` (`日期`, `CGI`), ADD INDEX `idx`(`CGI`, `基站名称`, `小区名称`);

TRUNCATE `4G_MAX`;
INSERT INTO `4G_MAX`
	SELECT `ULPRB_MAX`.* FROM `ULPRB_MAX` INNER JOIN `4G_MAX_IDX`
	ON
		`ULPRB_MAX`.`日期` = `4G_MAX_IDX`.`日期` AND
		`ULPRB_MAX`.`CGI` = `4G_MAX_IDX`.`CGI` AND
		`ULPRB_MAX`.`上行PUSCH利用率` = `4G_MAX_IDX`.`最大值`;

DELETE FROM `DLPRB_MAX` WHERE `日期` IS NULL;
INSERT INTO `4G_MAX`
	SELECT `DLPRB_MAX`.* FROM `DLPRB_MAX` INNER JOIN `4G_MAX_IDX`
	ON
		`DLPRB_MAX`.`日期` = `4G_MAX_IDX`.`日期` AND
		`DLPRB_MAX`.`CGI` = `4G_MAX_IDX`.`CGI` AND
		`DLPRB_MAX`.`下行PDSCH利用率` = `4G_MAX_IDX`.`最大值`
	WHERE NOT EXISTS (
		SELECT 1 FROM `4G_MAX`
		WHERE `4G_MAX`.`日期` = `DLPRB_MAX`.`日期`
		  AND `4G_MAX`.`CGI` = `DLPRB_MAX`.`CGI`
	);

DELETE FROM `CCE_MAX` WHERE `日期` IS NULL;
INSERT INTO `4G_MAX`
	SELECT `CCE_MAX`.* FROM `CCE_MAX` INNER JOIN `4G_MAX_IDX`
	ON
		`CCE_MAX`.`日期` = `4G_MAX_IDX`.`日期` AND
		`CCE_MAX`.`CGI` = `4G_MAX_IDX`.`CGI` AND
		`CCE_MAX`.`PDCCH资源利用率` = `4G_MAX_IDX`.`最大值`
	WHERE NOT EXISTS (
		SELECT 1 FROM `4G_MAX`
		WHERE `4G_MAX`.`日期` = `CCE_MAX`.`日期`
		  AND `4G_MAX`.`CGI` = `CCE_MAX`.`CGI`
	);


DROP TABLE IF EXISTS `CCE_MAX`;
DROP TABLE IF EXISTS `ULPRB_MAX`;
DROP TABLE IF EXISTS `DLPRB_MAX`;
DROP TABLE IF EXISTS `4G_MAX_IDX`;

CREATE TEMPORARY TABLE IF NOT EXISTS `日流量`(SELECT `日期`, `CGI`, SUM(`上下行总流量_GB`) AS `日流量` FROM `4G` GROUP BY `日期`, `CGI`);
ALTER TABLE `日流量` ADD INDEX (`CGI`);
DROP TABLE IF EXISTS `4G日均流量`;
CREATE TEMPORARY TABLE IF NOT EXISTS `4G日均流量` (
	SELECT `CGI`, AVG(`日流量`) AS `日均流量`, COUNT(`日期`) AS `流量有效天数` FROM `日流量` WHERE `日流量` > 0 GROUP BY `CGI`
);


CREATE TABLE IF NOT EXISTS `4G_结果表` (
	SELECT `CGI`, `基站名称`, `小区名称`,
		ROUND(AVG(`上下行总流量_GB`),6) AS `自忙时流量（GB）`,
		ROUND(AVG(`ERAB流量`),6) AS `ERAB流量`,
		ROUND(AVG(`上行流量_GB`),6) AS `上行流量（GB）`,
		ROUND(AVG(`下行流量_GB`),6) AS `下行流量（GB）`,
		ROUND(AVG(`用户面平均激活UE数`),6) AS `用户面平均激活UE数`,
		ROUND(AVG(`RRC连接建立最大用户数`),6) AS `YY-RRC连接建立最大用户数`,
		ROUND(AVG(`上行PUSCH利用率`),6) AS `上行PUSCH利用率`,
		ROUND(AVG(`下行PDSCH利用率`),6) AS `下行PDSCH利用率`,
		ROUND(AVG(`PDCCH资源利用率`),6) AS `PDCCH资源利用率`,
		ROUND(AVG(`用户面最大激活UE数`),6) AS `用户面最大激活UE数`
	FROM `4G_MAX` GROUP BY `CGI`, `基站名称`, `小区名称`
);
DROP TABLE IF EXISTS `4G_MAX`;
ALTER TABLE `4G_结果表` ADD COLUMN `日均流量（GB）` DOUBLE AFTER `小区名称`, ADD INDEX (`CGI`);
ALTER TABLE `4G日均流量` ADD INDEX (`CGI`);
UPDATE `4G_结果表` INNER JOIN `4G日均流量`
ON `4G_结果表`.`CGI` = `4G日均流量`.`CGI`
SET `4G_结果表`.`日均流量（GB）` = ROUND(`4G日均流量`.`日均流量`,6);

DROP TABLE IF EXISTS `日流量`;
DROP TABLE IF EXISTS `4G日均流量`;
DROP TABLE IF EXISTS `4G`;


# 5G脚本

CREATE TEMPORARY TABLE IF NOT EXISTS `ULPRB_MAX_IDX`(
	SELECT
		`日期`,
		`NCGI`,
		MAX(`上行PRB平均利用率`) AS `上行PRB平均利用率_忙时`
	FROM `5G`
	GROUP BY `日期`, `NCGI`
);

ALTER TABLE `ULPRB_MAX_IDX`
ADD COLUMN `日期时间` datetime,
ADD INDEX `DC`(`日期`, `NCGI`, `上行PRB平均利用率_忙时`),
ADD INDEX `TC`(`日期时间`, `NCGI`);

UPDATE `ULPRB_MAX_IDX` INNER JOIN `5G`
ON
	`ULPRB_MAX_IDX`.`日期` = `5G`.`日期` AND
	`ULPRB_MAX_IDX`.`NCGI` = `5G`.`NCGI` AND
	`ULPRB_MAX_IDX`.`上行PRB平均利用率_忙时` = `5G`.`上行PRB平均利用率`
SET
	`ULPRB_MAX_IDX`.`日期时间` = `5G`.`日期时间`;

CREATE TEMPORARY TABLE IF NOT EXISTS `ULPRB_MAX` (
	SELECT `5G`.*
	FROM `ULPRB_MAX_IDX` LEFT JOIN `5G`
	ON `ULPRB_MAX_IDX`.`NCGI` = `5G`.`NCGI` AND
		`ULPRB_MAX_IDX`.`日期时间` = `5G`.`日期时间`
);

CREATE TEMPORARY TABLE IF NOT EXISTS `DLPRB_MAX_IDX`(
	SELECT
		`日期`,
		`NCGI`,
		MAX(`下行PRB平均利用率`) AS `下行PRB平均利用率_忙时`
	FROM `5G`
	GROUP BY `日期`, `NCGI`
);

ALTER TABLE `DLPRB_MAX_IDX`
ADD COLUMN `日期时间` datetime,
ADD INDEX `DC`(`日期`, `NCGI`, `下行PRB平均利用率_忙时`),
ADD INDEX `TC`(`日期时间`, `NCGI`);

UPDATE `DLPRB_MAX_IDX` INNER JOIN `5G`
ON
	`DLPRB_MAX_IDX`.`日期` = `5G`.`日期` AND
	`DLPRB_MAX_IDX`.`NCGI` = `5G`.`NCGI` AND
	`DLPRB_MAX_IDX`.`下行PRB平均利用率_忙时` = `5G`.`下行PRB平均利用率`
SET
	`DLPRB_MAX_IDX`.`日期时间` = `5G`.`日期时间`;

CREATE TEMPORARY TABLE IF NOT EXISTS `DLPRB_MAX` (
	SELECT `5G`.*
	FROM `DLPRB_MAX_IDX` LEFT JOIN `5G`
	ON `DLPRB_MAX_IDX`.`NCGI` = `5G`.`NCGI` AND
		`DLPRB_MAX_IDX`.`日期时间` = `5G`.`日期时间`
);

DROP TABLE IF EXISTS `DLPRB_MAX_IDX`;
ALTER TABLE `DLPRB_MAX` ADD INDEX `DC`(`日期`, `NCGI`);
ALTER TABLE `ULPRB_MAX` ADD INDEX `DC`(`日期`, `NCGI`);

DROP TABLE IF EXISTS `5G_Date`;
CREATE TEMPORARY TABLE IF NOT EXISTS `5G_Date` (
	SELECT `日期`, `NCGI` FROM `5G` GROUP BY `日期`, `NCGI`
);
ALTER TABLE `5G_Date` ADD INDEX `DC`(`日期`, `NCGI`);

CREATE TEMPORARY TABLE IF NOT EXISTS `5G_MAX_IDX` (
	SELECT
		`5G_Date`.`日期`,
		`5G_Date`.`NCGI`,
		GREATEST(`ULPRB_MAX`.`上行PRB平均利用率`, `DLPRB_MAX`.`下行PRB平均利用率`) AS `最大值`
	FROM
		`5G_Date`
	INNER JOIN
		`DLPRB_MAX`
	ON
		`5G_Date`.`日期` = `DLPRB_MAX`.`日期` AND
		`5G_Date`.`NCGI` = `DLPRB_MAX`.`NCGI`
	INNER JOIN
		`ULPRB_MAX`
	ON
		`5G_Date`.`日期` = `ULPRB_MAX`.`日期` AND
		`5G_Date`.`NCGI` = `ULPRB_MAX`.`NCGI`
);

DROP TABLE IF EXISTS `5G_Date`;
ALTER TABLE `5G_MAX_IDX` ADD INDEX `DC`(`日期`, `NCGI`), ADD INDEX (`最大值`);

CREATE TABLE IF NOT EXISTS `5G_MAX` (
	SELECT * FROM `5G` LIMIT 0
);

ALTER TABLE `5G_MAX` ADD INDEX (`日期`), ADD INDEX (`NCGI`), ADD INDEX `DC` (`日期`, `NCGI`), ADD INDEX `idx`(`NCGI`, `CU小区配置名称`);

TRUNCATE `5G_MAX`;
INSERT INTO `5G_MAX`
	SELECT `ULPRB_MAX`.* FROM `ULPRB_MAX` INNER JOIN `5G_MAX_IDX`
	ON
		`ULPRB_MAX`.`日期` = `5G_MAX_IDX`.`日期` AND
		`ULPRB_MAX`.`NCGI` = `5G_MAX_IDX`.`NCGI` AND
		`ULPRB_MAX`.`上行PRB平均利用率` = `5G_MAX_IDX`.`最大值`;

DELETE FROM `DLPRB_MAX` WHERE `日期` IS NULL;
INSERT INTO `5G_MAX`
	SELECT `DLPRB_MAX`.* FROM `DLPRB_MAX` INNER JOIN `5G_MAX_IDX`
	ON
		`DLPRB_MAX`.`日期` = `5G_MAX_IDX`.`日期` AND
		`DLPRB_MAX`.`NCGI` = `5G_MAX_IDX`.`NCGI` AND
		`DLPRB_MAX`.`下行PRB平均利用率` = `5G_MAX_IDX`.`最大值`
	WHERE NOT EXISTS (
		SELECT 1 FROM `5G_MAX`
		WHERE `5G_MAX`.`日期` = `DLPRB_MAX`.`日期`
		  AND `5G_MAX`.`NCGI` = `DLPRB_MAX`.`NCGI`
	);

DROP TABLE IF EXISTS `ULPRB_MAX`;
DROP TABLE IF EXISTS `DLPRB_MAX`;
DROP TABLE IF EXISTS `5G_MAX_IDX`;

CREATE TEMPORARY TABLE IF NOT EXISTS `日流量`(SELECT `日期`, `NCGI`, SUM(`5G上下行总流量_GB`) AS `日流量` FROM `5G` GROUP BY `日期`, `NCGI`);
ALTER TABLE `日流量` ADD INDEX (`NCGI`);
CREATE TEMPORARY TABLE IF NOT EXISTS `5G日均流量` (
	SELECT `NCGI`, AVG(`日流量`) AS `日均流量`, COUNT(`日期`) AS `流量有效天数` FROM `日流量` WHERE `日流量` > 0 GROUP BY `NCGI`
);

CREATE TABLE IF NOT EXISTS `5G_结果表` (
	SELECT `NCGI`, `CU小区配置名称`,
		ROUND(AVG(`5G上下行总流量_GB`),6) AS `5G上下行总流量（上行PDCP PDU数据量+下行PDCP成功发送数据量）(GB)`,
		ROUND(AVG(`5G上行流量_GB`),6) AS `5G上行流量（上行PDCP PDU数据量）(GB)`,
		ROUND(AVG(`5G下行流量_GB`),6) AS `5G下行流量（下行PDCP成功发送数据量）(GB)`,
		ROUND(AVG(`小区平均激活UE数`),6) AS `小区平均激活UE数`,
		ROUND(AVG(`RRC连接最大连接用户数`),6) AS `RRC连接最大连接用户数`,
		ROUND(AVG(`RRC连接平均连接用户数`),6) AS `RRC连接平均连接用户数`,
		ROUND(AVG(`小区最大激活UE数`),6) AS `小区最大激活UE数`,
		ROUND(AVG(`上行PRB平均利用率`),6) AS `上行PRB平均利用率`,
		ROUND(AVG(`下行PRB平均利用率`),6) AS `下行PRB平均利用率`,
		ROUND(AVG(`PDCCH信道动态CCE占用率`),6) AS `PDCCH信道CCE占用率（动态）(%)`,
		ROUND(AVG(`小区下行RLC_SDU字节数_MByte`),6) AS `小区下行RLC SDU字节数(MByte)`,
		ROUND(AVG(`小区上行RLC_SDU字节数_MByte`),6) AS `小区上行RLC SDU字节数(MByte)`,
		ROUND(AVG(`平均单Flow流量_MB`),6) AS `单Flow流量(MB)`
	FROM `5G_MAX` GROUP BY `NCGI`, `CU小区配置名称`
);

ALTER TABLE `5G_结果表` ADD COLUMN `日均流量（GB）` DOUBLE AFTER `CU小区配置名称`, ADD INDEX (`NCGI`);
ALTER TABLE `5G日均流量` ADD INDEX (`NCGI`);
UPDATE `5G_结果表` INNER JOIN `5G日均流量`
ON `5G_结果表`.`NCGI` = `5G日均流量`.`NCGI`
SET `5G_结果表`.`日均流量（GB）` = ROUND(`5G日均流量`.`日均流量`,6);

DROP TABLE IF EXISTS `日流量`;
DROP TABLE IF EXISTS `5G日均流量`;
DROP TABLE IF EXISTS `4G`;
DROP TABLE IF EXISTS `5G`;
DROP TABLE IF EXISTS `5G_MAX`;

UPDATE `4G_结果表` SET `日均流量（GB）` = IFNULL(`日均流量（GB）`, 0),
`自忙时流量（GB）` = IFNULL(`自忙时流量（GB）`, 0),
`ERAB流量` = IFNULL(`ERAB流量`, 0),
`上行流量（GB）` = IFNULL(`上行流量（GB）`, 0),
`下行流量（GB）` = IFNULL(`下行流量（GB）`, 0),
`用户面平均激活UE数` = IFNULL(`用户面平均激活UE数`, 0),
`YY-RRC连接建立最大用户数` = IFNULL(`YY-RRC连接建立最大用户数`, 0),
`上行PUSCH利用率` = IFNULL(`上行PUSCH利用率`, 0),
`下行PDSCH利用率` = IFNULL(`下行PDSCH利用率`, 0),
`PDCCH资源利用率` = IFNULL(`PDCCH资源利用率`, 0),
`用户面最大激活UE数` = IFNULL(`用户面最大激活UE数`, 0);

UPDATE `5G_结果表` SET
`日均流量（GB）` = IFNULL(`日均流量（GB）`,0),
`5G上下行总流量（上行PDCP PDU数据量+下行PDCP成功发送数据量）(GB)` = IFNULL(`5G上下行总流量（上行PDCP PDU数据量+下行PDCP成功发送数据量）(GB)`,0),
`5G上行流量（上行PDCP PDU数据量）(GB)` = IFNULL(`5G上行流量（上行PDCP PDU数据量）(GB)`,0),
`5G下行流量（下行PDCP成功发送数据量）(GB)` = IFNULL(`5G下行流量（下行PDCP成功发送数据量）(GB)`,0),
`小区平均激活UE数` = IFNULL(`小区平均激活UE数`,0),
`RRC连接最大连接用户数` = IFNULL(`RRC连接最大连接用户数`,0),
`RRC连接平均连接用户数` = IFNULL(`RRC连接平均连接用户数`,0),
`小区最大激活UE数` = IFNULL(`小区最大激活UE数`,0),
`上行PRB平均利用率` = IFNULL(`上行PRB平均利用率`,0),
`下行PRB平均利用率` = IFNULL(`下行PRB平均利用率`,0),
`PDCCH信道CCE占用率（动态）(%)` = IFNULL(`PDCCH信道CCE占用率（动态）(%)`,0),
`小区下行RLC SDU字节数(MByte)` = IFNULL(`小区下行RLC SDU字节数(MByte)`,0),
`小区上行RLC SDU字节数(MByte)` = IFNULL(`小区上行RLC SDU字节数(MByte)`,0),
`单Flow流量(MB)` = IFNULL(`单Flow流量(MB)`,0);


# 处理日间（广电、移动）流量数据

ALTER TABLE `5G_结果表`
ADD COLUMN `_gNBId` varchar(50),
ADD COLUMN `_cellId` varchar(50),
ADD COLUMN `移动流量_GB` double NOT NULL DEFAULT 0 AFTER `CU小区配置名称`,
ADD COLUMN `广电流量_GB` double NOT NULL DEFAULT 0 AFTER `移动流量_GB`;

UPDATE `5G_结果表` SET
  `_gNBId` = SUBSTRING_INDEX(SUBSTRING_INDEX(`NCGI`, '-', 3), '-', -1),
  `_cellId` = SUBSTRING_INDEX(`NCGI`, '-', -1);

ALTER TABLE `5G_结果表` ADD INDEX `_rj`(`_gNBId`, `_cellId`);


CREATE TABLE `_rj_yd` ( `gNBId` varchar(50), `cellId` varchar(50), `上下行总流量_GB` double, INDEX (`gNBId`, `cellId`)) AS
	SELECT `gNBId`, `cellId`, AVG(`上下行总流量_GB`) AS `上下行总流量_GB` FROM (
		SELECT `gNBId`, `cellId`, `上下行总流量_GB` FROM `2_6grjyd`
		UNION ALL
		SELECT `gNBId`, `cellId`, `上下行总流量_GB` FROM `700mrjyd`
	) AS t
		GROUP BY `gNBId`, `cellId`;

CREATE TABLE `_rj_gd` (
    `gNBId` varchar(50), `cellId` varchar(50), `上下行总流量_GB` double,
    INDEX (`gNBId`, `cellId`)
) AS
SELECT `gNBId`, `cellId`, AVG(`上下行总流量_GB`) AS `上下行总流量_GB`
FROM (
    SELECT `gNBId`, `cellId`, `上下行总流量_GB` FROM `2_6grjgd`
    UNION ALL
    SELECT `gNBId`, `cellId`, `上下行总流量_GB` FROM `700mrjgd`
) AS t
GROUP BY `gNBId`, `cellId`;

CREATE TABLE `rj` (
    `gNBId` varchar(50), `cellId` varchar(50),
    `移动流量_GB` double NOT NULL DEFAULT 0,
    `广电流量_GB` double NOT NULL DEFAULT 0,
    INDEX (`gNBId`, `cellId`)
) AS
SELECT
    `_rj_yd`.`gNBId`, `_rj_yd`.`cellId`,
    IFNULL(`_rj_yd`.`上下行总流量_GB`, 0) AS `移动流量_GB`,
    IFNULL(`_rj_gd`.`上下行总流量_GB`, 0) AS `广电流量_GB`
FROM `_rj_yd`
LEFT JOIN `_rj_gd` ON `_rj_yd`.`gNBId` = `_rj_gd`.`gNBId` AND `_rj_yd`.`cellId` = `_rj_gd`.`cellId`
UNION ALL
SELECT
    `_rj_gd`.`gNBId`, `_rj_gd`.`cellId`,
    0, `_rj_gd`.`上下行总流量_GB`
FROM `_rj_gd`
LEFT JOIN `_rj_yd` ON `_rj_gd`.`gNBId` = `_rj_yd`.`gNBId` AND `_rj_gd`.`cellId` = `_rj_yd`.`cellId`
WHERE `_rj_yd`.`gNBId` IS NULL;

UPDATE `5G_结果表`
LEFT JOIN `rj`
  ON `5G_结果表`.`_gNBId` = `rj`.`gNBId`
 AND `5G_结果表`.`_cellId` = `rj`.`cellId`
SET
  `5G_结果表`.`移动流量_GB` = IFNULL(`rj`.`移动流量_GB`, 0),
  `5G_结果表`.`广电流量_GB` = IFNULL(`rj`.`广电流量_GB`, 0);

ALTER TABLE `5G_结果表` DROP INDEX `_rj`, DROP COLUMN `_gNBId`, DROP COLUMN `_cellId`;

DROP TABLE `_rj_yd`;
DROP TABLE `_rj_gd`;
DROP TABLE `rj`;


# ============================================================
# 从 sector / cellinfo 富集小区信息
# ============================================================


ALTER TABLE `4G_结果表`
  ADD COLUMN `扇区` varchar(200) AFTER `小区名称`,
  ADD COLUMN `物理站` varchar(200) AFTER `扇区`,
  ADD COLUMN `站型` varchar(50) AFTER `物理站`,
  ADD COLUMN `频段` varchar(50) AFTER `站型`,
  ADD COLUMN `频点` varchar(50) AFTER `频段`,
  ADD COLUMN `带宽` varchar(20) AFTER `频点`,
  ADD COLUMN `制式` varchar(50) AFTER `带宽`,
  ADD COLUMN `功率` varchar(100) AFTER `制式`;

ALTER TABLE `5G_结果表`
  ADD COLUMN `基站名称` varchar(200) AFTER `NCGI`,
  ADD COLUMN `扇区` varchar(200) AFTER `基站名称`,
  ADD COLUMN `物理站` varchar(200) AFTER `扇区`,
  ADD COLUMN `站型` varchar(50) AFTER `物理站`,
  ADD COLUMN `频段` varchar(50) AFTER `站型`,
  ADD COLUMN `频点` varchar(50) AFTER `频段`,
  ADD COLUMN `带宽` varchar(20) AFTER `频点`,
  ADD COLUMN `制式` varchar(50) AFTER `带宽`,
  ADD COLUMN `功率` varchar(100) AFTER `制式`;



UPDATE `4G_结果表` `t`
LEFT JOIN `sector` `s` ON `t`.`CGI` = `s`.`CGI`
SET
  `t`.`扇区` = `s`.`扇区`,
  `t`.`物理站` = `s`.`物理站`,
  `t`.`站型` = `s`.`站型`,
  `t`.`频段` = `s`.`频段`;


UPDATE `4G_结果表` `t`
LEFT JOIN `cellinfo` `c` ON `t`.`CGI` = `c`.`CGI`
SET
  `t`.`频点` = `c`.`频点`,
  `t`.`带宽` = `c`.`带宽`,
  `t`.`制式` = `c`.`制式`,
  `t`.`功率` = `c`.`功率`;
	

UPDATE `5G_结果表` `t`
LEFT JOIN `sector` `s` ON `t`.`NCGI` = `s`.`CGI`
SET
  `t`.`扇区` = `s`.`扇区`,
  `t`.`物理站` = `s`.`物理站`,
  `t`.`站型` = `s`.`站型`,
  `t`.`频段` = `s`.`频段`;


UPDATE `5G_结果表` `t`
LEFT JOIN `cellinfo` `c` ON `t`.`NCGI` = `c`.`CGI`
SET
  `t`.`基站名称` = `c`.`基站名称`,
  `t`.`频点` = `c`.`频点`,
  `t`.`带宽` = `c`.`带宽`,
  `t`.`制式` = `c`.`制式`,
  `t`.`功率` = `c`.`功率`;







# ============================================================
# 高负荷小区判定（互斥，利用率优先）
#   利用率达标 → 用户数达标 = 高负荷；否则 = 利用率预警
#   利用率不达标 → 流量达标 = 高流量预警；否则 = 正常
# 是否高负荷小区：仅「高负荷」= 是；两类预警与正常 = 否（预警 ≠ 高负荷）。
# 门限区分 制式 / 带宽（直接用富集写入结果表的 `制式` `带宽` 列，无需再 JOIN）；不分站型；3DMM 归 TDD(0.5)。
# 阈值与命中量见 docs/高负荷小区判定_调研记录.md（§8）。
# ============================================================

ALTER TABLE `4G_结果表` ADD COLUMN `是否高负荷小区` VARCHAR(100);
ALTER TABLE `4G_结果表` ADD COLUMN `高负荷问题` VARCHAR(50);

ALTER TABLE `4G_结果表` ADD COLUMN `优化建议` TEXT;

ALTER TABLE `5G_结果表` ADD COLUMN `是否高负荷小区` VARCHAR(100);
ALTER TABLE `5G_结果表` ADD COLUMN `高负荷问题` VARCHAR(50);
ALTER TABLE `5G_结果表` ADD COLUMN `优化建议` TEXT;

# 4G：利用率 FDD≥0.7 / 其余(TDD、3DMM)≥0.5；用户数(YY-RRC)按带宽 20M=30/15M=25/10M=20/5M=12；
#     高流量(下行流量GB)按带宽 20M=10/15M=7.5/10M=5/5M=2.5。
UPDATE `4G_结果表` SET `高负荷问题` = CASE
  WHEN (`下行PDSCH利用率` >= CASE WHEN `制式` = 'FDD' THEN 0.7 ELSE 0.5 END
        OR `上行PUSCH利用率` >= CASE WHEN `制式` = 'FDD' THEN 0.7 ELSE 0.5 END)
    THEN CASE
      WHEN `YY-RRC连接建立最大用户数` >= CASE `带宽` WHEN '15M' THEN 25 WHEN '10M' THEN 20 WHEN '5M' THEN 12 ELSE 30 END
        THEN '高负荷'
      ELSE '利用率预警'
    END
  WHEN `下行流量（GB）` >= CASE `带宽` WHEN '15M' THEN 7.5 WHEN '10M' THEN 5 WHEN '5M' THEN 2.5 ELSE 10 END
    THEN '高流量预警'
  ELSE NULL
END;

UPDATE `4G_结果表` SET `是否高负荷小区` = IF(`高负荷问题` = '高负荷', '是', '否');

# 5G：利用率 上行PRB≥0.5 或 下行PRB≥0.7；用户数(RRC平均)按带宽 100M/80M=200/60M=120/30M=90；
#     高流量(上行GB 或 下行GB)按带宽 100M=5/70、60M=3/43、30M=8/30。
UPDATE `5G_结果表` SET `高负荷问题` = CASE
  WHEN (`上行PRB平均利用率` >= 0.5 OR `下行PRB平均利用率` >= 0.7)
    THEN CASE
      WHEN `RRC连接平均连接用户数` >= CASE `带宽` WHEN '60M' THEN 120 WHEN '30M' THEN 90 ELSE 200 END
        THEN '高负荷'
      ELSE '利用率预警'
    END
  WHEN (`5G上行流量（上行PDCP PDU数据量）(GB)` >= CASE `带宽` WHEN '60M' THEN 3 WHEN '30M' THEN 8 ELSE 5 END
        OR `5G下行流量（下行PDCP成功发送数据量）(GB)` >= CASE `带宽` WHEN '60M' THEN 43 WHEN '30M' THEN 30 ELSE 70 END)
    THEN '高流量预警'
  ELSE NULL
END;

UPDATE `5G_结果表` SET `是否高负荷小区` = IF(`高负荷问题` = '高负荷', '是', '否');


# ============================================================
# 优化建议（仅对 是否高负荷小区='是' 的高负荷小区生成）
#   分析范围：同扇区(`扇区`) + 同 PLMN（CGI/NCGI 前两段，如 460-00 移动 / 460-15 广电；
#   不同运营商不可均衡、不视为同扇区）。
#   在该范围内取“最空闲”小区（`高负荷问题` IS NULL，按 下行利用率→日均流量 升序取一）：
#     有空闲小区 → 模板1：给出本小区与空闲小区的指标，建议负载均衡；
#     无空闲小区（同扇区皆 高负荷/利用率预警/高流量预警）→ 模板2：建议人工分析周边小区。
#   `_idle_4g`/`_idle_5g` 为每个(扇区,PLMN)的最空闲小区缓存表，用后即删。
# ============================================================

DROP TABLE IF EXISTS `_idle_4g`;
CREATE TABLE `_idle_4g` (
  `扇区` varchar(200), `plmn` varchar(20),
  `cgi` varchar(120), `name` varchar(200), `ul` double, `dl` double, `flow` double, `pwr` varchar(120),
  INDEX (`扇区`, `plmn`)
) AS
SELECT `扇区`, `plmn`, `CGI` AS `cgi`, `小区名称` AS `name`, `上行PUSCH利用率` AS `ul`, `下行PDSCH利用率` AS `dl`, `日均流量（GB）` AS `flow`, `功率` AS `pwr`
FROM (
  SELECT `扇区`, SUBSTRING_INDEX(`CGI`, '-', 2) AS `plmn`, `CGI`, `小区名称`,
         `上行PUSCH利用率`, `下行PDSCH利用率`, `日均流量（GB）`, `功率`,
         ROW_NUMBER() OVER (PARTITION BY `扇区`, SUBSTRING_INDEX(`CGI`, '-', 2)
                            ORDER BY `下行PDSCH利用率` ASC, `日均流量（GB）` ASC) AS `rn`
  FROM `4G_结果表`
  WHERE `高负荷问题` IS NULL AND `扇区` IS NOT NULL AND `扇区` <> ''
) `t`
WHERE `rn` = 1;

UPDATE `4G_结果表` `t`
LEFT JOIN `_idle_4g` `i` ON `i`.`扇区` = `t`.`扇区` AND `i`.`plmn` = SUBSTRING_INDEX(`t`.`CGI`, '-', 2)
SET `t`.`优化建议` = CONCAT(
  '高负荷小区', `t`.`CGI`, '（', IFNULL(`t`.`小区名称`, '-'), '）',
  '：上行利用率:', ROUND(`t`.`上行PUSCH利用率` * 100, 1), '%',
  ' 下行利用率:', ROUND(`t`.`下行PDSCH利用率` * 100, 1), '%',
  ' 日均流量:', ROUND(`t`.`日均流量（GB）`, 2), 'GB',
  ' 用户数:', ROUND(`t`.`YY-RRC连接建立最大用户数`, 0),
  ' 当前小区功率:', IFNULL(`t`.`功率`, '-'), '。',
  IF(`i`.`cgi` IS NOT NULL,
    CONCAT('存在同覆盖空闲小区:', `i`.`cgi`, '（', IFNULL(`i`.`name`, '-'), '）',
           '：下行利用率:', ROUND(`i`.`dl` * 100, 1), '%',
           ' 上行利用率:', ROUND(`i`.`ul` * 100, 1), '%',
           ' 日均流量:', ROUND(`i`.`flow`, 2), 'GB',
           ' 小区功率:', IFNULL(`i`.`pwr`, '-'),
           '，建议将本小区部分负荷均衡至该空闲小区（负载均衡/邻区参数优化）。'),
    '经分析，本站同扇区（同PLMN）小区均为高负荷或预警状态、无空闲可均衡小区，建议人工分析周边小区是否可均衡。'
  )
)
WHERE `t`.`是否高负荷小区` = '是';

DROP TABLE IF EXISTS `_idle_4g`;


DROP TABLE IF EXISTS `_idle_5g`;
CREATE TABLE `_idle_5g` (
  `扇区` varchar(200), `plmn` varchar(20),
  `cgi` varchar(120), `name` varchar(200), `ul` double, `dl` double, `flow` double, `pwr` varchar(120),
  INDEX (`扇区`, `plmn`)
) AS
SELECT `扇区`, `plmn`, `NCGI` AS `cgi`, `CU小区配置名称` AS `name`, `上行PRB平均利用率` AS `ul`, `下行PRB平均利用率` AS `dl`, `日均流量（GB）` AS `flow`, `功率` AS `pwr`
FROM (
  SELECT `扇区`, SUBSTRING_INDEX(`NCGI`, '-', 2) AS `plmn`, `NCGI`, `CU小区配置名称`,
         `上行PRB平均利用率`, `下行PRB平均利用率`, `日均流量（GB）`, `功率`,
         ROW_NUMBER() OVER (PARTITION BY `扇区`, SUBSTRING_INDEX(`NCGI`, '-', 2)
                            ORDER BY `下行PRB平均利用率` ASC, `日均流量（GB）` ASC) AS `rn`
  FROM `5G_结果表`
  WHERE `高负荷问题` IS NULL AND `扇区` IS NOT NULL AND `扇区` <> ''
) `t`
WHERE `rn` = 1;

UPDATE `5G_结果表` `t`
LEFT JOIN `_idle_5g` `i` ON `i`.`扇区` = `t`.`扇区` AND `i`.`plmn` = SUBSTRING_INDEX(`t`.`NCGI`, '-', 2)
SET `t`.`优化建议` = CONCAT(
  '高负荷小区', `t`.`NCGI`, '（', IFNULL(`t`.`CU小区配置名称`, '-'), '）',
  '：上行PRB利用率:', ROUND(`t`.`上行PRB平均利用率` * 100, 1), '%',
  ' 下行PRB利用率:', ROUND(`t`.`下行PRB平均利用率` * 100, 1), '%',
  ' 日均流量:', ROUND(`t`.`日均流量（GB）`, 2), 'GB',
  ' 用户数:', ROUND(`t`.`RRC连接平均连接用户数`, 0),
  ' 当前小区功率:', IFNULL(`t`.`功率`, '-'), '。',
  IF(`i`.`cgi` IS NOT NULL,
    CONCAT('存在同覆盖空闲小区:', `i`.`cgi`, '（', IFNULL(`i`.`name`, '-'), '）',
           '：下行PRB利用率:', ROUND(`i`.`dl` * 100, 1), '%',
           ' 上行PRB利用率:', ROUND(`i`.`ul` * 100, 1), '%',
           ' 日均流量:', ROUND(`i`.`flow`, 2), 'GB',
           ' 小区功率:', IFNULL(`i`.`pwr`, '-'),
           '，建议将本小区部分负荷均衡至该空闲小区（负载均衡/邻区参数优化）。'),
    '经分析，本站同扇区（同PLMN）小区均为高负荷或预警状态、无空闲可均衡小区，建议人工分析周边小区是否可均衡。'
  )
)
WHERE `t`.`是否高负荷小区` = '是';

DROP TABLE IF EXISTS `_idle_5g`;

