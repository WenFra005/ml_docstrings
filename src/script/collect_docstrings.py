import ast
import os
import shutil
import sqlite3
import time
import stat

from git import Repo
from halo import Halo
from tqdm import tqdm

# Constantes para formatação de saída
LINE_WIDTH = 120
DELIMITER_CHAR = "="
DELIMITER_CHAR_LIGHT = "-"


DATABASE_NAME = os.path.join("..", "data", "docstring.db")
CLONED_REPO_DIR = os.path.join("..", "cloned_repos")


def handle_remove_readonly(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        print(f"Erro ao forçar remoção de {path}")


def time_format(seconds):
    seconds = int(round(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, rest = divmod(seconds, 3600)

    parts = []
    if hours:
        parts.append(f"{hours} hora{'s' if hours > 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minuto{'s' if minutes > 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} segundo{'s' if seconds > 1 else ''}")

    return " e ".join(parts)


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
        INSERT INTO docstrings (content, source_url, project_name, file_path, doc_type, object_name ,style)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (content, source_url, project_name,
         file_path, doc_type, object_name, style),
    )
    conn.commit()
    conn.close()


def extract_docstrings_from_file(file_path, project_name=None):
    file_processed_count = 1
    erros_count = 0

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            tree = ast.parse(file.read(), filename=file_path)
    except Exception as e:
        print(f"Erro ao ler/parsear o arquivo {file_path}: {e}")
        erros_count = 1
        return (file_processed_count, erros_count)

    for node in ast.walk(tree):
        docstring_content = None
        doc_type = None
        obj_name = None

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
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
            obj_name = project_name if project_name else os.path.basename(
                file_path)

        if docstring_content and docstring_content.strip():
            relative_path = os.path.relpath(
                file_path, os.path.join(CLONED_REPO_DIR, project_name)
            )
            github_url = f"https://github.com/{project_name}/blob/main/{relative_path}"

            try:
                insert_docstring(
                    content=docstring_content,
                    source_url=github_url,
                    project_name=project_name,
                    file_path=os.path.relpath(file_path, CLONED_REPO_DIR),
                    doc_type=doc_type,
                    object_name=obj_name,
                    style=None,
                )
            except Exception as e:
                print(
                    f"Erro ao inserir docstring no banco de dados para o arquivo {file_path}: {e}")
                erros_count = 1
    return (file_processed_count, erros_count)


def clone_and_extract_from_github(repo_info):
    repo_url = repo_info["url"]
    project_name = repo_info["name"]

    repo_files_scanned = 0
    repo_extraction_errors = 0

    print(f"\n{DELIMITER_CHAR_LIGHT * LINE_WIDTH}")
    print(f"Iniciando Processamento: {project_name}".center(LINE_WIDTH))
    print(f"{DELIMITER_CHAR_LIGHT * LINE_WIDTH}\n")

    repo_dir = os.path.join(CLONED_REPO_DIR, project_name)

    start_time_repo = time.time()

    spinner = Halo(
        text=f"Clonando {project_name} de {repo_url}...", spinner="dots")
    spinner.start()

    if os.path.exists(repo_dir):
        spinner.text = f"{project_name} já existe. Fazendo pull..."
        try:
            repo = Repo(repo_dir)
            origin = repo.remotes.origin
            origin.pull()
            spinner.succeed(
                f"Repositório {project_name} atualizado com sucesso.")
            print()
        except Exception as e:
            spinner.fail(
                f"Erro ao atualizar o repositório {project_name}: {e}")
            print()
            return (0, 0)
    else:
        try:
            Repo.clone_from(repo_url, repo_dir)
            spinner.succeed(f"Repositório {project_name} clonado com sucesso.")
            print()
        except Exception as e:
            spinner.succeed(
                f"Erro ao clonar o repositório {project_name}: {e}")
            print()
            return (0, 0)

    py_files = []

    for root, _, files in os.walk(repo_dir):
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))

    for file_path in tqdm(py_files, desc=f"Processando arquivos em {project_name}", unit="file"):
        files_scanned_in_file, errors_in_file = extract_docstrings_from_file(
            file_path, project_name)
        repo_files_scanned += files_scanned_in_file
        repo_extraction_errors += errors_in_file

    print()

    print(f"Docstrings do repositório {project_name} extraídos com sucesso.")
    print()

    end_time_repo = time.time()
    formated_time = time_format(end_time_repo - start_time_repo)

    try:
        if os.path.exists(repo_dir):
            spinner = Halo(
                text=f"Deletando o repositório clonado {project_name}...", spinner="dots")
            spinner.start()
            shutil.rmtree(repo_dir, onerror=handle_remove_readonly)
            spinner.succeed(
                f"Repositório {project_name} deletado com sucesso.")
            print()
    except OSError as e:
        spinner.fail(f"Erro ao deletar o repositório {project_name}: {e}")
        print()

    print(
        f"Tempo total para processar o repositório {project_name}: {formated_time}")

    print(f"\n{DELIMITER_CHAR_LIGHT * LINE_WIDTH}\n")

    return (repo_files_scanned, repo_extraction_errors)


if __name__ == "__main__":
    os.makedirs(CLONED_REPO_DIR, exist_ok=True)

    github_repos_to_collect = [
        # Projetos NumPy-Style
        {"url": "https://github.com/numpy/numpy.git", "name": "numpy"},
        {"url": "https://github.com/scipy/scipy.git", "name": "scipy"},
        {"url": "https://github.com/pandas-dev/pandas.git", "name": "pandas"},
        {"url": "https://github.com/scikit-learn/scikit-learn.git",
            "name": "scikit-learn"},
        # Projetos Google-Style
        {"url": "https://github.com/google/yapf.git", "name": "yapf"},
        {"url": "https://github.com/tensorflow/neural-structured-learning.git",
            "name": "neural-structured-learning"},
        {"url": "https://github.com/tensorflow/tensorflow.git", "name": "tensorflow"},
        {"url": "https://github.com/google/pytype.git", "name": "pytype"},
        # Projetos reStructuredText-Style (reST) / Sphinx-Style
        {"url": "https://github.com/psf/requests.git", "name": "requests"},
        {"url": "https://github.com/pallets/flask.git", "name": "flask"},
        {"url": "https://github.com/sqlalchemy/sqlalchemy.git", "name": "sqlalchemy"},
        {"url": "https://github.com/django/django.git", "name": "django"},
        # Projetos Estilo Livre / Misto / Não Padrão
        {"url": "https://github.com/sivel/speedtest-cli.git", "name": "speedtest-cli"},
        {"url": "https://github.com/nvbn/thefuck.git", "name": "thefuck"},
        {"url": "https://github.com/rg3/youtube-dl.git", "name": "youtube-dl"},
        {"url": "https://github.com/rochacbruno/python-project-template.git",
            "name": "python-project-template"},
    ]

    print(DELIMITER_CHAR * LINE_WIDTH)
    print("INICIANDO COLETOR DE DOCSTRINGS DO GITHUB".center(LINE_WIDTH))
    print(DELIMITER_CHAR * LINE_WIDTH)
    print("\n")
    global_start_time = time.time()

    total_files_scanned = 0
    total_extraction_errors = 0

    db_dir = os.path.dirname(DATABASE_NAME)
    os.makedirs(db_dir, exist_ok=True)

    for repo_info in github_repos_to_collect:
        repo_files_scanned, repo_extraction_errors = clone_and_extract_from_github(
            repo_info)
        total_files_scanned += repo_files_scanned
        total_extraction_errors += repo_extraction_errors

    global_end_time = time.time()
    global_formated_time = time_format(global_end_time - global_start_time)

    print(DELIMITER_CHAR * LINE_WIDTH)
    print("COLETA DE DOCSTRINGS CONCLUÍDA".center(LINE_WIDTH))
    print(DELIMITER_CHAR * LINE_WIDTH)
    print("\n" * 2)

    print(f"Os repositórios clonados estão na pasta '{CLONED_REPO_DIR}'.\n".center(
        LINE_WIDTH))

    print(DELIMITER_CHAR_LIGHT * LINE_WIDTH)
    print("RELATÓRIO DE KPIS".center(LINE_WIDTH))
    print(DELIMITER_CHAR_LIGHT * LINE_WIDTH)
    print(f"Tempo total de coleta: {global_formated_time}".center(
        LINE_WIDTH))
    print(
        f"Total de arquivos escaneados: {total_files_scanned}".center(LINE_WIDTH))
    print(
        f"Total de erros de extração: {total_extraction_errors}".center(LINE_WIDTH))
    print(DELIMITER_CHAR_LIGHT * LINE_WIDTH)
    print("\n")

    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM docstrings;")
        total_docstrings_collected = cursor.fetchone()[0]
        print(f"Total de docstrings coletados no banco de dados: {total_docstrings_collected}\n".center(
            LINE_WIDTH))
    except Exception as e:
        print(f"Erro ao consultar o número total de docstrings no banco de dados: {e}\n".center(
            LINE_WIDTH))
    finally:
        if conn:
            conn.close()

    print(DELIMITER_CHAR * LINE_WIDTH)
    print("AMOSTRA DOS DADOS COLETADOS".center(LINE_WIDTH))
    print(DELIMITER_CHAR * LINE_WIDTH)
    print("\n")

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            id,
            content,
            project_name,
            file_path,
            doc_type,
            object_name,
            style
        FROM docstrings
        LIMIT 10;""")
    print("Exibindo os primeiros 10 docstrings coletados:")
    for row in cursor.fetchall():
        doc_id, content, project_name, file_path, doc_type, object_name, style = row
        print(f"ID: {doc_id}, Projeto: {project_name}, Arquivo: {file_path}, Tipo: {doc_type}, Objeto: {object_name}, Estilo: {style if style else 'Não rotulado'}")
        print(f"  Docstring: \"{content[:70]}...\"")
    conn.close()
    print(f"\n{DELIMITER_CHAR * LINE_WIDTH}\n")
