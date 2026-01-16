
import sqlite3
from datetime import datetime

class GameCache:
    def __init__(self, db_path='~/.savenexus_cache.db'):
        self.conn = sqlite3.connect(os.path.expanduser(db_path))
        self._init_db()
    
    def _init_db(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS games (
                disc_id TEXT PRIMARY KEY,
                title TEXT,
                icon_path TEXT,
                last_scanned TIMESTAMP,
                save_path TEXT
            )
        ''')
    
    def get_cached_game(self, disc_id, save_path):
        """Return cached data if save folder hasn't changed"""
        row = self.conn.execute(
            'SELECT * FROM games WHERE disc_id = ?', (disc_id,)
        ).fetchone()
        
        if row:
            last_modified = os.path.getmtime(save_path)
            cached_time = datetime.fromisoformat(row[3])
            if last_modified < cached_time.timestamp():
                return dict(zip(['disc_id', 'title', 'icon_path', ...], row))
        return None
