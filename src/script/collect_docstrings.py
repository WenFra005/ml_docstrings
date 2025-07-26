import ast
import os
import sqlite3

from git import Repo

DATABASE_NAME = os.path.join("..", "data", "docstring.db")
CLONED_REPO_DIR = os.path.join("..", "cloned_repos")


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


def extract_docstrings_from_file(file_path, project_name=None):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            tree = ast.parse(file.read(), filename=file_path)
    except Exception as e:
        print(f"Erro ao ler/parsear o arquivo {file_path}: {e}")
        return

    for node in ast.walk(tree):
        docstring_content = None
        doc_type = None
        obj_name = None

        if isinstance in (node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            docstring_content = ast.get_docstring(node)
            doc_type = "function"
            obj_name = node.name
        elif isinstance(node, ast.ClassDef):
            docstring_content = ast.get_docstring(node)
            doc_type = "class"
            obj_name = node.name
        elif isinstance(node, ast.Module):
            docstring_content = ast.get_docstring(node)
            doc_type = "module"
            obj_name = project_name if project_name else os.path.basename(file_path)

        if docstring_content and docstring_content.strip():
            relative_path = os.path.relpath(
                file_path, os.path.join(CLONED_REPO_DIR, project_name)
            )
            github_url = f"https://github.com/{project_name}/blob/main/{relative_path}"

            insert_docstring(
                content=docstring_content,
                source_url=github_url,
                project_name=project_name,
                file_path=os.path.relpath(file_path, CLONED_REPO_DIR),
                doc_type=doc_type,
                object_name=obj_name,
                style=None,
            )
