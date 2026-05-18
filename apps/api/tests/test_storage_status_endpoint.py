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
    assert data['migrations_available'] is False
    assert data['can_persist_paper_setup'] is False
    assert data['can_persist_transactions'] is False
    assert data['can_persist_audit_events'] is False
    assert data['summary_nl'] == 'Opslag gepland, nog niet verbonden.'
    assert any(b['label_nl'] == 'PostgreSQL' for b in data['backends'])
    assert any(b['label_nl'] == 'Auditlog' for b in data['backends'])
    assert data['backup']['status'] == 'not_configured'
    assert data['backup']['restore_tested'] is False
    assert 'secret' not in str(data).lower()
    assert all('connected' not in b['status_nl'].lower() for b in data['backends'])
