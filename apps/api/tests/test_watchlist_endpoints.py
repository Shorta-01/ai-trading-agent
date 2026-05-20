from fastapi.testclient import TestClient
from portfolio_outlook_api.main import app
from portfolio_outlook_api.watchlist import STORE

client = TestClient(app)

def setup_function() -> None:
    STORE.clear()

def test_watchlist_crud_flow() -> None:
    empty = client.get('/watchlist/items')
    assert empty.status_code == 200
    assert empty.json()['items'] == []

    created = client.post('/watchlist/items', json={'symbol': ' asml ', 'note': 'kernpositie volgen'})
    assert created.status_code == 200
    item = created.json()['item']
    assert item['symbol'] == 'ASML'
    get_one = client.get(f"/watchlist/items/{item['watchlist_item_id']}")
    assert get_one.status_code == 200

    dup = client.post('/watchlist/items', json={'symbol': 'ASML'})
    assert dup.status_code == 409

    updated = client.patch(f"/watchlist/items/{item['watchlist_item_id']}", json={'note': 'bijgewerkt'})
    assert updated.status_code == 200
    assert updated.json()['item']['note'] == 'bijgewerkt'

    archived = client.delete(f"/watchlist/items/{item['watchlist_item_id']}")
    assert archived.status_code == 200
    listed = client.get('/watchlist/items')
    assert listed.json()['items'] == []
