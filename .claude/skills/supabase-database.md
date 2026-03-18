# Supabase Database Skill

## Setup
- SUPABASE_URL, SUPABASE_ANON_KEY (client)
- SUPABASE_SERVICE_KEY (server only, never expose)

## Always Use Typed Client
```python
from supabase import create_client, Client
import os

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_ANON_KEY", "")
supabase: Client = create_client(url, key)
```

## Error Handling
```python
try:
    response = supabase.table("users").select("*").execute()
    data = response.data
except Exception as e:
    logger.error(f"Database error: {e}")
    raise RuntimeError("Failed to fetch users") from e
```

## RLS Rules
- ALWAYS enable RLS on user data tables
- Use auth.uid() to restrict to own data
- Test policies before deploying

## Common Patterns
```python
# Single record
response = supabase.table("profiles").select("*").eq("user_id", user_id).single().execute()

# Insert with return
response = supabase.table("posts").insert({"title": title, "user_id": user_id}).execute()

# Pagination
response = supabase.table("items").select("*", count="exact").range(0, 9).execute()
```

## Don'ts
- NEVER expose service key to client
- NEVER skip error checking
- NEVER disable RLS in production
