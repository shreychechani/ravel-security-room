"""Demo Flask app with three planted security findings for Ravel Security Room.

FINDING 1 (reachable):   SQL injection in search(), reached from /api/search
FINDING 2 (unreachable): eval() in legacy_utils.eval_expr(), never called
FINDING 3 (unreachable): unsafe yaml.load in vendor/old_parser.py, never imported
"""
import os
import sqlite3

from flask import Flask, jsonify, request

from payments import process_payment

app = Flask(__name__)
DB = os.environ.get("DEMO_DB", "demo.db")


def init_db():
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT)")
    if con.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO products (name) VALUES (?)",
            [("almonds",), ("cashews",), ("walnuts",)],
        )
    con.commit()
    con.close()


def search(term):
    con = sqlite3.connect(DB)
    # FINDING 1: user input is formatted straight into the SQL string
    rows = con.execute(
        f"SELECT id, name FROM products WHERE name LIKE '%{term}%'"
    ).fetchall()
    con.close()
    return rows


@app.route("/api/search")
def search_view():
    return jsonify(search(request.args.get("q", "")))


@app.route("/api/checkout", methods=["POST"])
def checkout_view():
    data = request.get_json(silent=True) or {}
    return jsonify(process_payment(data.get("amount", 0)))


if __name__ == "__main__":
    init_db()
    # Port 8000, not Flask's default 5000 (macOS AirPlay Receiver uses 5000)
    app.run(port=8000)
