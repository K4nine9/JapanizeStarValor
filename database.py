"""
Database module for storing and managing translations.
Uses SQLite for simplicity and portability.
"""
import sqlite3
from text_parser import TextEntry


class TranslationDB:
    """Manages the translation database."""
    
    def __init__(self, db_path='translations.db'):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to the database and create tables if needed."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()
        
    def _create_tables(self):
        """Create the translations table if it doesn't exist."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                classname TEXT NOT NULL,
                classid INTEGER NOT NULL,
                no TEXT NOT NULL,
                orig_text TEXT NOT NULL,
                trans_text TEXT DEFAULT '',
                UNIQUE(classid, no)
            )
        ''')
        self.conn.commit()
        
    def clear_all(self):
        """Clear all entries from the database."""
        self.cursor.execute('DELETE FROM translations')
        self.conn.commit()
        
    def insert_entry(self, entry):
        """
        Insert or update a translation entry.
        
        Args:
            entry: TextEntry object
        """
        self.cursor.execute('''
            INSERT OR REPLACE INTO translations 
            (classname, classid, no, orig_text, trans_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (entry.classname, entry.classid, entry.no, 
              entry.orig_text, entry.trans_text))
        self.conn.commit()
        
    def insert_entries(self, entries):
        """
        Insert multiple entries at once.
        
        Args:
            entries: List of TextEntry objects
        """
        for entry in entries:
            self.insert_entry(entry)
            
    def get_all_entries(self):
        """
        Retrieve all entries from the database.
        
        Returns:
            List of TextEntry objects
        """
        self.cursor.execute('''
            SELECT classname, classid, no, orig_text, trans_text
            FROM translations
            ORDER BY classid, no
        ''')
        
        entries = []
        for row in self.cursor.fetchall():
            entry = TextEntry(
                classname=row[0],
                classid=row[1],
                no=row[2],
                orig_text=row[3],
                trans_text=row[4]
            )
            entries.append(entry)
        
        return entries
    
    def get_entry_count(self):
        """Get the total number of entries."""
        self.cursor.execute('SELECT COUNT(*) FROM translations')
        return self.cursor.fetchone()[0]
    
    def get_translated_count(self):
        """Get the number of entries with translations."""
        self.cursor.execute(
            "SELECT COUNT(*) FROM translations WHERE trans_text != ''"
        )
        return self.cursor.fetchone()[0]
    
    def update_translation(self, classid, no, trans_text):
        """
        Update the translation for a specific entry.
        
        Args:
            classid: Class ID of the entry
            no: Entry number
            trans_text: Translated text
        """
        self.cursor.execute('''
            UPDATE translations
            SET trans_text = ?
            WHERE classid = ? AND no = ?
        ''', (trans_text, classid, no))
        self.conn.commit()
        
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
