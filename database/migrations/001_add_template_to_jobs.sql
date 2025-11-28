-- Add template_name column to jobs table
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS template_name VARCHAR(255);

-- Make template_name required for new jobs (existing jobs will have NULL)
-- We'll handle backward compatibility in the code
