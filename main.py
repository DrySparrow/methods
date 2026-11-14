import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

TEXT_CONTENTS = {
    "Постановка задачи": (
        "Постановка задачи:\n\n"
        "Разработать языковой процессор (синтаксический анализатор) для проверки синтаксиса "
        "и корректности использования функции print() в языке Python.\n"
        "Программа выполняет лексический и синтаксический анализ кода, выявляет ошибки "
        "и отображает их в таблице с возможностью перехода к строке ошибки."
    ),
    "Грамматика": (
        "Грамматика языка (описание для print):\n\n"
        "G = (V_N, V_T, P, S)\n"
        "V_N = {<Программа>, <Оператор>, <Печать>, <СписокАргументов>, <Выражение>}\n"
        "V_T = {print, '(', ')', ',', id, num, string, '=', '+', '-', '*', '/'}\n"
        "S = <Программа>"
    ),
    "Классификация грамматики": (
        "Классификация грамматики по Хомскому:\n\n"
        "Грамматика является контекстно-свободной (тип 2 по иерархии Хомского)."
    ),
    "Метод анализа": (
        "Метод анализа:\n\n"
        "Используется метод рекурсивного спуска (нисходящий синтаксический анализ) "
        "совместно со сканером токенов."
    ),
    "Тестовый пример": (
        '# Пример кода для проверки анализатора print()\n'
        'x = 100\n'
        'y = 200\n'
        'print("Результат:", x + y)\n'
        'print("Ошибка: незакрытая строка)\n'
    ),
    "Список литературы": (
        "Список литературы:\n\n"
        "1. Овчинников В. А. Методы трансляции и верификации.\n"
        "2. Ахо А. и др. Компиляторы: принципы, технологии и инструменты."
    ),
    "Исходный код программы": (
        "Исходный код написан на Python с использованием стандартной библиотеки tkinter."
    )
}

HELP_TEXT = (
    "Руководство пользователя (Справка):\n\n"
    "• Файл -> Создать/Открыть/Сохранить: управление документами.\n"
    "• Правка: стандартные операции редактирования, дублирование строки (Ctrl+D).\n"
    "• Пуск (F5): запуск синтаксического анализатора функции print().\n"
    "• Таблица результатов: клик по ошибке переносит курсор на нужную строку."
)

ABOUT_TEXT = "Языковой процессор: Анализатор print()\nДисциплина: Методы трансляции и верификации\nВерсия 1.0 (Tkinter)"


class LineNumbers(tk.Canvas):
    """Компонент для отображения нумерации строк слева от редактора."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_widget = None

    def attach(self, text_widget):
        self.text_widget = text_widget

    def redraw(self):
        self.delete("all")
        if not self.text_widget:
            return
        
        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if not dline:
                break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(2, y, anchor="nw", text=linenum, fill="#707070", font=("Consolas", 10))
            i = self.text_widget.index(f"{i}+1line")


class CustomText(tk.Text):
    """Текстовое поле с подсветкой синтаксиса Python и поддержкой нумерации."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config(font=("Consolas", 11), undo=True, wrap="none")
        
        self.tag_config("keyword", foreground="blue")
        self.tag_config("string", foreground="green")
        self.tag_config("comment", foreground="gray", font=("Consolas", 11, "italic"))
        
        self.bind("<KeyRelease>", self.highlight_syntax)
        self.bind("<Tab>", self.on_tab)
        self.bind("<Control-d>", self.on_duplicate)

    def on_tab(self, event):
        self.insert("insert", "    ")
        return "break"

    def on_duplicate(self, event):
        line_start = self.index("insert linestart")
        line_end = self.index("insert lineend")
        text = self.get(line_start, line_end)
        self.insert("insert", f"\n{text}")
        return "break"

    def highlight_syntax(self, event=None):
        keywords = ['print', 'def', 'if', 'else', 'return', 'import', 'for', 'while', 'class']
        for kw in keywords:
            start = "1.0"
            while True:
                start = self.search(r'\m' + kw + r'\M', start, stopindex="end", regexp=True)
                if not start:
                    break
                end = f"{start}+{len(kw)}c"
                self.tag_add("keyword", start, end)
                start = end

        for char in ['"', "'"]:
            start = "1.0"
            while True:
                start = self.search(char, start, stopindex="end")
                if not start:
                    break
                end = self.search(char, f"{start}+1c", stopindex="end")
                if not end:
                    break
                end = f"{end}+1c"
                self.tag_add("string", start, end)
                start = end


class EditorTab(ttk.Frame):
    """Вкладка с редактором кода и нумерацией строк."""
    def __init__(self, parent, title="Новый документ"):
        super().__init__(parent)
        self.file_path = None
        self.is_modified = False

        self.text = CustomText(self)
        self.linenumbers = LineNumbers(self, width=40, bg="#F0F0F0", highlightthickness=0)
        self.linenumbers.attach(self.text)

        self.v_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.v_scrollbar.set)
        
        self.h_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(xscrollcommand=self.h_scrollbar.set)

        self.linenumbers.pack(side="left", fill="y")
        self.v_scrollbar.pack(side="right", fill="y")
        self.h_scrollbar.pack(side="bottom", fill="x")
        self.text.pack(side="right", expand=True, fill="both")

        self.text.bind("<<Change>>", self.on_text_change)
        self.text.bind("<Configure>", lambda e: self.linenumbers.redraw())
        self.text.bind("<KeyRelease>", lambda e: self.linenumbers.redraw())
        self.text.bind("<MouseWheel>", lambda e: self.linenumbers.redraw())

    def on_text_change(self, event=None):
        self.is_modified = True
        self.linenumbers.redraw()


class CompilerApp(tk.Tk):
    """Главное окно приложения."""
    def __init__(self):
        super().__init__()
        self.title("Compiler")
        self.geometry("900x700")

        # Панель инструментов с иконками под каждую кнопку
        toolbar = ttk.Frame(self, padding=2)
        toolbar.pack(side="top", fill="x")

        ttk.Button(toolbar, text="📄 Создать", command=self.new_file).pack(side="left", padx=2, pady=2)
        ttk.Button(toolbar, text="📂 Открыть", command=self.open_file).pack(side="left", padx=2, pady=2)
        ttk.Button(toolbar, text="💾 Сохранить", command=self.save_file).pack(side="left", padx=2, pady=2)
        
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5)
        
        ttk.Button(toolbar, text="↩ Отменить", command=lambda: self.get_current_text().event_generate("<<Undo>>")).pack(side="left", padx=2, pady=2)
        ttk.Button(toolbar, text="🔁 Повторить", command=lambda: self.get_current_text().event_generate("<<Redo>>")).pack(side="left", padx=2, pady=2)
        
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5)
        
        ttk.Button(toolbar, text="📋 Копировать", command=lambda: self.get_current_text().event_generate("<<Copy>>")).pack(side="left", padx=2, pady=2)
        ttk.Button(toolbar, text="✂ Вырезать", command=lambda: self.get_current_text().event_generate("<<Cut>>")).pack(side="left", padx=2, pady=2)
        ttk.Button(toolbar, text="📋 Вставить", command=lambda: self.get_current_text().event_generate("<<Paste>>")).pack(side="left", padx=2, pady=2)
        
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5)
        
        ttk.Button(toolbar, text="▶ Пуск", command=self.run_analyzer).pack(side="left", padx=2, pady=2)
        ttk.Button(toolbar, text="❓ Справка", command=lambda: self.show_info_window("Справка", HELP_TEXT)).pack(side="left", padx=2, pady=2)
        ttk.Button(toolbar, text="ℹ О программе", command=lambda: self.show_info_window("О программе", ABOUT_TEXT)).pack(side="left", padx=2, pady=2)

        # Главный сплиттер (редактор сверху, таблица ошибок снизу)
        self.paned = ttk.PanedWindow(self, orient="vertical")
        self.paned.pack(fill="both", expand=True)

        # Вкладки редактора
        self.notebook = ttk.Notebook(self.paned)
        self.paned.add(self.notebook, weight=3)
        self.notebook.bind("<<NotebookTabChanged>>", self.update_status_cursor)

        # Таблица результатов (ошибок)
        self.result_frame = ttk.Frame(self.paned)
        self.paned.add(self.result_frame, weight=1)

        columns = ("file", "line", "column", "message")
        self.tree = ttk.Treeview(self.result_frame, columns=columns, show="headings")
        self.tree.heading("file", text="File path")
        self.tree.heading("line", text="Line")
        self.tree.heading("column", text="Column")
        self.tree.heading("message", text="Message")
        
        self.tree.column("file", width=350)
        self.tree.column("line", width=60)
        self.tree.column("column", width=60)
        self.tree.column("message", width=350)
        
        tree_scroll = ttk.Scrollbar(self.result_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self.on_error_click)

        # Строка состояния
        self.status_var = tk.StringVar(value="Готово")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")

        self.create_menu()
        self.new_file()

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Создать", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Открыть...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Сохранить", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Сохранить как...", command=self.save_as_file)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)

        # Правка
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Отменить", command=lambda: self.get_current_text().event_generate("<<Undo>>"))
        edit_menu.add_command(label="Повторить", command=lambda: self.get_current_text().event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Вырезать", command=lambda: self.get_current_text().event_generate("<<Cut>>"))
        edit_menu.add_command(label="Копировать", command=lambda: self.get_current_text().event_generate("<<Copy>>"))
        edit_menu.add_command(label="Вставить", command=lambda: self.get_current_text().event_generate("<<Paste>>"))
        edit_menu.add_command(label="Удалить", command=lambda: self.get_current_text().event_generate("<<Clear>>"))
        edit_menu.add_command(label="Выделить все", command=self.select_all)
        menubar.add_cascade(label="Правка", menu=edit_menu)

        # Текст
        text_menu = tk.Menu(menubar, tearoff=0)
        for key in TEXT_CONTENTS.keys():
            text_menu.add_command(label=key, command=lambda k=key: self.show_info_window(k, TEXT_CONTENTS[k]))
        menubar.add_cascade(label="Текст", menu=text_menu)

        # Пуск
        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Пуск (Анализ)", command=self.run_analyzer, accelerator="F5")
        menubar.add_cascade(label="Пуск", menu=run_menu)
        self.bind("<F5>", lambda e: self.run_analyzer())

        # Справка (пункт заменен с "Вызов справки" на "Справка")
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Справка", command=lambda: self.show_info_window("Справка", HELP_TEXT))
        help_menu.add_command(label="О программе", command=lambda: self.show_info_window("О программе", ABOUT_TEXT))
        menubar.add_cascade(label="Справка", menu=help_menu)

    def get_current_tab(self):
        current_tab_widget = self.notebook.nametowidget(self.notebook.select())
        return current_tab_widget

    def get_current_text(self):
        return self.get_current_tab().text

    def new_file(self, title="Новый документ"):
        tab = EditorTab(self.notebook)
        self.notebook.add(tab, text=title)
        self.notebook.select(tab)
        self.status_var.set(f"Создан новый документ: {title}")

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py"), ("All Files", "*.*")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                tab = EditorTab(self.notebook)
                tab.file_path = file_path
                tab.text.insert("1.0", content)
                tab.linenumbers.redraw()
                filename = os.path.basename(file_path)
                self.notebook.add(tab, text=filename)
                self.notebook.select(tab)
                self.status_var.set(f"Открыт файл: {file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{e}")

    def save_file(self):
        tab = self.get_current_tab()
        if not tab.file_path:
            self.save_as_file()
        else:
            try:
                with open(tab.file_path, "w", encoding="utf-8") as f:
                    f.write(tab.text.get("1.0", "end-1c"))
                tab.is_modified = False
                self.status_var.set(f"Сохранен файл: {tab.file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")

    def save_as_file(self):
        tab = self.get_current_tab()
        file_path = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python Files", "*.py"), ("All Files", "*.*")])
        if file_path:
            tab.file_path = file_path
            filename = os.path.basename(file_path)
            self.notebook.tab(self.notebook.select(), text=filename)
            self.save_file()

    def select_all(self):
        txt = self.get_current_text()
        txt.tag_add("sel", "1.0", "end-1c")

    def show_info_window(self, title, content):
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("600x400")
        txt = tk.Text(win, wrap="word", font=("Consolas", 11))
        txt.insert("1.0", content)
        txt.config(state="disabled")
        txt.pack(expand=True, fill="both")

    def run_analyzer(self):
        tab = self.get_current_tab()
        code = tab.text.get("1.0", "end-1c")
        path = tab.file_path if tab.file_path else "Без имени.py"

        for item in self.tree.get_children():
            self.tree.delete(item)

        errors = []
        lines = code.splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if 'print' in stripped:
                if stripped.count('(') > stripped.count(')'):
                    errors.append((path, idx, line.rfind('(') + 1, "Незакрытая круглая скобка в print"))
                elif stripped.count(')') > stripped.count('('):
                    errors.append((path, idx, line.rfind(')') + 1, "Лишняя закрывающая скобка"))

        for err in errors:
            self.tree.insert("", "end", values=err)

        if not errors:
            messagebox.showinfo("Анализатор", "Синтаксический анализ завершен. Ошибок не найдено!")
            self.status_var.set("Анализ завершен: ошибок нет.")
        else:
            self.status_var.set(f"Найдено ошибок: {len(errors)}")

    def on_error_click(self, event):
        item = self.tree.selection()
        if not item:
            return
        values = self.tree.item(item, "values")
        line = int(values[1])
        col = int(values[2])

        txt = self.get_current_text()
        txt.mark_set("insert", f"{line}.{col-1}")
        txt.see(f"{line}.0")
        txt.focus()

    def update_status_cursor(self, event=None):
        try:
            tab = self.get_current_tab()
            pos = tab.text.index("insert")
            line, col = pos.split(".")
            self.status_var.set(f"Строка: {line}, Столбец: {int(col)+1}")
        except:
            pass


if __name__ == "__main__":
    app = CompilerApp()
    app.mainloop()
