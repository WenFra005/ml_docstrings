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
                       object_name TEXT,
                       style TEXT
                       );
                    """
    )
    conn.commit()
    conn.close()
    print(
        f"Banco de dados '{DATABASE_NAME}' e tabela 'docstrings' criados/verificados com sucesso."
    )


def insert_docstring(
    content,
    source_url=None,
    project_name=None,
    file_path=None,
    doc_type=None,
    object_name=None,
    style=None,
):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
                   INSERT INTO docstrings (content, source_url, project_name, file_path, doc_type, style)
                   values (?, ?, ?, ?, ?, ?)
                   """,
        (content, source_url, project_name, file_path, doc_type, object_name, style),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_table()
    print("Tabela 'docstrings' criada com sucesso.")
