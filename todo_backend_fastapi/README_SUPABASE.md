# Backend and Supabase

Current FastAPI endpoints (/health, /quote) do not require Supabase, but the app is ready to extend with JWT verification if you expose protected endpoints.

CORS
- Set FRONTEND_ORIGINS in .env (comma separated) to your frontend origins.
- The app reads FRONTEND_ORIGINS and configures CORS accordingly.

JWT (optional future)
- If you later secure endpoints with Supabase JWTs, extract the Bearer token and validate with the Supabase jwks or use supabase-python if integrating PostgREST.
- RLS on the database continues to enforce data-level permissions for direct calls via supabase-js from the frontend.

See assets/supabase.md for database schema and policies.
