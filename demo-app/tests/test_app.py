import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def make_client(tmp_path):
    os.environ["DEMO_DB"] = str(tmp_path / "test.db")
    import importlib
    import app as app_module

    importlib.reload(app_module)
    app_module.init_db()
    return app_module.app.test_client()


def test_search_finds_product(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/search?q=almo").get_json() == [[1, "almonds"]]


def test_search_blocks_sql_injection(tmp_path):
    # Fails until FINDING 1 is fixed: the payload dumps every row
    client = make_client(tmp_path)
    rows = client.get("/api/search?q=' OR '1'='1' --").get_json()
    assert rows == []
