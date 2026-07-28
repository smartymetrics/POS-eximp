-- Migration 055: Blog module (posts, review workflow, placements, comments, reactions, media, audit log)
-- Follows existing conventions: Supabase/Postgres, gen_random_uuid(), TIMESTAMPTZ, admins(id) FK for staff refs.

-- 1. Blog posts -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS blog_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,      -- Tiptap JSON document
    excerpt TEXT,
    cover_image_url TEXT,

    status VARCHAR(30) NOT NULL DEFAULT 'draft',      -- draft | pending_review | published | rejected
    author_id UUID NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    author_name_snapshot VARCHAR(255),
    author_department_snapshot VARCHAR(100),

    reviewed_by_id UUID REFERENCES admins(id),
    reviewed_at TIMESTAMPTZ,
    review_comment TEXT,

    seo_title VARCHAR(255),
    seo_description VARCHAR(500),
    tags TEXT[] DEFAULT '{}',
    category VARCHAR(100),

    share_token UUID,                                 -- non-null enables preview link for draft/pending posts

    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blog_posts_status ON blog_posts(status);
CREATE INDEX IF NOT EXISTS idx_blog_posts_author ON blog_posts(author_id);
CREATE INDEX IF NOT EXISTS idx_blog_posts_slug ON blog_posts(slug);
CREATE INDEX IF NOT EXISTS idx_blog_posts_share_token ON blog_posts(share_token);

-- 2. Blog media (images/videos attached to a post, beyond inline editor content) ---
CREATE TABLE IF NOT EXISTS blog_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES blog_posts(id) ON DELETE CASCADE,
    media_type VARCHAR(20) NOT NULL,   -- image | video
    source VARCHAR(20) NOT NULL,       -- upload | url | youtube
    url TEXT NOT NULL,
    caption VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_blog_media_post ON blog_media(post_id);

-- 3. Audit log ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS blog_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES blog_posts(id) ON DELETE CASCADE,
    actor_id UUID REFERENCES admins(id),
    action VARCHAR(50) NOT NULL,   -- created | submitted | approved | rejected | edited | published | share_link_created | share_link_revoked
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_blog_audit_post ON blog_audit_log(post_id);

-- 4. Curation placements (featured / ticker / top content / custom shelves) ---
CREATE TABLE IF NOT EXISTS blog_placements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    placement_type VARCHAR(50) NOT NULL,  -- featured | ticker | top_content | category_spotlight | custom_shelf
    post_id UUID NOT NULL REFERENCES blog_posts(id) ON DELETE CASCADE,
    position INT DEFAULT 0,
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    created_by UUID REFERENCES admins(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_blog_placements_type ON blog_placements(placement_type);
CREATE INDEX IF NOT EXISTS idx_blog_placements_post ON blog_placements(post_id);

-- 5. Public comments (readers, not ERP admins) --------------------------------
CREATE TABLE IF NOT EXISTS blog_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES blog_posts(id) ON DELETE CASCADE,
    parent_comment_id UUID REFERENCES blog_comments(id) ON DELETE CASCADE,
    author_name VARCHAR(150) NOT NULL,
    author_email VARCHAR(255) NOT NULL,   -- never exposed publicly, spam-control only
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'visible',  -- visible | hidden | deleted
    hidden_by UUID REFERENCES admins(id),
    hidden_at TIMESTAMPTZ,
    hidden_reason VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_blog_comments_post ON blog_comments(post_id, status);

-- 6. Reactions (likes) ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS blog_reactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES blog_posts(id) ON DELETE CASCADE,
    reader_identifier VARCHAR(255) NOT NULL,  -- cookie/fingerprint id, not a user account
    reaction_type VARCHAR(20) NOT NULL DEFAULT 'like',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id, reader_identifier, reaction_type)
);
CREATE INDEX IF NOT EXISTS idx_blog_reactions_post ON blog_reactions(post_id);

-- Notes:
-- * Roles used by this module ("blog_publisher", "blog_curator", "blog_moderator") ride on the
--   existing comma-separated admins.role column -- no schema change needed there.
-- * Uses the existing `notifications` table / create_notification() helper for review-queue pings.