-- MySQL initialization for CapacityReport.
-- This file runs only when the MySQL data directory is empty.
-- 建两个库：CapacityReport（主仓库/容量结果）与 celldata（CellData 小区/扇区）。
-- 仅建库；具体表由应用前置检查（app/db_init.py + db_init/）按需创建。

CREATE DATABASE IF NOT EXISTS CapacityReport
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS celldata
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

SELECT 'CapacityReport & celldata databases initialized with utf8mb4 charset' AS status;
