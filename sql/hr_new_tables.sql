-- ════════════════════════════════════════════════════════════════════════════
-- HR SYSTEM — NEW TABLES MIGRATION
-- Run this in Supabase SQL Editor BEFORE deploying the new backend routes
-- ════════════════════════════════════════════════════════════════════════════

-- Timesheets
CREATE TABLE IF NOT EXISTS timesheets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  staff_id UUID REFERENCES admins(id),
  week_start DATE NOT NULL,
  mon_hrs NUMERIC DEFAULT 0,
  tue_hrs NUMERIC DEFAULT 0,
  wed_hrs NUMERIC DEFAULT 0,
  thu_hrs NUMERIC DEFAULT 0,
  fri_hrs NUMERIC DEFAULT 0,
  total_hrs NUMERIC DEFAULT 0,
  notes TEXT,
  status TEXT DEFAULT 'pending', -- pending | approved | rejected
  reviewer_id UUID REFERENCES admins(id),
  reviewer_notes TEXT,
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Shifts
CREATE TABLE IF NOT EXISTS shifts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  staff_id UUID REFERENCES admins(id),
  shift_date DATE NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  shift_type TEXT DEFAULT 'Regular', -- Regular | Overtime | Remote
  notes TEXT,
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Public Holidays
CREATE TABLE IF NOT EXISTS public_holidays (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  holiday_date DATE NOT NULL,
  is_recurring BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Leave Policies
CREATE TABLE IF NOT EXISTS leave_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  leave_type TEXT NOT NULL UNIQUE,
  days_per_year INTEGER NOT NULL DEFAULT 20,
  carry_over BOOLEAN DEFAULT FALSE,
  requires_proof BOOLEAN DEFAULT FALSE,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance Improvement Plans
CREATE TABLE IF NOT EXISTS performance_improvement_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  staff_id UUID REFERENCES admins(id),
  reason TEXT NOT NULL,
  goals TEXT,
  start_date DATE NOT NULL,
  review_date DATE,
  notes TEXT,
  status TEXT DEFAULT 'active', -- active | completed | closed
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trainings
CREATE TABLE IF NOT EXISTS trainings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  training_type TEXT DEFAULT 'Internal', -- Internal | External | Compliance
  description TEXT,
  start_date DATE NOT NULL,
  end_date DATE,
  trainer TEXT,
  max_participants INTEGER,
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS training_enrollments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  training_id UUID REFERENCES trainings(id) ON DELETE CASCADE,
  staff_id UUID REFERENCES admins(id),
  enrolled_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  UNIQUE(training_id, staff_id)
);

-- Onboarding Checklists
CREATE TABLE IF NOT EXISTS onboarding_checklists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  staff_id UUID REFERENCES admins(id),
  item TEXT NOT NULL,
  completed BOOLEAN DEFAULT FALSE,
  completed_at TIMESTAMPTZ,
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Probation Reviews
CREATE TABLE IF NOT EXISTS probation_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  staff_id UUID REFERENCES admins(id),
  review_date DATE NOT NULL,
  outcome TEXT NOT NULL, -- Pass | Extended | Failed
  notes TEXT,
  reviewed_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Compensation Bands
CREATE TABLE IF NOT EXISTS compensation_bands (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role_title TEXT NOT NULL,
  department TEXT,
  min_salary NUMERIC NOT NULL,
  max_salary NUMERIC NOT NULL,
  currency TEXT DEFAULT 'NGN',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bonuses
CREATE TABLE IF NOT EXISTS bonuses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  staff_id UUID REFERENCES admins(id),
  bonus_type TEXT NOT NULL, -- Performance | Annual | Spot | Commission
  amount NUMERIC NOT NULL,
  period TEXT, -- YYYY-MM
  notes TEXT,
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Announcements
CREATE TABLE IF NOT EXISTS announcements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  priority TEXT DEFAULT 'Normal', -- Normal | Urgent | Info
  target_department TEXT,
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Recognition (Kudos Wall)
CREATE TABLE IF NOT EXISTS recognition (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipient_id UUID REFERENCES admins(id),
  giver_id UUID REFERENCES admins(id),
  message TEXT NOT NULL,
  badge_type TEXT DEFAULT 'Kudos', -- Kudos | Star | Excellence | Teamwork
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Surveys
CREATE TABLE IF NOT EXISTS surveys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  questions JSONB NOT NULL DEFAULT '[]',
  is_anonymous BOOLEAN DEFAULT TRUE,
  is_active BOOLEAN DEFAULT TRUE,
  created_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS survey_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  survey_id UUID REFERENCES surveys(id) ON DELETE CASCADE,
  respondent_id UUID REFERENCES admins(id),
  answers JSONB NOT NULL DEFAULT '{}',
  is_anonymous BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Work Permits
CREATE TABLE IF NOT EXISTS work_permits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  staff_id UUID REFERENCES admins(id),
  permit_type TEXT NOT NULL,
  permit_number TEXT NOT NULL,
  issue_date DATE NOT NULL,
  expiry_date DATE NOT NULL,
  issuing_authority TEXT,
  status TEXT DEFAULT 'Active', -- Active | Expired | Cancelled
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HR Letters
CREATE TABLE IF NOT EXISTS hr_letters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  staff_id UUID REFERENCES admins(id),
  letter_type TEXT NOT NULL,
  content TEXT NOT NULL,
  date_issued DATE NOT NULL,
  issued_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Grievances
CREATE TABLE IF NOT EXISTS grievances (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject TEXT NOT NULL,
  description TEXT NOT NULL,
  is_anonymous BOOLEAN DEFAULT TRUE,
  filed_by UUID REFERENCES admins(id),
  against_staff_id UUID REFERENCES admins(id),
  status TEXT DEFAULT 'open', -- open | under_review | resolved | dismissed
  resolved_by UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id UUID REFERENCES admins(id),
  action TEXT NOT NULL,
  entity_type TEXT,
  entity_id TEXT,
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Departments (standalone table)
CREATE TABLE IF NOT EXISTS departments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  head_id UUID REFERENCES admins(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add status column to disciplinary_records if missing
ALTER TABLE disciplinary_records ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'open';
ALTER TABLE disciplinary_records ADD COLUMN IF NOT EXISTS resolution_notes TEXT;
ALTER TABLE disciplinary_records ADD COLUMN IF NOT EXISTS resolved_by UUID REFERENCES admins(id);
ALTER TABLE disciplinary_records ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;
ALTER TABLE disciplinary_records ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

-- Add status + completion columns to staff_tasks if missing
ALTER TABLE staff_tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE staff_tasks ADD COLUMN IF NOT EXISTS completion_notes TEXT;
ALTER TABLE staff_tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

-- ════════════════════════════════════════════════════════════════════════════
-- Seed default leave policies
INSERT INTO leave_policies (leave_type, days_per_year, carry_over, requires_proof, description)
VALUES 
  ('Annual Leave', 20, FALSE, FALSE, 'Standard annual leave entitlement'),
  ('Sick Leave', 10, FALSE, TRUE, 'Paid sick leave. Doctor''s note required for 2+ days.'),
  ('Maternity Leave', 90, FALSE, TRUE, '90 days fully paid maternity leave'),
  ('Paternity Leave', 5, FALSE, FALSE, '5 days paternity leave on birth of child'),
  ('Study Leave', 5, FALSE, TRUE, 'Approved study/examination leave'),
  ('Compassionate Leave', 3, FALSE, FALSE, 'Bereavement and family emergency leave')
ON CONFLICT (leave_type) DO NOTHING;

-- Seed Nigerian public holidays 2026
INSERT INTO public_holidays (name, holiday_date, is_recurring) VALUES
  ('New Year''s Day', '2026-01-01', TRUE),
  ('Good Friday', '2026-04-03', FALSE),
  ('Easter Monday', '2026-04-06', FALSE),
  ('Workers'' Day', '2026-05-01', TRUE),
  ('Democracy Day', '2026-06-12', TRUE),
  ('Eid el-Fitr', '2026-03-31', FALSE),
  ('Eid el-Adha', '2026-06-07', FALSE),
  ('Independence Day', '2026-10-01', TRUE),
  ('Christmas Day', '2026-12-25', TRUE),
  ('Boxing Day', '2026-12-26', TRUE)
ON CONFLICT DO NOTHING;