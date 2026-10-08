"""Copy every content table from a SQLite file into an empty, migrated database (Railway Postgres)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import Integer, create_engine, func, select, text
from sqlalchemy.engine import make_url

from app.config import normalize_database_url
from app.db.migrate import current_revision, head_revision
from app.db.models import Base


class CopyError(RuntimeError):
    pass


def _reset_postgres_sequences(connection) -> None:
    """Rows were inserted with explicit ids, so move each serial sequence past the highest id."""
    for table in Base.metadata.sorted_tables:
        id_column = table.columns.get("id")
        if id_column is None or not isinstance(id_column.type, Integer):
            continue
        connection.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {table.name}), 1), "
                f"(SELECT MAX(id) FROM {table.name}) IS NOT NULL)"
            )
        )


def copy_database(source_url: str, target_url: str) -> dict[str, int]:
    source_url, target_url = normalize_database_url(source_url), normalize_database_url(target_url)
    if current_revision(target_url) != head_revision():
        raise CopyError("Target schema is not at the latest migration; run `alembic upgrade head` against it first.")

    source = create_engine(source_url)
    target = create_engine(target_url)
    tables = Base.metadata.sorted_tables
    try:
        with target.connect() as connection:
            occupied = [t.name for t in tables if connection.scalar(select(func.count()).select_from(t))]
        if occupied:
            raise CopyError(f"Target is not empty ({', '.join(occupied)} already have rows); refusing to copy.")

        copied: dict[str, int] = {}
        with source.connect() as reader, target.begin() as writer:
            for table in tables:
                rows = [dict(row) for row in reader.execute(select(table)).mappings()]
                if rows:
                    writer.execute(table.insert(), rows)
                copied[table.name] = len(rows)
            if writer.dialect.name == "postgresql":
                _reset_postgres_sequences(writer)

        with target.connect() as connection:
            for table in tables:
                landed = connection.scalar(select(func.count()).select_from(table))
                if landed != copied[table.name]:
                    raise CopyError(f"{table.name}: copied {copied[table.name]} rows but target has {landed}.")
        return copied
    finally:
        source.dispose()
        target.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Path to the SQLite file to copy from")
    parser.add_argument("--target-env", default="DATABASE_PUBLIC_URL", help="Environment variable holding the target URL")
    args = parser.parse_args()

    if not args.source.is_file():
        print(f"Source file not found: {args.source}", file=sys.stderr)
        return 1
    target_url = os.environ.get(args.target_env)
    if not target_url:
        print(f"{args.target_env} is not set; run this under `railway run --service Postgres`.", file=sys.stderr)
        return 1

    print("Target:", make_url(normalize_database_url(target_url)).render_as_string(hide_password=True))
    try:
        counts = copy_database(f"sqlite:///{args.source.resolve()}", target_url)
    except CopyError as error:
        print(f"Copy refused: {error}", file=sys.stderr)
        return 1
    for name, count in counts.items():
        print(f"{name:24} {count}")
    print("Copy complete; row counts match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
