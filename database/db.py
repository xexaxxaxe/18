from pathlib import Path
import sqlite3

def get_db():
    from flask import current_app, g
    if 'db' not in g:
        conn = sqlite3.connect(str(current_app.config['DB_PATH']), timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        g.db = conn
    return g.db

def close_db(error=None):
    from flask import g
    conn = g.pop('db', None)
    if conn is not None: conn.close()

def init_schema(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute('PRAGMA foreign_keys = ON')
        conn.executescript((Path(__file__).parent/'schema.sql').read_text(encoding='utf-8'))

def load_named_sql(name):
    sql = (Path(__file__).parent/'queries.sql').read_text(encoding='utf-8')
    tag = name + ':\n'
    if tag not in sql: raise ValueError('Missing SQL block')
    return sql.split(tag,1)[1].split('\n\n',1)[0].strip()
