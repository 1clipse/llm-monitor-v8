# data/

Local runtime files live here:

- `llm_monitor.db` is created automatically by the backend when SQLite is used.
- `relays.json` configures mock and OpenAI-compatible relay targets.
- Uploaded historical logs or vector files can be placed here for future import scripts.

This directory is mounted into the backend container by Docker Compose, so data remains on the host machine.
