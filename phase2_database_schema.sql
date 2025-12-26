-- Family Chores App - Phase 2 Database Schema
-- Adds recurring chores, due dates, parental review, and reporting enhancements

USE family_chores;

-- Add columns to chores table for recurring functionality
ALTER TABLE chores
ADD COLUMN is_recurring BOOLEAN DEFAULT FALSE,
ADD COLUMN recurrence_type ENUM('daily', 'weekly', 'monthly', 'weekdays', 'specific_days') DEFAULT NULL,
ADD COLUMN recurrence_days VARCHAR(20) DEFAULT NULL COMMENT 'Comma-separated days for specific_days (M,T,W,TH,F,SA,SU)';

-- Add due_date to assignments
ALTER TABLE assignments
ADD COLUMN due_date DATE DEFAULT NULL,
ADD COLUMN notes TEXT DEFAULT NULL;

-- Add parental review table
CREATE TABLE IF NOT EXISTS parental_reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    completion_id INT NOT NULL,
    reviewed_by_person_id INT NOT NULL,
    reviewed_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved BOOLEAN DEFAULT TRUE,
    review_notes TEXT,
    FOREIGN KEY (completion_id) REFERENCES completions(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by_person_id) REFERENCES people(id) ON DELETE CASCADE
);

-- Add indexes for Phase 2 performance
CREATE INDEX idx_chores_recurring ON chores(is_recurring);
CREATE INDEX idx_assignments_due_date ON assignments(due_date);
CREATE INDEX idx_parental_reviews_completion ON parental_reviews(completion_id);

-- Create a view for reporting - daily completion summary
CREATE OR REPLACE VIEW daily_completion_summary AS
SELECT 
    a.assigned_date,
    COUNT(DISTINCT a.id) as total_assigned,
    COUNT(DISTINCT c.id) as total_completed,
    ROUND(COUNT(DISTINCT c.id) * 100.0 / COUNT(DISTINCT a.id), 2) as completion_rate,
    SUM(ch.estimated_time) as estimated_minutes,
    SUM(COALESCE(c.actual_minutes, 0)) as actual_minutes
FROM assignments a
JOIN chores ch ON a.chore_id = ch.id
LEFT JOIN completions c ON a.id = c.assignment_id
GROUP BY a.assigned_date;

-- Create a view for individual performance
CREATE OR REPLACE VIEW individual_performance AS
SELECT 
    p.id as person_id,
    p.name as person_name,
    a.assigned_date,
    COUNT(DISTINCT a.id) as assigned_count,
    COUNT(DISTINCT c.id) as completed_count,
    ROUND(COUNT(DISTINCT c.id) * 100.0 / COUNT(DISTINCT a.id), 2) as completion_rate,
    SUM(ch.estimated_time) as estimated_minutes,
    SUM(COALESCE(c.actual_minutes, 0)) as actual_minutes
FROM people p
JOIN assignments a ON p.id = a.person_id
JOIN chores ch ON a.chore_id = ch.id
LEFT JOIN completions c ON a.id = c.assignment_id
GROUP BY p.id, p.name, a.assigned_date;

-- Procedure to generate assignments for recurring chores
DELIMITER //

CREATE PROCEDURE generate_recurring_assignments(IN target_date DATE)
BEGIN
    DECLARE day_of_week VARCHAR(2);
    DECLARE day_name VARCHAR(10);
    
    -- Get day of week (M, T, W, TH, F, SA, SU)
    SET day_of_week = CASE DAYOFWEEK(target_date)
        WHEN 1 THEN 'SU'
        WHEN 2 THEN 'M'
        WHEN 3 THEN 'T'
        WHEN 4 THEN 'W'
        WHEN 5 THEN 'TH'
        WHEN 6 THEN 'F'
        WHEN 7 THEN 'SA'
    END;
    
    -- Daily recurring chores
    INSERT IGNORE INTO assignments (chore_id, person_id, assigned_date, due_date)
    SELECT 
        rc.chore_id,
        rc.person_id,
        target_date,
        target_date
    FROM (
        SELECT c.id as chore_id, 
               (SELECT id FROM people ORDER BY RAND() LIMIT 1) as person_id
        FROM chores c
        WHERE c.is_recurring = TRUE 
        AND c.recurrence_type = 'daily'
    ) rc;
    
    -- Weekly recurring chores (only on specific day, e.g., Monday)
    -- This is a simple implementation; you may want to customize per chore
    IF DAYOFWEEK(target_date) = 2 THEN  -- Monday
        INSERT IGNORE INTO assignments (chore_id, person_id, assigned_date, due_date)
        SELECT 
            c.id,
            (SELECT id FROM people ORDER BY RAND() LIMIT 1),
            target_date,
            target_date
        FROM chores c
        WHERE c.is_recurring = TRUE 
        AND c.recurrence_type = 'weekly';
    END IF;
    
    -- Weekdays only (Monday-Friday)
    IF DAYOFWEEK(target_date) BETWEEN 2 AND 6 THEN
        INSERT IGNORE INTO assignments (chore_id, person_id, assigned_date, due_date)
        SELECT 
            c.id,
            (SELECT id FROM people ORDER BY RAND() LIMIT 1),
            target_date,
            target_date
        FROM chores c
        WHERE c.is_recurring = TRUE 
        AND c.recurrence_type = 'weekdays';
    END IF;
    
    -- Specific days of week
    INSERT IGNORE INTO assignments (chore_id, person_id, assigned_date, due_date)
    SELECT 
        c.id,
        (SELECT id FROM people ORDER BY RAND() LIMIT 1),
        target_date,
        target_date
    FROM chores c
    WHERE c.is_recurring = TRUE 
    AND c.recurrence_type = 'specific_days'
    AND FIND_IN_SET(day_of_week, c.recurrence_days) > 0;
    
END //

DELIMITER ;

-- Sample update to mark some chores as recurring (you can modify these)
-- Update daily chores to be recurring
UPDATE chores 
SET is_recurring = TRUE, recurrence_type = 'daily'
WHERE frequency = 'Daily';

-- Update weekly chores to be recurring on specific days
UPDATE chores 
SET is_recurring = TRUE, recurrence_type = 'weekly'
WHERE frequency = 'Weekly';

-- Update summer-weekly chores
UPDATE chores 
SET is_recurring = TRUE, recurrence_type = 'weekly'
WHERE frequency = 'Summer-weekly';
