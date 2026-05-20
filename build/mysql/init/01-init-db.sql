-- MySQL initialization for CapacityReport.
-- This file runs only when the MySQL data directory is empty.

CREATE DATABASE IF NOT EXISTS CapacityReport
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE CapacityReport;

SELECT 'CapacityReport database initialized with utf8mb4 charset' AS status;
