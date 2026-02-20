-- 選出（nomination）にひとこと推薦コメントを追加
ALTER TABLE votes ADD COLUMN IF NOT EXISTS comment TEXT;
