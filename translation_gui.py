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
        file_menu.add_command(label="過去の翻訳をインポート", command=self.import_previous_translation)
        file_menu.add_command(label="テキストファイルにエクスポート", command=self.export_file)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="編集", menu=edit_menu)
        edit_menu.add_command(label="検索", command=self.open_search_dialog)
        
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
    
    def import_previous_translation(self):
        """Import translations from a previously translated file."""
        filepath = filedialog.askopenfilename(
            title="過去の翻訳ファイルを選択",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        # Check if database has entries
        if self.db.get_entry_count() == 0:
            messagebox.showwarning("警告", "先に現在の翻訳対象ファイルを読み込んでください。")
            return
        
        try:
            # Parse the old translation file
            parser = TextParser()
            old_entries = parser.parse_file(filepath)
            
            if not old_entries:
                messagebox.showwarning("警告", "エントリが見つかりませんでした。")
                return
            
            # Import translations
            stats = self.db.import_translations_from_entries(old_entries)
            
            # Reload from database to reflect changes
            self.load_from_db()
            
            # Show import statistics
            msg = (
                f"インポート結果:\n\n"
                f"インポート: {stats['matched_by_id']}件\n"
                f"未一致: {stats['not_matched']}件"
            )
            messagebox.showinfo("インポート完了", msg)
            
        except Exception as e:
            messagebox.showerror("エラー", f"インポートに失敗しました:\n{str(e)}")
            
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
    
    def open_search_dialog(self):
        """Open the search dialog."""
        SearchDialog(self.root, self.db, self)


class SearchDialog:
    """Search dialog for finding entries by original or translated text."""
    
    def __init__(self, parent, db, main_app):
        """
        Initialize the search dialog.
        
        Args:
            parent: Parent window
            db: TranslationDB instance
            main_app: TranslationApp instance for navigation
        """
        self.db = db
        self.main_app = main_app
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("検索")
        self.dialog.geometry("700x500")
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_ui()
        
    def _create_ui(self):
        """Create the search dialog UI."""
        # Search frame
        search_frame = ttk.Frame(self.dialog, padding="10")
        search_frame.pack(fill=tk.X)
        
        ttk.Label(search_frame, text="検索:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind('<Return>', lambda e: self.perform_search())
        
        ttk.Button(search_frame, text="検索", command=self.perform_search).pack(side=tk.LEFT, padx=5)
        
        # Search type selection
        type_frame = ttk.Frame(self.dialog, padding="10")
        type_frame.pack(fill=tk.X)
        
        ttk.Label(type_frame, text="検索対象:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_type = tk.StringVar(value="original")
        ttk.Radiobutton(
            type_frame, 
            text="原文", 
            variable=self.search_type, 
            value="original"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            type_frame, 
            text="翻訳", 
            variable=self.search_type, 
            value="translation"
        ).pack(side=tk.LEFT, padx=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.dialog, text="検索結果", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Results count label
        self.count_label = ttk.Label(results_frame, text="")
        self.count_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Treeview for results
        tree_scroll = ttk.Scrollbar(results_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_tree = ttk.Treeview(
            results_frame,
            columns=('class', 'no', 'orig', 'trans'),
            show='headings',
            yscrollcommand=tree_scroll.set
        )
        tree_scroll.config(command=self.results_tree.yview)
        
        self.results_tree.heading('class', text='クラス')
        self.results_tree.heading('no', text='No')
        self.results_tree.heading('orig', text='原文')
        self.results_tree.heading('trans', text='翻訳')
        
        self.results_tree.column('class', width=120)
        self.results_tree.column('no', width=50)
        self.results_tree.column('orig', width=200)
        self.results_tree.column('trans', width=200)
        
        self.results_tree.pack(fill=tk.BOTH, expand=True)
        self.results_tree.bind('<Double-Button-1>', self.on_result_double_click)
        
        # Button frame
        button_frame = ttk.Frame(self.dialog, padding="10")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="閉じる", command=self.dialog.destroy).pack(side=tk.RIGHT)
        
    def perform_search(self):
        """Perform the search based on user input."""
        search_text = self.search_entry.get().strip()
        
        if not search_text:
            messagebox.showwarning("警告", "検索語を入力してください。", parent=self.dialog)
            return
        
        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Perform search
        try:
            if self.search_type.get() == "original":
                results = self.db.search_by_original(search_text)
            else:
                results = self.db.search_by_translation(search_text)
            
            # Display results
            for entry in results:
                orig_preview = entry.orig_text[:40] if len(entry.orig_text) > 40 else entry.orig_text
                trans_preview = entry.trans_text[:40] if entry.trans_text and len(entry.trans_text) > 40 else entry.trans_text
                
                self.results_tree.insert('', tk.END, values=(
                    f"[{entry.classid}] {entry.classname}",
                    entry.no,
                    orig_preview,
                    trans_preview
                ), tags=(entry.classid, entry.no))
            
            # Update count label
            self.count_label.config(text=f"{len(results)}件見つかりました")
            
            if len(results) == 0:
                messagebox.showinfo("検索結果", "一致するエントリが見つかりませんでした。", parent=self.dialog)
                
        except Exception as e:
            messagebox.showerror("エラー", f"検索に失敗しました:\n{str(e)}", parent=self.dialog)
    
    def on_result_double_click(self, event):
        """Handle double-click on a search result."""
        selection = self.results_tree.selection()
        if not selection:
            return
        
        # Get the classid and no from the selected item
        item = self.results_tree.item(selection[0])
        tags = item['tags']
        if len(tags) < 2:
            return
        
        classid = int(tags[0])
        no = tags[1]
        
        # Find the entry index in main app
        for i, entry in enumerate(self.main_app.entries):
            if entry.classid == classid and entry.no == no:
                self.main_app.current_index = i
                self.main_app.update_display()
                # Close the search dialog
                self.dialog.destroy()
                # Bring main window to front
                self.main_app.root.lift()
                break


def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = TranslationApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
