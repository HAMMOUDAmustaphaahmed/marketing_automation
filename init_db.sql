-- ============================================================
-- Marketing Automation Platform - MySQL Database Init Script
-- Run this script in MySQL to create the database
-- ============================================================

CREATE DATABASE IF NOT EXISTS marketing_automation
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE marketing_automation;

-- The tables are auto-created by SQLAlchemy (db.create_all())
-- when you first run the Flask app.
-- This script just creates the database and a user.

-- Optional: Create a dedicated MySQL user
-- CREATE USER 'ma_user'@'localhost' IDENTIFIED BY 'your_password';
-- GRANT ALL PRIVILEGES ON marketing_automation.* TO 'ma_user'@'localhost';
-- FLUSH PRIVILEGES;

SELECT 'Database marketing_automation created successfully!' AS status;
