-- Add image column to messages table
-- This migration adds an image URL column to store generated analysis images

ALTER TABLE messages ADD COLUMN image TEXT NULL COMMENT '이미지 URL 저장';

-- Update existing records to have NULL image values (already default)
-- No additional update needed as new column defaults to NULL
