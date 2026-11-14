# -*- coding: utf-8 -*-
"""
Основной файл графического интерфейса языкового процессора (Compiler).
Реализует текстовый редактор с вкладками, нумерацией строк, подсветкой синтаксиса,
панелью инструментов, главным меню, таблицей ошибок и горячими клавишами.
"""

import sys
import os
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QTextEdit, QTableWidget, QTableWidgetItem, QSplitter, QTabWidget,
    QFileDialog, QMessageBox, QDialog, QTextBrowser, QLabel, QMenu, QToolBar,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QRect, QSize, QUrl
from PyQt6.QtGui import (
    QPainter, QColor, QTextFormat, QTextCursor, QFont, QSyntaxHighlighter,
    QTextCharFormat, QKeySequence, QAction, QIcon, QDragEnterEvent, QDropEvent
)

from parser_core import PrintParser, TEXT_CONTENTS, HELP_TEXT, ABOUT_TEXT


class PythonHighlighter(QSyntaxHighlighter):
    """Подсветка синтаксиса Python для ключевых слов, строк, комментариев и чисел."""
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        # Ключевые слова
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000FF"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None',
            'nonlocal', 'not', 'or', 'pass', 'print', 'raise', 'return',
            'True', 'try', 'while', 'with', 'yield'
        ]
        for word in keywords:
            pattern = re.compile(r'\b' + word + r'\b')
            self.highlighting_rules.append((pattern, keyword_format))

        # Строки
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#008000"))
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlighting_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))

        # Комментарии
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r'#[^\n]*'), comment_format))

        # Числа
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#FF8C00"))
        self.highlighting_rules.append((re.compile(r'\b\d+(\.\d+)?\b'), number_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


class LineNumberArea(QWidget):
    """Область нумерации строк слева от редактора."""
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """Текстовый редактор с нумерацией строк и поддержкой 4 пробелов для табуляции."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)
        self.highlighter = PythonHighlighter(self.document())
        self.file_path = None
        self.is_modified = False
        self.textChanged.connect(self.mark_modified)

    def mark_modified(self):
        self.is_modified = True

    def line_number_area_width(self):
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val //= 10
            digits += 1
        space = 12 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#F0F0F0"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#707070"))
                painter.drawText(0, top, self.line_number_area.width() - 6, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

    def keyPressEvent(self, event):
        # Табуляция строго в 4 пробела
        if event.key() == Qt.Key.Key_Tab:
            self.insertPlainText("    ")
            event.accept()
        # Дублирование строки (Ctrl + D)
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_D:
            cursor = self.textCursor()
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            text = cursor.selectedText()
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
            cursor.insertBlock()
            cursor.insertText(text)
            event.accept()
        else:
            super().keyPressEvent(event)


class InfoDialog(QDialog):
    """Диалоговое окно для отображения разделов меню 'Текст' и справок."""
    def __init__(self, title, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 450)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setPlainText(text)
        browser.setFont(QFont("Consolas" if sys.platform == "win32" else "Monospace", 10))
        layout.addWidget(browser)


class MainWindow(QMainWindow):
    """Главное окно приложения языкового процессора."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Compiler")
        self.resize(900, 700)
        self.setAcceptDrops(True)

        # Главный макет и сплиттер (редактор сверху, таблица результатов снизу)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(4, 4, 4, 4)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(self.splitter)

        # Область редактирования (Вкладки)
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.splitter.addWidget(self.tab_widget)

        # Область отображения результатов (Таблица ошибок)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["File path", "Line", "Column", "Message"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.cellClicked.connect(self.on_error_clicked)
        self.splitter.addWidget(self.results_table)

        self.splitter.setSizes([500, 200])

        # Строка состояния
        self.status_bar = self.statusBar()
        self.status_label = QLabel("Готово")
        self.status_bar.addPermanentWidget(self.status_label)

        # Создание интерфейса
        self.create_actions()
        self.create_menus()
        self.create_tool_bar()

        # Открыть начальную вкладку
        self.new_document()

    def new_document(self, title="Новый документ"):
        editor = CodeEditor()
        editor.file_path = None
        editor.cursorPositionChanged.connect(self.update_cursor_status)
        index = self.tab_widget.addTab(editor, title)
        self.tab_widget.setCurrentIndex(index)
        self.status_label.setText(f"Создан новый документ: {title}")
        return editor

    def current_editor(self):
        widget = self.tab_widget.currentWidget()
        if isinstance(widget, CodeEditor):
            return widget
        return None

    def update_cursor_status(self):
        editor = self.current_editor()
        if editor:
            cursor = editor.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            file_name = os.path.basename(editor.file_path) if editor.file_path else "Без имени"
            self.status_label.setText(f"Файл: {file_name} | Строка: {line}, Столбец: {col}")

    # --- Функции меню ФАЙЛ ---
    def file_new(self):
        self.new_document("Новый документ")

    def file_open(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Открыть документ", "", "Python Files (*.py);;All Files (*.*)")
        if file_name:
            try:
                with open(file_name, "r", encoding="utf-8") as f:
                    content = f.read()
                editor = self.new_document(os.path.basename(file_name))
                editor.setPlainText(content)
                editor.file_path = file_name
                editor.is_modified = False
                self.status_label.setText(f"Открыт файл: {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{e}")

    def file_save(self):
        editor = self.current_editor()
        if not editor:
            return
        if not editor.file_path:
            self.file_save_as()
        else:
            try:
                with open(editor.file_path, "w", encoding="utf-8") as f:
                    f.write(editor.toPlainText())
                editor.is_modified = False
                self.status_label.setText(f"Файл сохранен: {editor.file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")

    def file_save_as(self):
        editor = self.current_editor()
        if not editor:
            return
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить как", "", "Python Files (*.py);;All Files (*.*)")
        if file_name:
            editor.file_path = file_name
            self.tab_widget.setTabText(self.tab_widget.currentIndex(), os.path.basename(file_name))
            self.file_save()

    def close_tab(self, index):
        widget = self.tab_widget.widget(index)
        if isinstance(widget, CodeEditor) and widget.is_modified:
            ans = QMessageBox.question(
                self, "Сохранение изменений",
                "Документ был изменен. Сохранить изменения перед закрытием?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if ans == QMessageBox.StandardButton.Save:
                self.tab_widget.setCurrentIndex(index)
                self.file_save()
            elif ans == QMessageBox.StandardButton.Cancel:
                return
        self.tab_widget.removeTab(index)

    # --- Функции меню ПРАВКА ---
    def edit_undo(self):
        editor = self.current_editor()
        if editor: editor.undo()

    def edit_redo(self):
        editor = self.current_editor()
        if editor: editor.redo()

    def edit_cut(self):
        editor = self.current_editor()
        if editor: editor.cut()

    def edit_copy(self):
        editor = self.current_editor()
        if editor: editor.copy()

    def edit_paste(self):
        editor = self.current_editor()
        if editor: editor.paste()

    def edit_delete(self):
        editor = self.current_editor()
        if editor: editor.textCursor().removeSelectedText()

    def edit_select_all(self):
        editor = self.current_editor()
        if editor: editor.selectAll()

    # --- Запуск анализатора (Пуск) ---
    def run_analyzer(self):
        editor = self.current_editor()
        if not editor:
            return
        text = editor.toPlainText()
        path = editor.file_path if editor.file_path else "Без имени.py"
        
        errors = PrintParser.analyze(text, path)
        self.results_table.setRowCount(0)
        
        if not errors:
            self.status_label.setText("Анализ завершен: ошибок не обнаружено.")
            QMessageBox.information(self, "Анализатор", "Синтаксический анализ успешно завершен. Ошибок не найдено!")
            return

        self.results_table.setRowCount(len(errors))
        for row, err in enumerate(errors):
            self.results_table.setItem(row, 0, QTableWidgetItem(str(err['file'])))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(err['line'])))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(err['column'])))
            self.results_table.setItem(row, 3, QTableWidgetItem(str(err['message'])))

        self.status_label.setText(f"Найдено ошибок: {len(errors)}")

    def on_error_clicked(self, row, column):
        """Клик по ошибке в таблице переносит курсор в редакторе на нужную строку."""
        try:
            line_item = self.results_table.item(row, 1)
            col_item = self.results_table.item(row, 2)
            if not line_item or not col_item:
                return
            target_line = int(line_item.text())
            target_col = int(col_item.text())

            editor = self.current_editor()
            if editor:
                cursor = editor.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                for _ in range(target_line - 1):
                    cursor.movePosition(QTextCursor.MoveOperation.Down)
                for _ in range(target_col - 1):
                    cursor.movePosition(QTextCursor.MoveOperation.Right)
                editor.setTextCursor(cursor)
                editor.setFocus()
        except Exception as e:
            print(f"Ошибка перехода: {e}")

    # --- Меню Текст ---
    def show_text_menu_item(self, key):
        content = TEXT_CONTENTS.get(key, "Информация отсутствует.")
        dlg = InfoDialog(key, content, self)
        dlg.exec()

    # --- Справка ---
    def show_help(self):
        dlg = InfoDialog("Вызов справки", HELP_TEXT, self)
        dlg.exec()

    def show_about(self):
        dlg = InfoDialog("О программе", ABOUT_TEXT, self)
        dlg.exec()

    # --- Вид / Шрифт ---
    def change_font_size(self, delta):
        editor = self.current_editor()
        if editor:
            font = editor.font()
            new_size = max(8, font.pointSize() + delta)
            font.setPointSize(new_size)
            editor.setFont(font)

    # --- Создание меню и панели инструментов ---
    def create_actions(self):
        # Файл
        self.act_new = QAction("Создать", self)
        self.act_new.setShortcut(QKeySequence.StandardKey.New)
        self.act_new.triggered.connect(self.file_new)

        self.act_open = QAction("Открыть...", self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self.file_open)

        self.act_save = QAction("Сохранить", self)
        self.act_save.setShortcut(QKeySequence.StandardKey.Save)
        self.act_save.triggered.connect(self.file_save)

        self.act_save_as = QAction("Сохранить как...", self)
        self.act_save_as.triggered.connect(self.file_save_as)

        self.act_exit = QAction("Выход", self)
        self.act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_exit.triggered.connect(self.close)

        # Правка
        self.act_undo = QAction("Отменить", self)
        self.act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.act_undo.triggered.connect(self.edit_undo)

        self.act_redo = QAction("Повторить", self)
        self.act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.act_redo.triggered.connect(self.edit_redo)

        self.act_cut = QAction("Вырезать", self)
        self.act_cut.setShortcut(QKeySequence.StandardKey.Cut)
        self.act_cut.triggered.connect(self.edit_cut)

        self.act_copy = QAction("Копировать", self)
        self.act_copy.setShortcut(QKeySequence.StandardKey.Copy)
        self.act_copy.triggered.connect(self.edit_copy)

        self.act_paste = QAction("Вставить", self)
        self.act_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.act_paste.triggered.connect(self.edit_paste)

        self.act_delete = QAction("Удалить", self)
        self.act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self.act_delete.triggered.connect(self.edit_delete)

        self.act_select_all = QAction("Выделить все", self)
        self.act_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        self.act_select_all.triggered.connect(self.edit_select_all)

        # Пуск
        self.act_run = QAction("Пуск", self)
        self.act_run.setShortcut(QKeySequence("F5"))
        self.act_run.triggered.connect(self.run_analyzer)

        # Справка
        self.act_help = QAction("Вызов справки", self)
        self.act_help.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.act_help.triggered.connect(self.show_help)

        self.act_about = QAction("О программе", self)
        self.act_about.triggered.connect(self.show_about)

    def create_menus(self):
        menubar = self.menuBar()

        # Файл
        menu_file = menubar.addMenu("Файл")
        menu_file.addAction(self.act_new)
        menu_file.addAction(self.act_open)
        menu_file.addAction(self.act_save)
        menu_file.addAction(self.act_save_as)
        menu_file.addSeparator()
        menu_file.addAction(self.act_exit)

        # Правка
        menu_edit = menubar.addMenu("Правка")
        menu_edit.addAction(self.act_undo)
        menu_edit.addAction(self.act_redo)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_cut)
        menu_edit.addAction(self.act_copy)
        menu_edit.addAction(self.act_paste)
        menu_edit.addAction(self.act_delete)
        menu_edit.addSeparator()
        menu_edit.addAction(self.act_select_all)

        # Текст
        menu_text = menubar.addMenu("Текст")
        for key in TEXT_CONTENTS.keys():
            action = QAction(key, self)
            action.triggered.connect(lambda checked, k=key: self.show_text_menu_item(k))
            menu_text.addAction(action)

        # Пуск
        menu_run = menubar.addMenu("Пуск")
        menu_run.addAction(self.act_run)

        # Справка
        menu_help = menubar.addMenu("Справка")
        menu_help.addAction(self.act_help)
        menu_help.addAction(self.act_about)

        # Вид (дополнительно)
        menu_view = menubar.addMenu("Вид")
        act_zoom_in = QAction("Увеличить шрифт", self)
        act_zoom_in.triggered.connect(lambda: self.change_font_size(2))
        act_zoom_out = QAction("Уменьшить шрифт", self)
        act_zoom_out.triggered.connect(lambda: self.change_font_size(-2))
        menu_view.addAction(act_zoom_in)
        menu_view.addAction(act_zoom_out)

    def create_tool_bar(self):
        toolbar = QToolBar("Панель инструментов")
        self.addToolBar(toolbar)

        toolbar.addAction(self.act_new)
        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)
        toolbar.addSeparator()
        toolbar.addAction(self.act_undo)
        toolbar.addAction(self.act_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.act_copy)
        toolbar.addAction(self.act_cut)
        toolbar.addAction(self.act_paste)
        toolbar.addSeparator()
        toolbar.addAction(self.act_run)
        toolbar.addSeparator()
        toolbar.addAction(self.act_help)
        toolbar.addAction(self.act_about)

    # --- Поддержка Drag & Drop файлов ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    editor = self.new_document(os.path.basename(file_path))
                    editor.setPlainText(content)
                    editor.file_path = file_path
                    editor.is_modified = False
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
