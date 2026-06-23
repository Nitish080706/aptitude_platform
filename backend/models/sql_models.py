# sql_models.py — REMOVED
#
# SQLAlchemy ORM models were removed from this project.
# All user profiles are now stored in Firestore users/{uid}.
# Firestore document structure:
#   users/{uid}
#     name: string
#     username: string
#     email: string
#     role: "user" | "admin"
#     theme_pref: "dark" | "light"
#     created_at: timestamp
#
# This file is kept as a placeholder to avoid import errors.
# You may safely delete it.
