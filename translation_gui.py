"""
Translation GUI application for Star Valor game text.
Provides a tkinter-based interface for managing translations.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from text_parser import TextParser
from database import TranslationDB


class TranslationApp:
    """Main translation application GUI."""
    
    def __init__(self, root):
        """
        Initialize the translation application.
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("Star Valor Translation Tool")
        self.root.geometry("900x700")
        
        # Initialize database
        self.db = TranslationDB()
        self.db.connect()
        
        # Current entry data
        self.entries = []
        self.current_index = 0
        
        # Create UI
        self._create_menu()
        self._create_ui()
        
        # Load entries from database
        self.load_from_db()
        
    def _create_menu(self):
        """Create the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="テキストファイルを読み込む", command=self.import_file)
        file_menu.add_command(label="テキストファイルにエクスポート", command=self.export_file)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
        
    def _create_ui(self):
        """Create the main user interface."""
        # Top frame for file operations and stats
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Button(top_frame, text="読み込み", command=self.import_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="エクスポート", command=self.export_file).pack(side=tk.LEFT, padx=5)
        
        self.stats_label = ttk.Label(top_frame, text="")
        self.stats_label.pack(side=tk.RIGHT, padx=10)
        
        # Main content frame
        content_frame = ttk.Frame(self.root, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Entry info
        info_frame = ttk.LabelFrame(content_frame, text="エントリ情報", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=tk.X)
        
        ttk.Label(info_grid, text="クラス:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.class_label = ttk.Label(info_grid, text="", font=('TkDefaultFont', 10, 'bold'))
        self.class_label.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(info_grid, text="番号:").grid(row=0, column=2, sticky=tk.W, padx=(20, 5))
        self.no_label = ttk.Label(info_grid, text="", font=('TkDefaultFont', 10, 'bold'))
        self.no_label.grid(row=0, column=3, sticky=tk.W)
        
        # Original text
        orig_frame = ttk.LabelFrame(content_frame, text="原文", padding="10")
        orig_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.orig_text = tk.Text(orig_frame, height=6, wrap=tk.WORD, font=('TkDefaultFont', 11))
        self.orig_text.pack(fill=tk.BOTH, expand=True)
        self.orig_text.config(state=tk.DISABLED, bg='#f0f0f0')
        
        # Translation text
        trans_frame = ttk.LabelFrame(content_frame, text="翻訳", padding="10")
        trans_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.trans_text = tk.Text(trans_frame, height=6, wrap=tk.WORD, font=('TkDefaultFont', 11))
        self.trans_text.pack(fill=tk.BOTH, expand=True)
        self.trans_text.bind('<KeyRelease>', self.on_translation_changed)
        
        # Navigation frame
        nav_frame = ttk.Frame(content_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(nav_frame, text="<<", command=self.first_entry, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="< 前", command=self.prev_entry, width=8).pack(side=tk.LEFT, padx=2)
        
        self.entry_label = ttk.Label(nav_frame, text="0 / 0", font=('TkDefaultFont', 10, 'bold'))
        self.entry_label.pack(side=tk.LEFT, expand=True)
        
        ttk.Button(nav_frame, text="次 >", command=self.next_entry, width=8).pack(side=tk.RIGHT, padx=2)
        ttk.Button(nav_frame, text=">>", command=self.last_entry, width=5).pack(side=tk.RIGHT, padx=2)
        
        # List frame
        list_frame = ttk.LabelFrame(content_frame, text="エントリ一覧", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for entry list
        tree_scroll = ttk.Scrollbar(list_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            list_frame, 
            columns=('class', 'no', 'orig', 'trans'),
            show='headings',
            yscrollcommand=tree_scroll.set
        )
        tree_scroll.config(command=self.tree.yview)
        
        self.tree.heading('class', text='クラス')
        self.tree.heading('no', text='No')
        self.tree.heading('orig', text='原文')
        self.tree.heading('trans', text='翻訳')
        
        self.tree.column('class', width=150)
        self.tree.column('no', width=50)
        self.tree.column('orig', width=250)
        self.tree.column('trans', width=250)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        
        # Update display
        self.update_stats()
        
        # Ensure proper cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_closing(self):
        """Handle application closing."""
        self.db.close()
        self.root.destroy()
        
    def import_file(self):
        """Import a text file and load into database."""
        filepath = filedialog.askopenfilename(
            title="テキストファイルを選択",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            # Parse the file
            parser = TextParser()
            entries = parser.parse_file(filepath)
            
            if not entries:
                messagebox.showwarning("警告", "エントリが見つかりませんでした。")
                return
            
            # Clear existing data and insert new entries
            self.db.clear_all()
            self.db.insert_entries(entries)
            
            # Reload from database
            self.load_from_db()
            
            messagebox.showinfo("成功", f"{len(entries)}個のエントリを読み込みました。")
            
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました:\n{str(e)}")
            
    def export_file(self):
        """Export translations to a text file."""
        filepath = filedialog.asksaveasfilename(
            title="エクスポート先を選択",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            # Get all entries from database
            entries = self.db.get_all_entries()
            
            if not entries:
                messagebox.showwarning("警告", "エクスポートするデータがありません。")
                return
            
            # Export to file
            parser = TextParser()
            parser.export_to_file(entries, filepath)
            
            messagebox.showinfo("成功", f"{len(entries)}個のエントリをエクスポートしました。")
            
        except Exception as e:
            messagebox.showerror("エラー", f"エクスポートに失敗しました:\n{str(e)}")
            
    def load_from_db(self):
        """Load all entries from database."""
        self.entries = self.db.get_all_entries()
        self.current_index = 0
        self.update_tree()
        self.update_display()
        self.update_stats()
        
    def update_display(self):
        """Update the display with current entry."""
        if not self.entries:
            self.class_label.config(text="")
            self.no_label.config(text="")
            self.orig_text.config(state=tk.NORMAL)
            self.orig_text.delete('1.0', tk.END)
            self.orig_text.config(state=tk.DISABLED)
            self.trans_text.delete('1.0', tk.END)
            self.entry_label.config(text="0 / 0")
            return
        
        entry = self.entries[self.current_index]
        
        # Update labels
        self.class_label.config(text=f"[{entry.classid}] {entry.classname}")
        self.no_label.config(text=entry.no)
        
        # Update original text
        self.orig_text.config(state=tk.NORMAL)
        self.orig_text.delete('1.0', tk.END)
        self.orig_text.insert('1.0', entry.orig_text)
        self.orig_text.config(state=tk.DISABLED)
        
        # Update translation text
        self.trans_text.delete('1.0', tk.END)
        if entry.trans_text:
            self.trans_text.insert('1.0', entry.trans_text)
        
        # Update entry counter
        self.entry_label.config(text=f"{self.current_index + 1} / {len(self.entries)}")
        
        # Highlight current entry in tree
        self.highlight_current_in_tree()
        
    def update_tree(self):
        """Update the entry list tree."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add entries
        for i, entry in enumerate(self.entries):
            trans_preview = entry.trans_text[:30] if entry.trans_text else ""
            orig_preview = entry.orig_text[:30] if len(entry.orig_text) > 30 else entry.orig_text
            
            self.tree.insert('', tk.END, iid=str(i), values=(
                f"[{entry.classid}] {entry.classname}",
                entry.no,
                orig_preview,
                trans_preview
            ))
            
    def highlight_current_in_tree(self):
        """Highlight the current entry in the tree."""
        if self.entries:
            self.tree.selection_set(str(self.current_index))
            self.tree.see(str(self.current_index))
            
    def update_stats(self):
        """Update statistics display."""
        total = self.db.get_entry_count()
        translated = self.db.get_translated_count()
        percentage = (translated / total * 100) if total > 0 else 0
        
        self.stats_label.config(
            text=f"翻訳済み: {translated} / {total} ({percentage:.1f}%)"
        )
        
    def on_translation_changed(self, event=None):
        """Handle translation text changes."""
        if not self.entries:
            return
        
        entry = self.entries[self.current_index]
        trans_text = self.trans_text.get('1.0', tk.END).strip()
        
        # Update database
        self.db.update_translation(entry.classid, entry.no, trans_text)
        
        # Update entry object
        entry.trans_text = trans_text
        
        # Update tree
        self.tree.item(str(self.current_index), values=(
            f"[{entry.classid}] {entry.classname}",
            entry.no,
            entry.orig_text[:30],
            trans_text[:30]
        ))
        
        # Update stats
        self.update_stats()
        
    def on_tree_select(self, event):
        """Handle tree selection."""
        selection = self.tree.selection()
        if selection:
            index = int(selection[0])
            self.current_index = index
            self.update_display()
            
    def next_entry(self):
        """Navigate to next entry."""
        if self.current_index < len(self.entries) - 1:
            self.current_index += 1
            self.update_display()
            
    def prev_entry(self):
        """Navigate to previous entry."""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()
            
    def first_entry(self):
        """Navigate to first entry."""
        if self.entries:
            self.current_index = 0
            self.update_display()
            
    def last_entry(self):
        """Navigate to last entry."""
        if self.entries:
            self.current_index = len(self.entries) - 1
            self.update_display()


def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = TranslationApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
