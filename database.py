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
        
    def import_translations_from_entries(self, old_entries):
        """
        Import translations from old entries into current database.
        
        When importing from an exported translated file, the old file's text 
        is actually the translated text (since export replaces orig with trans).
        We match entries by (classid, no) and treat the old entry's orig_text
        as the translation to import.
        
        Args:
            old_entries: List of TextEntry objects from old translation file
            
        Returns:
            Dictionary with statistics: matched_by_id, not_matched
        """
        stats = {
            'matched_by_id': 0,
            'not_matched': 0
        }
        
        for old_entry in old_entries:
            # Try to match by (classid, no)
            self.cursor.execute('''
                SELECT classid, no, orig_text, trans_text FROM translations
                WHERE classid = ? AND no = ?
            ''', (old_entry.classid, old_entry.no))
            
            result = self.cursor.fetchone()
            if result:
                current_orig = result[2]
                current_trans = result[3]
                
                # The old entry's orig_text is actually the translation
                # Only import if:
                # 1. The old text differs from current orig (meaning it was translated)
                # 2. OR the old entry has trans_text set
                old_text = old_entry.trans_text if old_entry.trans_text else old_entry.orig_text
                
                # If the old text is the same as current orig, skip (not translated)
                if old_text != current_orig:
                    # Update translation only if current entry is not yet translated
                    # or if we want to overwrite (let's preserve existing translations)
                    if not current_trans:
                        self.cursor.execute('''
                            UPDATE translations
                            SET trans_text = ?
                            WHERE classid = ? AND no = ?
                        ''', (old_text, old_entry.classid, old_entry.no))
                        stats['matched_by_id'] += 1
                    else:
                        # Already translated, count as matched but don't overwrite
                        stats['matched_by_id'] += 1
                else:
                    # Same as original, not a translation
                    stats['not_matched'] += 1
            else:
                stats['not_matched'] += 1
        
        self.conn.commit()
        return stats
    
    def search_by_original(self, search_text):
        """
        Search for entries by original text.
        
        Args:
            search_text: Text to search for in orig_text
            
        Returns:
            List of TextEntry objects matching the search
        """
        self.cursor.execute('''
            SELECT classname, classid, no, orig_text, trans_text
            FROM translations
            WHERE orig_text LIKE ?
            ORDER BY classid, no
        ''', (f'%{search_text}%',))
        
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
    
    def search_by_translation(self, search_text):
        """
        Search for entries by translated text.
        
        Args:
            search_text: Text to search for in trans_text
            
        Returns:
            List of TextEntry objects matching the search
        """
        self.cursor.execute('''
            SELECT classname, classid, no, orig_text, trans_text
            FROM translations
            WHERE trans_text LIKE ?
            ORDER BY classid, no
        ''', (f'%{search_text}%',))
        
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
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
