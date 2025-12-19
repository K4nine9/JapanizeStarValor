"""
Star Valor ゲームテキスト翻訳 GUI アプリケーション
tkinter ベースの翻訳管理インターフェース
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from text_parser import TextParser
from database import TranslationDB


class TranslationApp:
    """翻訳アプリケーション GUIメインクラス"""
    
    def __init__(self, root):
        """
        翻訳アプリケーションを初期化
        
        Args:
            root: Tkinter ルートウィンドウ
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
        # Track last saved text to detect real changes (not programmatic updates)
        self._last_saved_text = ""
        # Suppress tree selection events when selecting programmatically
        self._suppress_tree_event = False
        
        # Create UI
        self._create_menu()
        self._create_ui()
        
        # データベースから項目を読み込む asynchronously after UI is ready
        self.root.after(100, self._async_load_from_db)
        
    def _create_menu(self):
        """アプリケーションメニューバーを作成"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="テキストファイルを読み込む", command=self.import_file)
        file_menu.add_command(label="過去の翻訳をインポート", command=self.import_previous_translation)
        file_menu.add_command(label="テキストファイルにエクスポート", command=self.export_file)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.on_closing)
        
        # 編集メニュー
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="編集", menu=edit_menu)
        edit_menu.add_command(label="検索", command=self.open_search_dialog)
        # 保存ショートカット (Ctrl+S)
        self.root.bind_all('<Control-s>', lambda e: self.save_current())
        
    def _create_ui(self):
        """メインユーザーインターフェースを作成"""
        # 上部フレーム（ファイル操作と統計情報）
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Button(top_frame, text="読み込み", command=self.import_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="保存", command=self.save_current).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="エクスポート", command=self.export_file).pack(side=tk.LEFT, padx=5)
        
        # ステータス表示
        self.save_status_label = ttk.Label(top_frame, text="", foreground="red")
        self.save_status_label.pack(side=tk.RIGHT, padx=5)
        self.stats_label = ttk.Label(top_frame, text="")
        self.stats_label.pack(side=tk.RIGHT, padx=10)
        
        # メインコンテンツフレーム
        content_frame = ttk.Frame(self.root, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # エントリ情報
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
        
        # 原文
        orig_frame = ttk.LabelFrame(content_frame, text="原文", padding="10")
        orig_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.orig_text = tk.Text(orig_frame, height=6, wrap=tk.WORD, font=('TkDefaultFont', 11))
        self.orig_text.pack(fill=tk.BOTH, expand=True)
        self.orig_text.config(state=tk.DISABLED, bg='#f0f0f0')
        
        # 翻訳
        trans_frame = ttk.LabelFrame(content_frame, text="翻訳", padding="10")
        trans_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.trans_text = tk.Text(trans_frame, height=6, wrap=tk.WORD, font=('TkDefaultFont', 11))
        self.trans_text.pack(fill=tk.BOTH, expand=True)
        self.trans_text.config(state=tk.NORMAL)
        self.trans_text.bind('<KeyRelease>', self.on_translation_changed)
        self.trans_text.bind('<Control-s>', lambda e: self.save_current())
        # Track pending save timer for debounced DB updates
        self._save_timer_id = None
        # Ensure clicks give focus to the translation text
        self.trans_text.bind('<Button-1>', lambda e: self.trans_text.focus_set())
        
        # ナビゲーションフレーム
        nav_frame = ttk.Frame(content_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(nav_frame, text="<<", command=self.first_entry, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="< 前へ", command=self.prev_entry, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="前の未翻訳", command=self.jump_to_untranslated_prev, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text=">>", command=self.last_entry, width=5).pack(side=tk.RIGHT, padx=2)
        ttk.Button(nav_frame, text="次へ >", command=self.next_entry, width=8).pack(side=tk.RIGHT, padx=2)
        ttk.Button(nav_frame, text="次の未翻訳", command=self.jump_to_untranslated, width=12).pack(side=tk.RIGHT, padx=2)

        
        self.entry_label = ttk.Label(nav_frame, text="0 / 0", font=('TkDefaultFont', 10, 'bold'))
        self.entry_label.pack(side=tk.BOTTOM, expand=True, padx=10)
        
        # エントリ一覧フレーム
        list_frame = ttk.LabelFrame(content_frame, text="エントリ一覧", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview用スクロールバー
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
        
        # 詳細財算の一貫処理を下部で実施
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_closing(self):
        """Handle application closing."""
        try:
            # Check if current text differs from last saved version
            current_text = self.trans_text.get('1.0', 'end-1c') if self.entries else ""
            if current_text != self._last_saved_text:
                should_save = messagebox.askyesno(
                    "未保存の変更",
                    "変更が保存されていません保存しますか？"
                )
                if should_save:
                    self.save_current()
        finally:
            self.db.close()
            self.root.destroy()
    
    def _async_load_from_db(self):
        """Load entries from database asynchronously on startup."""
        # データベース内の項目数を確認
        entry_count = self.db.get_entry_count()
        
        if entry_count == 0:
            # エントリがなければ表示を更新するだけ
            self.update_display()
            self.update_stats()
            return
        
        # 読み込み用進捗ダイアログを表示
        progress = ProgressDialog(self.root, "起動中")
        
        def load_thread():
            # このスレッド用に新しい DB 接続を作成
            thread_db = TranslationDB(self.db.db_path)
            thread_db.connect()
            
            try:
                progress.update_status("データベースから読み込み中...", f"{entry_count}個のエントリ")
                
                # データベースから項目を読み込む
                entries = thread_db.get_all_entries()
                
                # メインスレッドで更新
                self.root.after(0, self._finalize_startup_load, entries, progress)
                
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: [
                    progress.close(),
                    messagebox.showerror("エラー", f"データベースの読み込みに失敗しました:\n{error_msg}")
                ])
            finally:
                thread_db.close()
        
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
    
    def _finalize_startup_load(self, entries, progress):
        """Finalize startup loading on main thread."""
        try:
            progress.update_status("表示を更新中...")
            
            self.entries = entries
            self.current_index = 0
            
            # Update display first (faster)
            self.update_display()
            self.update_stats()
            
            progress.close()
            
            # Update tree in background to avoid blocking
            self.root.after(10, self.update_tree)
        except Exception as e:
            progress.close()
            messagebox.showerror("エラー", f"表示の更新に失敗しました:\n{str(e)}")
        
    def import_file(self):
        """Import a text file and load into database."""
        filepath = filedialog.askopenfilename(
            title="テキストファイルを選択",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        # Show progress dialog
        progress = ProgressDialog(self.root, "ファイル読み込み中")
        
        # Run import in separate thread
        def import_thread():
            # このスレッド用に新しい DB 接続を作成
            thread_db = TranslationDB(self.db.db_path)
            thread_db.connect()
            
            try:
                progress.update_status("ファイルを解析中...")
                
                # Parse the file
                parser = TextParser()
                entries = parser.parse_file(filepath)
                
                if not entries:
                    self.root.after(0, lambda: [
                        progress.close(),
                        messagebox.showwarning("警告", "エントリが見つかりませんでした")
                    ])
                    thread_db.close()
                    return
                
                progress.update_status("データベースをクリア中...", f"{len(entries)}個のエントリを処理")
                
                # Clear existing data and insert new entries
                thread_db.clear_all()
                
                progress.set_determinate(len(entries))
                progress.update_status("エントリをデータベースに保存中...")
                
                # Bulk insert with progress updates
                thread_db.insert_entries_bulk(entries, 
                    progress_callback=lambda i, total: progress.update_progress(i))
                
                progress.update_status("表示を更新中...")
                
                # Reload from database (on main thread)
                self.root.after(0, self._finalize_import, entries, progress)
                
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: [
                    progress.close(),
                    messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました:\n{error_msg}")
                ])
            finally:
                thread_db.close()
        
        thread = threading.Thread(target=import_thread, daemon=True)
        thread.start()
    
    def _finalize_import(self, entries, progress):
        """Finalize import on main thread."""
        try:
            self.load_from_db()
            progress.close()
            messagebox.showinfo("成功", f"{len(entries)}個のエントリを読み込みました")
        except Exception as e:
            progress.close()
            messagebox.showerror("エラー", f"表示の更新に失敗しました:\n{str(e)}")
    
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
            messagebox.showwarning("警告", "先に現在の翻訳対象ファイルを読み込んでください")
            return
        
        # Show progress dialog
        progress = ProgressDialog(self.root, "翻訳インポート中")
        
        def import_thread():
            # このスレッド用に新しい DB 接続を作成
            thread_db = TranslationDB(self.db.db_path)
            thread_db.connect()
            
            try:
                progress.update_status("ファイルを解析中...")
                
                # Parse the old translation file
                parser = TextParser()
                old_entries = parser.parse_file(filepath)
                
                if not old_entries:
                    self.root.after(0, lambda: [
                        progress.close(),
                        messagebox.showwarning("警告", "エントリが見つかりませんでした")
                    ])
                    thread_db.close()
                    return
                
                progress.set_determinate(len(old_entries))
                progress.update_status("翻訳をインポート中...", f"{len(old_entries)}個のエントリを処理")
                
                # Import translations with progress
                stats = thread_db.import_translations_from_entries_bulk(old_entries,
                    progress_callback=lambda i, total: progress.update_progress(i))
                
                progress.update_status("表示を更新中...")
                
                # Reload and show results (on main thread)
                self.root.after(0, self._finalize_translation_import, stats, progress)
                
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: [
                    progress.close(),
                    messagebox.showerror("エラー", f"インポートに失敗しました:\n{error_msg}")
                ])
            finally:
                thread_db.close()
        
        thread = threading.Thread(target=import_thread, daemon=True)
        thread.start()
    
    def _finalize_translation_import(self, stats, progress):
        """Finalize translation import on main thread."""
        try:
            self.load_from_db()
            progress.close()
            
            msg = (
                f"インポート結果:\n\n"
                f"インポート: {stats['matched_by_id']}件\n"
                f"未一致: {stats['not_matched']}件"
            )
            messagebox.showinfo("インポート完了", msg)
        except Exception as e:
            progress.close()
            messagebox.showerror("エラー", f"表示の更新に失敗しました:\n{str(e)}")
            
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
                messagebox.showwarning("警告", "エクスポートするデータがありません")
                return
            
            # Export to file
            parser = TextParser()
            parser.export_to_file(entries, filepath)
            
            messagebox.showinfo("成功", f"{len(entries)}個のエントリをエクスポートしました")
            
        except Exception as e:
            messagebox.showerror("エラー", f"エクスポートに失敗しました:\n{str(e)}")
            
    def load_from_db(self):
        """Load all entries from database."""
        self.entries = self.db.get_all_entries()
        self.current_index = 0
        self.update_display()
        self.update_stats()
        # Defer tree update to avoid blocking
        self.root.after(10, self.update_tree)
        
    def update_display(self):
        """Update the display with current entry."""
        if not self.entries:
            self.class_label.config(text="")
            self.no_label.config(text="")
            self.orig_text.config(state=tk.NORMAL)
            self.orig_text.delete('1.0', tk.END)
            self.orig_text.config(state=tk.DISABLED)
            # Ensure translation text is editable
            self.trans_text.config(state=tk.NORMAL)
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
        self.trans_text.config(state=tk.NORMAL)
        self.trans_text.delete('1.0', tk.END)
        if entry.trans_text:
            self.trans_text.insert('1.0', entry.trans_text)
        # Store snapshot of current text (no unsaved changes yet)
        self._last_saved_text = entry.trans_text
        # Keep focus on translation field for smooth typing
        try:
            self.trans_text.focus_set()
        except Exception:
            pass
        
        # Update entry counter
        self.entry_label.config(text=f"{self.current_index + 1} / {len(self.entries)}")
        
        # Defer tree highlight to avoid blocking navigation
        if hasattr(self, '_highlight_id'):
            self.root.after_cancel(self._highlight_id)
        self._highlight_id = self.root.after(50, self.highlight_current_in_tree)
        
    def update_tree(self):
        """Update the entry list tree."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add entries in batches for better performance
        batch_size = 200
        for i in range(0, len(self.entries), batch_size):
            batch_end = min(i + batch_size, len(self.entries))
            for j in range(i, batch_end):
                entry = self.entries[j]
                trans_preview = entry.trans_text[:30] if entry.trans_text else ""
                orig_preview = entry.orig_text[:30] if len(entry.orig_text) > 30 else entry.orig_text
                
                self.tree.insert('', tk.END, iid=str(j), values=(
                    f"[{entry.classid}] {entry.classname}",
                    entry.no,
                    orig_preview,
                    trans_preview
                ))
            
            # Allow UI to update less frequently to avoid blocking
            if batch_end < len(self.entries) and i % 400 == 0:
                self.root.update_idletasks()
            
    def highlight_current_in_tree(self):
        """Highlight the current entry in the tree."""
        if self.entries:
            try:
                # Check if the item exists in the tree
                if self.tree.exists(str(self.current_index)):
                    # Prevent recursive selection -> on_tree_select -> update_display loops
                    self._suppress_tree_event = True
                    self.tree.selection_set(str(self.current_index))
                    # Re-enable event handling after idle
                    self.root.after(0, lambda: setattr(self, '_suppress_tree_event', False))
            except:
                pass  # Ignore errors if tree is not yet updated
            
    def update_stats(self):
        """Update statistics display."""
        total = self.db.get_entry_count()
        translated = self.db.get_translated_count()
        percentage = (translated / total * 100) if total > 0 else 0
        
        self.stats_label.config(
            text=f"翻訳済み: {translated} / {total} ({percentage:.1f}%)"
        )
        
    def on_translation_changed(self, event=None):
        """Update list preview and unsaved status indicator on text change."""
        if not self.entries:
            return
        
        # Get current text
        trans_text = self.trans_text.get('1.0', 'end-1c')
        
        # Update unsaved indicator based on comparison with last saved
        if trans_text != self._last_saved_text:
            try:
                self.save_status_label.config(text="未保存の変更あり", foreground="red")
            except Exception:
                pass
        else:
            try:
                self.save_status_label.config(text="")
            except Exception:
                pass
        
        # Update Treeview preview for current entry
        try:
            if self.tree.exists(str(self.current_index)):
                values = list(self.tree.item(str(self.current_index), 'values'))
                if len(values) == 4:
                    values[3] = trans_text[:30] if trans_text else ""
                    self.tree.item(str(self.current_index), values=values)
        except Exception:
            pass

    def save_current(self):
        """Manually save the current translation to the database."""
        if not self.entries:
            return
        entry = self.entries[self.current_index]
        trans_text = self.trans_text.get('1.0', 'end-1c')
        try:
            self.db.update_translation(entry.classid, entry.no, trans_text)
            entry.trans_text = trans_text
            # Store snapshot of saved text
            self._last_saved_text = trans_text
            
            # Show save success indicator
            try:
                self.save_status_label.config(text="保存しました", foreground="green")
                # Clear status after 1.5 seconds
                self.root.after(1500, lambda: self.save_status_label.config(text=""))
            except Exception:
                pass
            
            # Update stats with slight delay
            if hasattr(self, '_stats_update_id') and self._stats_update_id:
                try:
                    self.root.after_cancel(self._stats_update_id)
                except Exception:
                    pass
            self._stats_update_id = self.root.after(200, self.update_stats)
            
            # Ensure Treeview preview reflects saved text
            try:
                if self.tree.exists(str(self.current_index)):
                    values = list(self.tree.item(str(self.current_index), 'values'))
                    if len(values) == 4:
                        values[3] = trans_text[:30] if trans_text else ""
                        self.tree.item(str(self.current_index), values=values)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("エラー", f"保存に失敗しました:\n{str(e)}")
        
    def on_tree_select(self, event):
        """Handle tree selection."""
        # Ignore programmatic selection events
        if getattr(self, '_suppress_tree_event', False):
            return
        selection = self.tree.selection()
        if selection:
            index = int(selection[0])
            # Avoid redundant update when selecting the same item
            if index == self.current_index:
                return
            self.current_index = index
            self.update_display()
            
    def next_entry(self):
        """Navigate to next entry."""
        if self.current_index < len(self.entries) - 1:
            self.current_index += 1
            self.update_display()
            # Auto-scroll tree to show current entry
            self.root.after(0, self._auto_scroll_tree)
            
    def prev_entry(self):
        """Navigate to previous entry."""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()
            # Auto-scroll tree to show current entry
            self.root.after(0, self._auto_scroll_tree)
            
    def first_entry(self):
        """Navigate to first entry."""
        if self.entries:
            self.current_index = 0
            self.update_display()
            # Auto-scroll tree to show current entry
            self.root.after(0, self._auto_scroll_tree)
            
    def last_entry(self):
        """Navigate to last entry."""
        if self.entries:
            self.current_index = len(self.entries) - 1
            self.update_display()
            # Auto-scroll tree to show current entry
            self.root.after(0, self._auto_scroll_tree)
    
    def jump_to_untranslated(self):
        """Jump to the next untranslated entry."""
        if not self.entries:
            messagebox.showwarning("警告", "エントリがありません")
            return
        
        # Start searching from current position + 1
        start_index = (self.current_index + 1) % len(self.entries)
        
        for i in range(len(self.entries)):
            index = (start_index + i) % len(self.entries)
            entry = self.entries[index]
            
            # Check if entry is untranslated:
            # - Original text is not empty AND translation is empty
            if entry.orig_text.strip() and not entry.trans_text.strip():
                self.current_index = index
                self.update_display()
                # Auto-scroll tree to show current entry
                self.root.after(0, self._auto_scroll_tree)
                return
        
        messagebox.showinfo("情報", "すべてのエントリが翻訳済みです")
    
    def jump_to_untranslated_prev(self):
        """Jump to the previous untranslated entry."""
        if not self.entries:
            messagebox.showwarning("警告", "エントリがありません")
            return
        
        # Start searching from current position - 1 (backwards)
        start_index = (self.current_index - 1) % len(self.entries)
        
        for i in range(len(self.entries)):
            index = (start_index - i) % len(self.entries)
            entry = self.entries[index]
            
            # Check if entry is untranslated:
            # - Original text is not empty AND translation is empty
            if entry.orig_text.strip() and not entry.trans_text.strip():
                self.current_index = index
                self.update_display()
                # Auto-scroll tree to show current entry
                self.root.after(0, self._auto_scroll_tree)
                return
        
        messagebox.showinfo("情報", "すべてのエントリが翻訳済みです")
    
    def open_search_dialog(self):
        """Open the search dialog."""
        SearchDialog(self.root, self.db, self)
    
    def _auto_scroll_tree(self):
        """Auto-scroll tree to show current entry when navigating."""
        if self.entries and self.tree.exists(str(self.current_index)):
            try:
                self._suppress_tree_event = True
                self.tree.selection_set(str(self.current_index))
                self.tree.see(str(self.current_index))
                self.root.after(0, lambda: setattr(self, '_suppress_tree_event', False))
            except:
                pass


class ProgressDialog:
    """Progress dialog for showing long-running operations."""
    
    def __init__(self, parent, title="処理中..."):
        """Initialize the progress dialog."""
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (400 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (150 // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Prevent closing
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Create UI
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_label = ttk.Label(main_frame, text="準備中...", font=('TkDefaultFont', 10))
        self.status_label.pack(pady=(0, 10))
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=300)
        self.progress.pack(pady=10)
        self.progress.start(10)
        
        self.detail_label = ttk.Label(main_frame, text="", font=('TkDefaultFont', 9))
        self.detail_label.pack(pady=(10, 0))
        
    def update_status(self, status, detail=""):
        """Update the status message."""
        self.status_label.config(text=status)
        self.detail_label.config(text=detail)
        self.dialog.update()
        
    def set_determinate(self, maximum):
        """Switch to determinate progress bar."""
        self.progress.stop()
        self.progress.config(mode='determinate', maximum=maximum, value=0)
        
    def update_progress(self, value):
        """Update progress bar value."""
        self.progress.config(value=value)
        self.dialog.update()
        
    def close(self):
        """Close the dialog."""
        self.progress.stop()
        self.dialog.grab_release()
        self.dialog.destroy()


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
            messagebox.showwarning("警告", "検索語を入力してください", parent=self.dialog)
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
                messagebox.showinfo("検索結果", "一致するエントリが見つかりませんでした", parent=self.dialog)
                
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
