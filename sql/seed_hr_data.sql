-- Seed HR Prototype Users
-- Passwords should be handled via the backend register endpoint if possible, 
-- but this SQL provides the structure. Note: Supabase passwords are hashed.
-- For direct SQL insertion, we use placeholders or the app logic.

-- INSERT INTO admins (id, full_name, email, role, primary_role) 
-- VALUES 
-- (gen_random_uuid(), 'Femi Adeyemi', 'f.adeyemi@eximps-cloves.com', 'hr_admin,admin', 'hr'),
-- (gen_random_uuid(), 'Amaka Okonkwo', 'a.okonkwo@eximps-cloves.com', 'line_manager,staff', 'hr'),
-- (gen_random_uuid(), 'Chidi Eze', 'c.eze@eximps-cloves.com', 'staff', 'dashboard'),
-- (gen_random_uuid(), 'Tunde Olawale', 't.olawale@eximps-cloves.com', 'staff', 'dashboard'),
-- (gen_random_uuid(), 'Ebele Nwosu', 'e.nwosu@eximps-cloves.com', 'staff', 'dashboard');

-- Since I cannot hash passwords in pure SQL easily (without extensions), 
-- I will provide the script as a reference.

/*
HR ADMIN
Name: Femi Adeyemi
Email: f.adeyemi@eximps-cloves.com
Password: hr2026

LINE MANAGER
Name: Amaka Okonkwo
Email: a.okonkwo@eximps-cloves.com
Password: lm2026

STAFF
Name: Chidi Eze
Email: c.eze@eximps-cloves.com
Password: ce2026

CONTRACTOR (Staff Role)
Name: Tunde Olawale
Email: t.olawale@eximps-cloves.com
Password: to2026

ONSITE (Staff Role)
Name: Ebele Nwosu
Email: e.nwosu@eximps-cloves.com
Password: en2026
*/
