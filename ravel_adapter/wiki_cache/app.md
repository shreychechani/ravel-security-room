📄 Wiki · app.py
Demo Flask app with three planted security findings for Ravel Security Room.
Used by: no other module
Functions:
• init_db() — called by app.py module code
• search(term) — called by search_view() · ⚠️ B608 SQL injection (reachable)
• search_view() — HTTP route GET /api/search (outside input) · calls search()
• checkout_view() — HTTP route POST /api/checkout (outside input) · calls process_payment()
