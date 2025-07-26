import os
import sqlite3

DATABASE_NAME = os.path.join("..", "data", "docstring.db")


def create_table():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
                   CREATE TABLE IF NOT EXISTS docstrings (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       content TEXT NOT NULL,
                       source_url TEXT,
                       project_name TEXT,
                       file_path TEXT,
                       doc_type TEXT,
                       style TEXT
                       );
                    """
    )
    conn.commit()
    conn.close()
    print(
        f"Banco de dados '{DATABASE_NAME}' e tabela 'docstrings' criados/verificados com sucesso."
    )
