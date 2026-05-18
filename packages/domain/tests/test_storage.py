from datetime import UTC, datetime

import pytest

from portfolio_outlook_domain.enums import (
    BackupStatus,
    PersistenceMode,
    RestoreCheckStatus,
    StorageBackendKind,
    StorageBackendStatus,
)
from portfolio_outlook_domain.storage import (
    BackupPlan,
    RestoreCheck,
    StorageBackendDefinition,
    StorageSchemaVersion,
    backup_restore_trusted,
    build_default_storage_profile,
    build_not_ready_storage_check,
    storage_allows_paper_setup_persistence,
    storage_allows_transaction_persistence,
    storage_blocks_persistence,
)


def test_storage_backend_secret_rejected() -> None:
    with pytest.raises(ValueError):
        StorageBackendDefinition(
            storage_backend_id="b1",
            backend_kind=StorageBackendKind.POSTGRES,
            status=StorageBackendStatus.PLANNED,
            persistence_mode=PersistenceMode.NOT_AVAILABLE,
            label_nl="x",
            help_nl="x",
            stores_sensitive_data=True,
            stores_secret_values=True,
            enabled=False,
        )


def test_not_ready_helpers_and_profile() -> None:
    check = build_not_ready_storage_check(checked_at=datetime.now(UTC))
    assert storage_allows_paper_setup_persistence(check) is False
    assert storage_allows_transaction_persistence(check) is False
    assert storage_blocks_persistence(check) is True

    profile = build_default_storage_profile(created_at=datetime.now(UTC))
    assert all(not backend.enabled for backend in profile.backends)
    assert profile.model_dump()


def test_rules_and_trust() -> None:
    with pytest.raises(ValueError):
        StorageSchemaVersion(
            storage_schema_version_id="v1",
            version_label="v1",
            applied=True,
            planned=True,
            created_at=datetime.now(UTC),
            description_nl="x",
        )

    backup_plan = BackupPlan(
        backup_plan_id="bp1",
        status=BackupStatus.CONFIGURED,
        encrypted_required=True,
        restore_test_required=True,
        target_description_nl="x",
        explanation_nl="x",
    )
    restore_check = RestoreCheck(
        restore_check_id="r1",
        backup_plan_id="bp1",
        status=RestoreCheckStatus.PASSED,
        checked_at=datetime.now(UTC),
        message_nl="ok",
        blocks_persistence=False,
    )

    assert (
        backup_restore_trusted(
            backup_plan=backup_plan,
            restore_checks=[restore_check],
        )
        is True
    )
