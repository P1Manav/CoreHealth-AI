-- ============================================================================
-- Healthcare AI Chatbot — Supabase Schema
-- ============================================================================
-- Run this in the Supabase SQL Editor after:
--   1. Enabling the Google OAuth provider in Auth → Providers → Google
--   2. Enabling the pgvector extension in Database → Extensions
-- ============================================================================

-- Enable pgvector for semantic memory recall
create extension if not exists vector;

-- ============================================================================
-- TABLES
-- ============================================================================

-- User profile: demographics, preferences, interaction style
create table if not exists profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  demographics jsonb default '{}'::jsonb,
  preferences jsonb default '{"answer_style": "balanced", "reading_level": "general", "language": "en"}'::jsonb,
  interaction_style jsonb default '{"tends_to_worry": false, "prefers_reassurance": false, "asks_followups": false}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Tracked medical conditions
create table if not exists medical_conditions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  status text not null check (status in ('ongoing', 'resolved', 'unknown')),
  first_mentioned timestamptz default now(),
  last_checked timestamptz default now()
);

-- Symptom log
create table if not exists symptom_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  symptom text not null,
  status text not null check (status in ('ongoing', 'resolved', 'unknown')),
  first_mentioned timestamptz default now(),
  last_checked timestamptz default now()
);

-- Semantic memory facts (with vector embedding for similarity search)
create table if not exists memory_facts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  fact text not null,
  embedding vector(384),  -- matches all-MiniLM-L6-v2 output dimension
  confidence float default 0.8,
  source_message_id uuid,
  created_at timestamptz default now()
);

-- Chat sessions (one per visit/conversation)
create table if not exists chat_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text,
  created_at timestamptz default now()
);

-- Add title column if upgrading from old schema (safe to run multiple times)
alter table chat_sessions add column if not exists title text;

-- Chat messages within sessions
create table if not exists chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references chat_sessions(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamptz default now()
);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================
-- Every table is locked down so users can only access their own data.

alter table profiles enable row level security;
alter table medical_conditions enable row level security;
alter table symptom_log enable row level security;
alter table memory_facts enable row level security;
alter table chat_sessions enable row level security;
alter table chat_messages enable row level security;

-- Profiles
create policy "Users can read own profile"
  on profiles for select using (user_id = auth.uid());
create policy "Users can insert own profile"
  on profiles for insert with check (user_id = auth.uid());
create policy "Users can update own profile"
  on profiles for update using (user_id = auth.uid());
create policy "Users can delete own profile"
  on profiles for delete using (user_id = auth.uid());

-- Medical conditions
create policy "Users can read own conditions"
  on medical_conditions for select using (user_id = auth.uid());
create policy "Users can insert own conditions"
  on medical_conditions for insert with check (user_id = auth.uid());
create policy "Users can update own conditions"
  on medical_conditions for update using (user_id = auth.uid());
create policy "Users can delete own conditions"
  on medical_conditions for delete using (user_id = auth.uid());

-- Symptom log
create policy "Users can read own symptoms"
  on symptom_log for select using (user_id = auth.uid());
create policy "Users can insert own symptoms"
  on symptom_log for insert with check (user_id = auth.uid());
create policy "Users can update own symptoms"
  on symptom_log for update using (user_id = auth.uid());
create policy "Users can delete own symptoms"
  on symptom_log for delete using (user_id = auth.uid());

-- Memory facts
create policy "Users can read own memory facts"
  on memory_facts for select using (user_id = auth.uid());
create policy "Users can insert own memory facts"
  on memory_facts for insert with check (user_id = auth.uid());
create policy "Users can update own memory facts"
  on memory_facts for update using (user_id = auth.uid());
create policy "Users can delete own memory facts"
  on memory_facts for delete using (user_id = auth.uid());

-- Chat sessions
create policy "Users can read own sessions"
  on chat_sessions for select using (user_id = auth.uid());
create policy "Users can insert own sessions"
  on chat_sessions for insert with check (user_id = auth.uid());
create policy "Users can delete own sessions"
  on chat_sessions for delete using (user_id = auth.uid());

-- Chat messages (scoped through session ownership)
create policy "Users can read own messages"
  on chat_messages for select
  using (session_id in (select id from chat_sessions where user_id = auth.uid()));
create policy "Users can insert own messages"
  on chat_messages for insert
  with check (session_id in (select id from chat_sessions where user_id = auth.uid()));
create policy "Users can delete own messages"
  on chat_messages for delete
  using (session_id in (select id from chat_sessions where user_id = auth.uid()));

-- ============================================================================
-- INDEXES for performance
-- ============================================================================
create index if not exists idx_medical_conditions_user on medical_conditions(user_id);
create index if not exists idx_symptom_log_user on symptom_log(user_id);
create index if not exists idx_memory_facts_user on memory_facts(user_id);
create index if not exists idx_chat_sessions_user on chat_sessions(user_id);
create index if not exists idx_chat_messages_session on chat_messages(session_id);

-- pgvector index for semantic memory similarity search
create index if not exists idx_memory_facts_embedding
  on memory_facts using ivfflat (embedding vector_cosine_ops)
  with (lists = 10);

-- ============================================================================
-- AUTO-CREATE PROFILE on sign-up (trigger)
-- ============================================================================
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (user_id)
  values (new.id)
  on conflict (user_id) do nothing;
  return new;
exception when others then
  -- Ensure auth user creation is never blocked
  return new;
end;
$$ language plpgsql security definer set search_path = public;

-- Re-create trigger safely
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
