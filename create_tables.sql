-- 深掘り機能（Deep Dive）のテーブル作成SQL
-- このSQLを直接MySQLで実行することもできます

-- deep_dive_progress テーブル
CREATE TABLE IF NOT EXISTS deep_dive_progress (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    axis_code VARCHAR(64) NOT NULL,
    card_id VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'not_started',
    summary TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_card (user_id, card_id),
    INDEX idx_user_axis (user_id, axis_code),
    INDEX idx_card_id (card_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- deep_dive_chat_logs テーブル
CREATE TABLE IF NOT EXISTS deep_dive_chat_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    card_id VARCHAR(128) NOT NULL,
    role VARCHAR(16) NOT NULL COMMENT 'user or assistant',
    message TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_card (user_id, card_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



