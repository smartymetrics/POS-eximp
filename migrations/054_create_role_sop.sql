-- 054_create_role_sop.sql
-- "My Role & SOP" — per-department minimum-requirement briefs sourced from the
-- Eximp & Cloves Standard Operating Procedure Manual. One row per canonical
-- department (see role_sop_seed.py for the seed list); HR can edit content
-- in place without a redeploy.

CREATE TABLE IF NOT EXISTS role_sop (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department TEXT NOT NULL UNIQUE,       -- canonical department name, matched via alias map
    aliases JSONB DEFAULT '[]',            -- array of free-text department strings (as stored on admins.department) that resolve to this brief — HR-editable, fixes the free-text mismatch problem without a code deploy
    purpose TEXT,                          -- 1-2 sentence department purpose
    responsibilities JSONB DEFAULT '[]',   -- array of strings: core functions / duties
    slas JSONB DEFAULT '[]',               -- array of strings: SLA commitments
    workflow_steps JSONB DEFAULT '[]',     -- array of strings: step-by-step operational flow
    reporting_rhythm TEXT,                 -- daily/weekly/monthly reporting cadence
    doc_reference TEXT,                    -- e.g. "SOP Section 6.0"
    updated_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_role_sop_department ON role_sop(department);