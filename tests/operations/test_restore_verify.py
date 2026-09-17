from __future__ import annotations

from scripts.restore_verify import RecoveryReport


def test_recovery_report_requires_all_checks_to_pass():
    report = RecoveryReport(
        migration=True,
        connectivity=True,
        representative_read=True,
        public_page=True,
        admin_edit=True,
        snapshot_generation=False,
        duration_seconds=12,
        failures=["snapshot generation failed"],
    )
    assert report.success is False
