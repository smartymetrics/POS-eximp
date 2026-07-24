-- Add unique constraint on guarantors(submission_id, slot_number)
-- Required for the upsert (ON CONFLICT) in the public save-partial endpoint.
ALTER TABLE guarantors
  ADD CONSTRAINT guarantors_submission_slot_unique
  UNIQUE (submission_id, slot_number);
