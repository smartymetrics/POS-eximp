-- hr_phase7_profile_enrichment.sql
-- Enriching staff profiles with personal metadata, bio, and leave quota management

DO $$ 
BEGIN
    -- 1. Add dob and bio if they don't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='staff_profiles' AND column_name='dob') THEN
        ALTER TABLE staff_profiles ADD COLUMN dob DATE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='staff_profiles' AND column_name='bio') THEN
        ALTER TABLE staff_profiles ADD COLUMN bio TEXT;
    END IF;

    -- 2. Add Demographic info
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='staff_profiles' AND column_name='gender') THEN
        ALTER TABLE staff_profiles ADD COLUMN gender VARCHAR(20);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='staff_profiles' AND column_name='marital_status') THEN
        ALTER TABLE staff_profiles ADD COLUMN marital_status VARCHAR(50);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='staff_profiles' AND column_name='nationality') THEN
        ALTER TABLE staff_profiles ADD COLUMN nationality VARCHAR(100);
    END IF;

    -- 3. Add Leave Management
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='staff_profiles' AND column_name='leave_quota') THEN
        ALTER TABLE staff_profiles ADD COLUMN leave_quota INT DEFAULT 20;
    END IF;

    -- 4. Add Financial info
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='staff_profiles' AND column_name='bank_name') THEN
        ALTER TABLE staff_profiles ADD COLUMN bank_name VARCHAR(255);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='staff_profiles' AND column_name='account_number') THEN
        ALTER TABLE staff_profiles ADD COLUMN account_number VARCHAR(100);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='staff_profiles' AND column_name='account_name') THEN
        ALTER TABLE staff_profiles ADD COLUMN account_name VARCHAR(255);
    END IF;

END $$;
