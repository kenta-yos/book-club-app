-- 本の論理削除用カラムを追加
ALTER TABLE books ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
