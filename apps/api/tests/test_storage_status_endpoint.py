from ai_trading_agent_storage import build_expected_migration_inventory
from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app


def test_storage_status_endpoint() -> None:
    client = TestClient(app)
    response = client.get('/storage/status')
    assert response.status_code == 200
    data = response.json()
    assert data['storage_ready'] is False
    assert data['selected_database_nl'] == 'PostgreSQL gepland'
    assert data['migration_tool_nl'] == 'Alembic gepland'
    assert data['implementation_status_nl'] == 'Nog niet geïmplementeerd'
    assert data['first_persistence_target_nl'] == 'Eerste paper setup en paper cash'
    assert data['migrations_available'] is True
    assert data['can_persist_paper_setup'] is False
    assert data['can_persist_transactions'] is False
    assert data['can_persist_audit_events'] is False
    assert data['summary_nl'].startswith('Database niet verbonden')

    migration_readiness = data['migration_readiness']
    assert migration_readiness['status'] == 'not_connected'
    assert migration_readiness['status_nl'] == 'Database niet verbonden'
    assert migration_readiness['database_connected'] is False
    assert migration_readiness['migrations_checked_against_database'] is False
    assert migration_readiness['offline_inventory_valid'] is True
    expected_inventory = build_expected_migration_inventory()
    assert (
        migration_readiness['latest_expected_revision_id']
        == expected_inventory.latest_expected_revision_id
    )
    assert (
        migration_readiness['expected_revision_count']
        == expected_inventory.revision_count
    )
    assert migration_readiness['database_revision_id'] is None
    assert migration_readiness['persistence_allowed'] is False
    assert migration_readiness['blocks_runtime_writes'] is True
    assert migration_readiness['safe_to_write'] is False

    assert any(b['label_nl'] == 'PostgreSQL' for b in data['backends'])
    assert any(b['label_nl'] == 'Auditlog' for b in data['backends'])
    assert data['backup']['status'] == 'not_configured'
    assert data['backup']['restore_tested'] is False
    assert 'secret' not in str(data).lower()
    assert all('connected' not in b['status_nl'].lower() for b in data['backends'])
