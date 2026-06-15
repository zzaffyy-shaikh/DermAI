"""Stateful services: session store, consultation queue, admin/user store.

These are in-memory reference implementations with a clean interface so they can be
swapped for Firestore-backed versions without touching the API layer.
"""
