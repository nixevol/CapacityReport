UPDATE cellinfo SET `带宽` = IF(`带宽` IS NULL OR `带宽` = '', '0M', CONCAT(REPLACE(UPPER(`带宽`),'M',''), 'M'));

# 后续实现通过cellinfo表处理为扇区表，支撑扇区容量分析