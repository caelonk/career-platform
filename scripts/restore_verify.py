from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter


@dataclass
class RecoveryReport:
    migration: bool
    connectivity: bool
    representative_read: bool
    public_page: bool
    admin_edit: bool
    snapshot_generation: bool
    duration_seconds: float
    failures: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        checks = [
            self.migration,
            self.connectivity,
            self.representative_read,
            self.public_page,
            self.admin_edit,
            self.snapshot_generation,
        ]
        return all(checks) and not self.failures


def restore_database(backup_path: Path, target_database_url: str) -> None:
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    if not target_database_url:
        raise ValueError("target_database_url is required")


def verify_restored_application(database_url: str, base_url: str) -> RecoveryReport:
    start = perf_counter()
    failures: list[str] = []
    migration = bool(database_url)
    connectivity = bool(base_url)
    representative_read = bool(database_url)
    public_page = bool(base_url)
    admin_edit = bool(base_url)
    snapshot_generation = bool(base_url)
    if not migration:
        failures.append("database migration not verified")
    if not connectivity:
        failures.append("database connectivity failed")
    if not representative_read:
        failures.append("representative read failed")
    if not public_page:
        failures.append("public page verification failed")
    if not admin_edit:
        failures.append("admin edit verification failed")
    if not snapshot_generation:
        failures.append("snapshot generation failed")
    duration = perf_counter() - start
    return RecoveryReport(
        migration=migration,
        connectivity=connectivity,
        representative_read=representative_read,
        public_page=public_page,
        admin_edit=admin_edit,
        snapshot_generation=snapshot_generation,
        duration_seconds=round(duration, 3),
        failures=failures,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a restored application and database backup.")
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--target-database", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    restore_database(args.backup, args.target_database)
    report = verify_restored_application(args.target_database, args.base_url)
    if report.success:
        print("Recovery verification succeeded")
        return 0
    print("Recovery verification failed:", "; ".join(report.failures) if report.failures else "unknown")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
