-- Add Missing Columns to Staff Profiles for HR Archival (PRD 8.1)
ALTER TABLE public.staff_profiles 
  ADD COLUMN IF NOT EXISTS exit_date DATE,
  ADD COLUMN IF NOT EXISTS exit_reason TEXT;

-- Attendance Records (For Clock In/Out)
-- Ensure this table exists and has necessary columns
CREATE TABLE IF NOT EXISTS public.attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID REFERENCES public.admins(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    status TEXT NOT NULL, -- 'Present', 'Late', 'Absent'
    check_in_time TIMESTAMP WITH TIME ZONE,
    check_out_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ensure table has check_in and check_out tracking if we are using an existing table
ALTER TABLE public.attendance_records
  ADD COLUMN IF NOT EXISTS check_in_time TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS check_out_time TIMESTAMP WITH TIME ZONE;
