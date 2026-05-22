import sqlite3

# --------------------------------
# CREATE DATABASE + TABLE
# --------------------------------
def initialize_database():

    conn = sqlite3.connect("summaries.db")

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        summary TEXT
    )
    """)

    conn.commit()

    conn.close()

    print("Database initialized.")


# --------------------------------
# SAVE SUMMARY
# --------------------------------
def save_summary(query, summary):

    conn = sqlite3.connect("summaries.db")

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO summaries (query, summary)
        VALUES (?, ?)
        """,
        (query, summary)
    )

    conn.commit()

    conn.close()

    print("Summary saved to database.")


# --------------------------------
# VIEW SAVED SUMMARIES
# --------------------------------
def view_summaries():

    conn = sqlite3.connect("summaries.db")

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM summaries")

    rows = cursor.fetchall()

    conn.close()

    return rows