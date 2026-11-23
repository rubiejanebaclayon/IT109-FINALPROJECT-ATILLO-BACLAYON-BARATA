-- =====================================================================
-- Student Gig & Skill Marketplace - PostgreSQL schema (Supabase)
-- Run this whole file once in: Supabase Dashboard > SQL Editor > New query
-- =====================================================================

create extension if not exists "pgcrypto";   -- gen_random_uuid()

-- ---------- ENUM TYPES ------------------------------------------------
do $$ begin
  create type user_role      as enum ('client', 'freelancer', 'admin');
  create type gig_status     as enum ('pending_approval', 'approved', 'rejected', 'awarded', 'closed', 'cancelled');
  create type bid_status     as enum ('pending', 'accepted', 'rejected', 'withdrawn');
  create type contract_status as enum ('pending_payment', 'funded', 'submitted', 'approved', 'paid_out', 'cancelled');
  create type payment_status as enum ('pending', 'paid', 'failed', 'expired');
  create type payout_status  as enum ('pending', 'processing', 'paid', 'failed');
exception when duplicate_object then null; end $$;

-- ---------- USERS -----------------------------------------------------
create table if not exists users (
  id            uuid primary key default gen_random_uuid(),
  google_sub    text unique not null,                -- Google account id
  email         text unique not null,
  full_name     text not null,
  avatar_url    text,
  role          user_role not null default 'client',
  is_active     boolean not null default true,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- ---------- PROFILES (1:1 with users) --------------------------------
create table if not exists profiles (
  user_id        uuid primary key references users(id) on delete cascade,
  headline       text check (char_length(headline) <= 120),
  bio            text check (char_length(bio) <= 2000),
  skills         text[] not null default '{}',
  school_or_dept text,
  contact_number text,
  -- PSGC address (codes + names saved so the UI can show them offline)
  region_code    text, region_name   text,
  province_code  text, province_name text,
  city_code      text, city_name     text,
  barangay_code  text, barangay_name text,
  updated_at     timestamptz not null default now()
);

-- ---------- PORTFOLIO ITEMS (assets live in object storage) ---------
create table if not exists portfolio_items (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references users(id) on delete cascade,
  title        text not null check (char_length(title) between 3 and 120),
  description  text check (char_length(description) <= 1000),
  asset_url    text not null,          -- public URL from Supabase Storage
  storage_path text not null,          -- path inside the bucket (for deletes)
  content_type text not null,
  created_at   timestamptz not null default now()
);
create index if not exists idx_portfolio_user on portfolio_items(user_id);

-- ---------- GIG REQUESTS ---------------------------------------------
create table if not exists gig_requests (
  id           uuid primary key default gen_random_uuid(),
  client_id    uuid not null references users(id) on delete cascade,
  title        text not null check (char_length(title) between 5 and 150),
  description  text not null check (char_length(description) between 20 and 4000),
  category     text not null,
  budget_min   numeric(10,2) not null check (budget_min >= 50),
  budget_max   numeric(10,2) not null check (budget_max >= budget_min),
  deadline     date not null,
  status       gig_status not null default 'pending_approval',
  admin_note   text,                    -- reason when rejected
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists idx_gigs_status   on gig_requests(status);
create index if not exists idx_gigs_client   on gig_requests(client_id);
create index if not exists idx_gigs_category on gig_requests(category);

-- ---------- BIDS -------------------------------------------------------
create table if not exists bids (
  id            uuid primary key default gen_random_uuid(),
  gig_id        uuid not null references gig_requests(id) on delete cascade,
  freelancer_id uuid not null references users(id) on delete cascade,
  amount        numeric(10,2) not null check (amount >= 50),
  delivery_days int not null check (delivery_days between 1 and 90),
  proposal      text not null check (char_length(proposal) between 20 and 2000),
  status        bid_status not null default 'pending',
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (gig_id, freelancer_id)        -- one bid per freelancer per gig
);
create index if not exists idx_bids_gig        on bids(gig_id);
create index if not exists idx_bids_freelancer on bids(freelancer_id);

-- ---------- CONTRACTS (escrow state machine) -------------------------
create table if not exists contracts (
  id            uuid primary key default gen_random_uuid(),
  gig_id        uuid not null unique references gig_requests(id),
  bid_id        uuid not null unique references bids(id),
  client_id     uuid not null references users(id),
  freelancer_id uuid not null references users(id),
  amount        numeric(10,2) not null check (amount > 0),
  status        contract_status not null default 'pending_payment',
  funded_at     timestamptz,
  submitted_at  timestamptz,
  approved_at   timestamptz,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index if not exists idx_contracts_client     on contracts(client_id);
create index if not exists idx_contracts_freelancer on contracts(freelancer_id);

-- ---------- PAYMENTS (PayMongo sandbox prepayments) ------------------
create table if not exists payments (
  id                    uuid primary key default gen_random_uuid(),
  contract_id           uuid not null references contracts(id) on delete cascade,
  paymongo_session_id   text unique,           -- checkout session id (cs_...)
  paymongo_payment_id   text,                  -- pay_... once paid
  checkout_url          text,
  amount                numeric(10,2) not null,
  status                payment_status not null default 'pending',
  paid_at               timestamptz,
  created_at            timestamptz not null default now()
);
create index if not exists idx_payments_contract on payments(contract_id);

-- Idempotency: each PayMongo webhook event is processed only once
create table if not exists webhook_events (
  event_id    text primary key,
  event_type  text not null,
  received_at timestamptz not null default now()
);

-- ---------- SUBMISSIONS (external link deliverables) -----------------
create table if not exists submissions (
  id          uuid primary key default gen_random_uuid(),
  contract_id uuid not null references contracts(id) on delete cascade,
  link_url    text not null,                    -- e.g. Google Drive link
  notes       text check (char_length(notes) <= 1000),
  created_at  timestamptz not null default now()
);
create index if not exists idx_submissions_contract on submissions(contract_id);

-- ---------- GIG TICKET THREAD (not real-time chat) -------------------
create table if not exists thread_messages (
  id          uuid primary key default gen_random_uuid(),
  contract_id uuid not null references contracts(id) on delete cascade,
  sender_id   uuid not null references users(id),
  body        text not null check (char_length(body) between 1 and 2000),
  created_at  timestamptz not null default now()
);
create index if not exists idx_thread_contract on thread_messages(contract_id, created_at);

-- ---------- PAYOUTS (recorded manually by admin) --------------------
create table if not exists payouts (
  id            uuid primary key default gen_random_uuid(),
  contract_id   uuid not null unique references contracts(id),
  freelancer_id uuid not null references users(id),
  gross_amount  numeric(10,2) not null,
  platform_fee  numeric(10,2) not null default 0,
  net_amount    numeric(10,2) not null,
  status        payout_status not null default 'pending',
  method        text,                 -- e.g. GCash, Bank transfer
  reference_no  text,                 -- the admin's transfer reference
  admin_note    text,
  updated_by    uuid references users(id),
  paid_at       timestamptz,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index if not exists idx_payouts_freelancer on payouts(freelancer_id);

-- ---------- AUDIT LOG (who did what) --------------------------------
create table if not exists audit_log (
  id         bigserial primary key,
  actor_id   uuid references users(id),
  action     text not null,
  entity     text not null,
  entity_id  text,
  detail     jsonb,
  created_at timestamptz not null default now()
);

-- ---------- updated_at trigger ---------------------------------------
create or replace function set_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end; $$ language plpgsql;

do $$
declare t text;
begin
  foreach t in array array['users','profiles','gig_requests','bids','contracts','payouts']
  loop
    execute format('drop trigger if exists trg_%1$s_updated on %1$s;', t);
    execute format('create trigger trg_%1$s_updated before update on %1$s
                    for each row execute function set_updated_at();', t);
  end loop;
end $$;

-- ---------- ROW LEVEL SECURITY ---------------------------------------
-- The FastAPI backend connects with the database owner connection string and
-- enforces permissions itself. Enabling RLS with no policies blocks the public
-- Supabase REST API (anon key) from reading any table directly.
do $$
declare t text;
begin
  foreach t in array array['users','profiles','portfolio_items','gig_requests','bids',
    'contracts','payments','webhook_events','submissions','thread_messages','payouts','audit_log']
  loop
    execute format('alter table %I enable row level security;', t);
  end loop;
end $$;

-- ---------- STORAGE BUCKET (public read, uploads only via backend) ---
insert into storage.buckets (id, name, public)
values ('portfolio', 'portfolio', true)
on conflict (id) do nothing;

-- ---------- Promote your first admin AFTER you log in once ----------
-- update users set role = 'admin' where email = 'your.email@gmail.com';
