### **Spotify Personal Analytics Platform | Full-Stack Data Analytics App**
**July 2026**

**Tech Stack:** React 19.1.1, TypeScript 5.9.3, Vite 7.1.7, Material UI 7.3.4, MUI X Charts 8.14.0, Zustand 5.0.8, React Router 7.9.4, Axios 1.12.2, Python, FastAPI, Uvicorn, Pydantic, pandas, scikit-learn, PostgreSQL (Supabase), spotipy (Spotify Web API), lyricsgenius (Genius API), musixmatch-api, Netlify, Render

**Context:** Personal analytics platform processing a Spotify GDPR streaming-history export through a Python ETL pipeline, storing results in a Supabase/PostgreSQL analytics schema, and serving insights via a FastAPI backend + React/MUI dashboard. Pipeline flow: raw JSON export → dedup/extraction → metadata + genre enrichment via Spotify Web API → two-stage lyrics ingestion → validation → load into PostgreSQL → materialized views → FastAPI → React dashboard.

- Engineered a 4-stage Python ETL pipeline processing 71K+ Spotify streaming events, enriching metadata via Spotify Web API with custom rate limiting and exponential-backoff retry handling
- Built a genre-enrichment pipeline by joining artist-level metadata, overcoming a Spotify API limitation to enrich 13K+ tracks for downstream analytics
- Developed a two-stage lyrics ingestion pipeline (batch + retry) processing 13.8K tracks with checkpointing, multi-source API fallback, and automatic failure-based source disabling
- Designed a PostgreSQL analytics schema with materialized views, composite/partial indexes, and 16 SQL RPC functions, enabling low-latency pre-aggregated queries over streaming history
