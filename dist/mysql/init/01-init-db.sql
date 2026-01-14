-- MySQL 初始化脚本 - 确保数据库以正确的字符集创建
-- 此脚本仅在首次初始化时执行（数据目录为空时）

-- 如果数据库不存在，则创建（使用 utf8mb4 字符集）
CREATE DATABASE IF NOT EXISTS CapacityReport
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- 切换到数据库
USE CapacityReport;

-- 输出确认信息
SELECT 'CapacityReport database initialized with utf8mb4 charset' AS status;
