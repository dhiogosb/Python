import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
import threading
import pystray
from PIL import Image, ImageDraw


# =========================
# DATABASE MANAGER
# =========================
class DatabaseManager:
    def __init__(self, db_name="database.db"):
        self.conn = sqlite3.connect(db_name)

    def create_table_from_df(self, table_name, df):
        df.to_sql(table_name, self.conn, if_exists="replace", index=False)

    def get_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [row[0] for row in cursor.fetchall()]

    def get_columns(self, table):
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        return [col[1] for col in cursor.fetchall()]

    def search(self, table, column, value):
        query = f"""
            SELECT * FROM {table}
            WHERE {column} LIKE ?
            LIMIT 500
        """
        return pd.read_sql_query(query, self.conn, params=(f"%{value}%",))


# =========================
# DATA IMPORTER
# =========================
class DataImporter:
    @staticmethod
    def import_file(db_manager):
        file_path = filedialog.askopenfilename(
            filetypes=[("Data files", "*.csv *.txt")]
        )

        if not file_path:
            return None

        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_csv(file_path, delimiter=";")

        table_name = os.path.splitext(os.path.basename(file_path))[0]
        table_name = table_name.replace("-", "_").replace(" ", "_")

        db_manager.create_table_from_df(table_name, df)
        return table_name


# =========================
# TRAY MANAGER
# =========================
class TrayManager:
    def __init__(self, root):
        self.root = root
        self.icon = None

    def create_image(self):
        image = Image.new('RGB', (64, 64), color=(40, 40, 40))
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill=(0, 150, 255))
        return image

    def show_window(self, icon, item):
        self.root.after(0, self.root.deiconify)
        icon.stop()

    def quit_app(self, icon, item):
        icon.stop()
        self.root.destroy()

    def minimize_to_tray(self):
        self.root.withdraw()
        image = self.create_image()

        menu = pystray.Menu(
            pystray.MenuItem("Abrir", self.show_window),
            pystray.MenuItem("Sair", self.quit_app)
        )

        self.icon = pystray.Icon("RTF", image, "RTF Tool", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()


# =========================
# APP UI
# =========================
class AppUI:
    def __init__(self, root):
        self.root = root
        self.db = DatabaseManager()
        self.tray = TrayManager(root)
        self.last_df = pd.DataFrame()

        self.setup_ui()
        self.load_tables()

    def setup_ui(self):
        self.root.title("RTF - Reader Text File")
        self.root.geometry("1100x650")

        style = ttk.Style()
        style.theme_use("clam")

        frame = ttk.Frame(self.root)
        frame.pack(padx=15, pady=15, fill="x")

        self.import_btn = ttk.Button(
            frame, text="Importar CSV/TXT",
            command=self.import_data
        )
        self.import_btn.grid(row=0, column=0, padx=5)

        self.selected_table = tk.StringVar()
        self.table_menu = ttk.Combobox(
            frame, textvariable=self.selected_table, width=25
        )
        self.table_menu.grid(row=0, column=1, padx=5)
        self.table_menu.bind("<<ComboboxSelected>>", self.load_columns)

        self.selected_column = tk.StringVar()
        self.column_menu = ttk.Combobox(
            frame, textvariable=self.selected_column, width=25
        )
        self.column_menu.grid(row=0, column=2, padx=5)

        self.search_entry = ttk.Entry(frame, width=30)
        self.search_entry.grid(row=0, column=3, padx=5)

        self.search_btn = ttk.Button(
            frame, text="Pesquisar",
            command=self.search_data
        )
        self.search_btn.grid(row=0, column=4, padx=5)

        self.export_btn = ttk.Button(
            frame, text="Exportar Excel",
            command=self.export_data
        )
        self.export_btn.grid(row=0, column=5, padx=5)

        self.tree = ttk.Treeview(self.root, show="headings")
        self.tree.pack(fill="both", expand=True, padx=15, pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.tray.minimize_to_tray)

    def import_data(self):
        table_name = DataImporter.import_file(self.db)
        if table_name:
            messagebox.showinfo("Sucesso", f"Tabela '{table_name}' criada!")
            self.load_tables()

    def load_tables(self):
        tables = self.db.get_tables()
        self.table_menu["values"] = tables
        if tables:
            self.table_menu.current(0)
            self.load_columns()

    def load_columns(self, event=None):
        table = self.selected_table.get()
        columns = self.db.get_columns(table)

        self.column_menu["values"] = columns
        if columns:
            self.column_menu.current(0)

        self.tree["columns"] = columns
        self.tree.delete(*self.tree.get_children())

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

    def search_data(self):
        table = self.selected_table.get()
        column = self.selected_column.get()
        value = self.search_entry.get()

        self.last_df = self.db.search(table, column, value)

        self.tree.delete(*self.tree.get_children())
        for _, row in self.last_df.iterrows():
            self.tree.insert("", "end", values=list(row))

    def export_data(self):
        if self.last_df.empty:
            messagebox.showwarning("Aviso", "Nenhum dado para exportar.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )

        if file_path:
            self.last_df.to_excel(file_path, index=False)
            messagebox.showinfo("Sucesso", "Exportado com sucesso!")


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    root = tk.Tk()
    app = AppUI(root)
    root.mainloop()
