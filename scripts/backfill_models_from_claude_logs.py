import argparse
import json
import sqlite3
from pathlib import Path


def text_from_content(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    parts: list[str] = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, str) and block.strip():
                parts.append(block.strip())
            elif isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                text = str(block["text"]).strip()
                if text:
                    parts.append(text)
    return "\n".join(parts).strip()


def iter_assistant_events(projects_dir: Path, recent_files: int):
    files = sorted(projects_dir.rglob("*.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)[:recent_files]
    for file_path in files:
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = event.get("message") or {}
            if event.get("type") != "assistant" or message.get("role") != "assistant":
                continue
            model = message.get("model")
            text = text_from_content(message.get("content"))
            if not model or not text:
                continue
            usage = message.get("usage") or {}
            input_tokens = int(usage.get("input_tokens") or 0)
            output_tokens = int(usage.get("output_tokens") or 0)
            yield {
                "model": str(model),
                "text": text,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill LLM Monitor model names from Claude Code JSONL logs.")
    parser.add_argument("--projects-dir", default=r"C:\Users\Knightz\.claude\projects")
    parser.add_argument("--database", default=r"D:\LLMtext\llm-monitor-v8\data\llm_monitor.db")
    parser.add_argument("--recent-files", type=int, default=160)
    args = parser.parse_args()

    projects_dir = Path(args.projects_dir)
    database = Path(args.database)
    if not projects_dir.exists():
        raise SystemExit(f"Claude projects directory not found: {projects_dir}")
    if not database.exists():
        raise SystemExit(f"Monitor database not found: {database}")

    events = list(iter_assistant_events(projects_dir, args.recent_files))
    updated = 0
    with sqlite3.connect(database) as conn:
        for event in events:
            cursor = conn.execute(
                """
                UPDATE logs
                SET model_name = ?,
                    provider = coalesce(provider, 'claude-code'),
                    prompt_tokens = CASE WHEN ? > 0 THEN ? ELSE prompt_tokens END,
                    completion_tokens = CASE WHEN ? > 0 THEN ? ELSE completion_tokens END,
                    total_tokens = CASE WHEN ? > 0 THEN ? ELSE total_tokens END,
                    token_source = CASE WHEN ? > 0 THEN 'reported' ELSE coalesce(token_source, 'estimated') END
                WHERE id = (
                    SELECT id FROM logs
                    WHERE (model_name IS NULL OR model_name IN ('unknown-model', 'cc-switch-observed'))
                      AND response_text = ?
                    ORDER BY id DESC
                    LIMIT 1
                )
                """,
                (
                    event["model"],
                    event["input_tokens"],
                    event["input_tokens"],
                    event["output_tokens"],
                    event["output_tokens"],
                    event["total_tokens"],
                    event["total_tokens"],
                    event["total_tokens"],
                    event["text"],
                ),
            )
            updated += cursor.rowcount
        conn.commit()
    print(f"Backfill complete. Matched/updated rows: {updated} from Claude assistant events: {len(events)}")


if __name__ == "__main__":
    main()
