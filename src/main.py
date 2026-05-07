import sys
import re
import markdown as md_lib
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QPushButton, QLabel, QFrame, QSizePolicy, QTextEdit,
    QTextBrowser,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent, QSize
from PyQt6.QtGui import QFont, QColor
from generation.generate import generate_response


# ── Color palette ─────────────────────────────────────────────────────────────
C = {
    "app_bg":        "#09091a",
    "header_bg":     "#0d0d1f",
    "chat_bg":       "#0f0f20",
    "user_bubble":   "#4361ee",
    "user_bubble_h": "#5372ff",
    "bot_bubble":    "#181830",
    "bot_border":    "#252548",
    "input_area_bg": "#0d0d1f",
    "input_field":   "#171730",
    "input_border":  "#282850",
    "input_focus":   "#4361ee",
    "send_btn":      "#4361ee",
    "send_hover":    "#5372ff",
    "send_dis":      "#222240",
    "text_primary":  "#e8e8ff",
    "text_user":     "#ffffff",
    "text_muted":    "#6a6a9a",
    "text_hint":     "#4a4a7a",
    "green_dot":     "#3ddc84",
    "divider":       "#181830",
    "avatar_bg":     "#1a1a35",
    "welcome_bg":    "#131328",
    "welcome_bdr":   "#222245",
    "scrollbar":     "#252550",
    "error_bubble":  "#2a1428",
    "error_border":  "#5a2040",
    "error_text":    "#ff7eb6",
}

FF = "Segoe UI"

def _md(text: str) -> str:
    """Convert a markdown string to an HTML fragment."""
    return md_lib.markdown(text.strip(), extensions=["extra"])


def _parse_sections(text: str) -> tuple[str, str, str]:
    """
    Split the structured LLM answer into (answer, key_terms, sources).
    Handles both **Bold** headers and ## Markdown headers.
    Falls back gracefully if the response is not structured.
    """
    header = r"(?:\*\*{h}\*\*|##\s*{h})"

    ans_pat = re.search(
        header.format(h=r"Answer") + r"(.*?)"
        r"(?=" + header.format(h=r"Key\s+term[^*\n]*") + r"|"
               + header.format(h=r"Sources[^*\n]*") + r"|\Z)",
        text, re.DOTALL | re.IGNORECASE,
    )
    kt_pat = re.search(
        header.format(h=r"Key\s+term[^*\n]*") + r"(.*?)"
        r"(?=" + header.format(h=r"Sources[^*\n]*") + r"|\Z)",
        text, re.DOTALL | re.IGNORECASE,
    )
    src_pat = re.search(
        header.format(h=r"Sources\s+used[^*\n]*") + r"(.*?)$",
        text, re.DOTALL | re.IGNORECASE,
    )

    answer    = ans_pat.group(1).strip()  if ans_pat  else text.strip()
    key_terms = kt_pat.group(1).strip()   if kt_pat   else ""
    sources   = src_pat.group(1).strip()  if src_pat  else ""
    return answer, key_terms, sources


_BOT_CSS = """
<style>
body  { font-family:'Segoe UI',system-ui,sans-serif; font-size:14px;
        color:#e0e0ff; line-height:1.8; margin:0; padding:0;
        background:transparent; }
p     { margin:0 0 10px 0; }
strong{ color:#a8b8ff; }
em    { color:#c0c8ff; font-style:italic; }
ul,ol { margin:4px 0 10px 0; padding-left:22px; }
li    { margin:4px 0; }
code  { background:#0d0d2a; color:#a0b4ff; padding:2px 7px;
        border-radius:4px; font-size:12px; font-family:monospace; }
h1,h2,h3 { color:#b0c0ff; margin:12px 0 5px; font-size:15px; font-weight:600; }
</style>
"""


# ── Table HTML post-processor ─────────────────────────────────────────────────
# Qt's HTML engine ignores most CSS for table elements, so we inject
# inline styles and HTML attributes directly onto every table tag.

_TH_STYLE = (
    "background-color:#151530;"
    "color:#9aaeff;"
    "padding:9px 16px;"
    "border-bottom:2px solid #4361ee;"
    "text-align:left;"
    "font-weight:600;"
    "font-size:13px;"
    "white-space:nowrap;"
)

_TD_STYLE = (
    "color:#dde0ff;"
    "padding:8px 16px;"
    "border-bottom:1px solid #1e1e40;"
    "vertical-align:top;"
    "font-size:13px;"
)

_TD_ALT_STYLE = (
    "background-color:#111128;"
    "color:#dde0ff;"
    "padding:8px 16px;"
    "border-bottom:1px solid #1e1e40;"
    "vertical-align:top;"
    "font-size:13px;"
)


def _fix_tables(html: str) -> str:
    """
    Post-process markdown-generated table HTML for Qt's limited renderer.
    Injects inline styles on <table>, <th>, <td>, and alternating <tr> rows.
    """
    # Wrap <table> with proper attributes
    html = re.sub(
        r'<table>',
        '<table cellspacing="0" cellpadding="0" width="100%" '
        'style="margin:14px 0; border-collapse:collapse;">',
        html,
    )

    # Header cells
    html = re.sub(r'<th>', f'<th style="{_TH_STYLE}">', html)

    # Alternate row background via stateful replacer
    _row: list[int] = [0]

    def _style_tr(m: re.Match) -> str:
        # skip header rows (inside <thead>)
        _row[0] += 1
        return '<tr>'   # plain tr — td bg handles alternation below

    html = re.sub(r'<tr>', _style_tr, html)

    # Data cells — inject alternating bg by tracking position within each table
    _cell_row: list[int] = [0]
    _in_thead: list[bool] = [False]

    def _replace_cell(m: re.Match) -> str:
        style = _TD_ALT_STYLE if (_cell_row[0] % 2 == 1) else _TD_STYLE
        return f'<td style="{style}">'

    def _enter_tbody(m: re.Match) -> str:
        _cell_row[0] = 0
        return m.group(0)

    def _tr_in_tbody(m: re.Match) -> str:
        _cell_row[0] += 1
        return m.group(0)

    # Use a single-pass state machine instead of nested regex
    result: list[str] = []
    pos = 0
    in_tbody = False
    row_index = 0

    i = 0
    tokens = re.split(r'(</?tbody>|</?thead>|<tr>|</?tr>|<td>)', html)
    for tok in tokens:
        if tok == '<tbody>':
            in_tbody = True
            row_index = 0
            result.append(tok)
        elif tok == '</tbody>':
            in_tbody = False
            result.append(tok)
        elif tok == '<thead>':
            in_tbody = False
            result.append(tok)
        elif tok == '<tr>' and in_tbody:
            row_index += 1
            result.append(tok)
        elif tok == '<td>' and in_tbody:
            style = _TD_ALT_STYLE if (row_index % 2 == 0) else _TD_STYLE
            result.append(f'<td style="{style}">')
        else:
            result.append(tok)

    return "".join(result)


def build_bot_html(text: str) -> str:
    """
    Convert the structured LLM response into dark-themed, section-aware HTML
    for rendering inside a QTextBrowser.
    """
    answer, key_terms, sources = _parse_sections(text)

    html = _BOT_CSS

    # Answer — run through table fixer so any markdown tables render properly
    html += f'<div style="margin:0;">{_fix_tables(_md(answer))}</div>'

    # Key Terms
    if key_terms:
        html += f"""
        <table width="100%" cellspacing="0" cellpadding="0"
               style="margin-top:12px;">
          <tr><td style="background-color:#12122c;
                         border-left:3px solid #4361ee;
                         padding:8px 12px;">
            <p style="font-size:10px; font-weight:bold; letter-spacing:1px;
                      color:#5060a0; margin:0 0 5px 0;">KEY TERMS</p>
            {_fix_tables(_md(key_terms))}
          </td></tr>
        </table>"""

    # Sources
    if sources:
        html += f"""
        <table width="100%" cellspacing="0" cellpadding="0"
               style="margin-top:10px; border-top:1px solid #252548;">
          <tr><td style="padding-top:8px;">
            <p style="font-size:10px; font-weight:bold; letter-spacing:1px;
                      color:#5060a0; margin:0 0 4px 0;">SOURCES</p>
            <div style="color:#6a6a9a; font-size:11px;">{_fix_tables(_md(sources))}</div>
          </td></tr>
        </table>"""

    return html


# ══════════════════════════════════════════════════════════════════════════════
# Worker thread
# ══════════════════════════════════════════════════════════════════════════════
class GenerateWorker(QThread):
    finished = pyqtSignal(str)
    errored  = pyqtSignal(str)

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self):
        try:
            self.finished.emit(generate_response(self.query))
        except Exception as exc:
            self.errored.emit(str(exc))


# ══════════════════════════════════════════════════════════════════════════════
# Typing / thinking indicator
# ══════════════════════════════════════════════════════════════════════════════
class TypingIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._step = 0

        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 4, 20, 4)
        outer.setSpacing(10)

        # Avatar
        av = QLabel("📚")
        av.setFixedSize(36, 36)
        av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        av.setFont(QFont(FF, 16))
        av.setStyleSheet(f"background:{C['avatar_bg']};border-radius:18px;")
        outer.addWidget(av, 0, Qt.AlignmentFlag.AlignTop)

        # Bubble
        self._label = QLabel("Thinking .")
        self._label.setFont(QFont(FF, 10))
        self._label.setStyleSheet(f"""
            background: {C['bot_bubble']};
            color: {C['text_muted']};
            border: 1px solid {C['bot_border']};
            border-radius: 18px;
            border-top-left-radius: 4px;
            padding: 10px 18px;
        """)
        outer.addWidget(self._label)
        outer.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(480)

    def _tick(self):
        dots = "." * ((self._step % 3) + 1)
        spaces = "  " * (3 - (self._step % 3) - 1)   # keep width stable
        self._label.setText(f"Thinking {dots}{spaces}")
        self._step += 1

    def stop(self):
        self._timer.stop()


# ══════════════════════════════════════════════════════════════════════════════
# Message bubble
# ══════════════════════════════════════════════════════════════════════════════
class MessageBubble(QWidget):
    def __init__(self, text: str, is_user: bool, is_error: bool = False, parent=None):
        super().__init__(parent)
        self._build(text, is_user, is_error)

    def _build(self, text: str, is_user: bool, is_error: bool):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 4, 20, 4)
        outer.setSpacing(10)

        # ── bot avatar ─────────────────────────────────────────────────────
        if not is_user:
            av = QLabel("📚")
            av.setFixedSize(36, 36)
            av.setAlignment(Qt.AlignmentFlag.AlignCenter)
            av.setFont(QFont(FF, 16))
            av.setStyleSheet(f"background:{C['avatar_bg']};border-radius:18px;")
            outer.addWidget(av, 0, Qt.AlignmentFlag.AlignTop)

        # ══ USER bubble — plain QLabel ═════════════════════════════════════
        if is_user:
            bubble = QLabel(text)
            bubble.setWordWrap(True)
            bubble.setFont(QFont(FF, 11))
            bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            bubble.setMaximumWidth(800)
            bubble.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse |
                Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            bubble.setStyleSheet(f"""
                QLabel {{
                    background: {C['user_bubble']};
                    color: {C['text_user']};
                    border-radius: 18px;
                    border-bottom-right-radius: 4px;
                    padding: 10px 16px;
                }}
            """)
            outer.addStretch()
            outer.addWidget(bubble)
            return

        # ══ ERROR bubble — plain QLabel ════════════════════════════════════
        if is_error:
            bubble = QLabel(f"⚠️  {text}")
            bubble.setWordWrap(True)
            bubble.setFont(QFont(FF, 11))
            bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            bubble.setMaximumWidth(800)
            bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            bubble.setStyleSheet(f"""
                QLabel {{
                    background: {C['error_bubble']};
                    color: {C['error_text']};
                    border: 1px solid {C['error_border']};
                    border-radius: 18px;
                    border-top-left-radius: 4px;
                    padding: 10px 16px;
                }}
            """)
            outer.addWidget(bubble)
            outer.addStretch()
            return

        # ══ BOT bubble — QTextBrowser with rendered markdown ════════════════
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        browser.setStyleSheet(f"""
            QTextBrowser {{
                background: {C['bot_bubble']};
                color: {C['text_primary']};
                border: 1px solid {C['bot_border']};
                border-radius: 18px;
                border-top-left-radius: 4px;
                padding: 10px 14px;
                selection-background-color: {C['user_bubble']};
                font-size: 14px;
            }}
            QTextBrowser:focus {{ border-color: {C['bot_border']}; }}
        """)

        html = build_bot_html(text)
        browser.setHtml(html)

        # Auto-fit height to content (runs after Qt has laid out the document)
        def _fit():
            h = int(browser.document().size().height())
            browser.setFixedHeight(h + 20)

        QTimer.singleShot(0,  _fit)   # first pass (fast, catches most cases)
        QTimer.singleShot(80, _fit)   # second pass (catches late reflow)

        outer.addWidget(browser)
        outer.addStretch()


# ══════════════════════════════════════════════════════════════════════════════
# Header bar
# ══════════════════════════════════════════════════════════════════════════════
class HeaderBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(62)
        self.setStyleSheet(f"""
            QWidget {{
                background: {C['header_bg']};
                border-bottom: 1px solid {C['divider']};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 24, 0)
        layout.setSpacing(0)

        # Icon
        icon = QLabel("📚")
        icon.setFont(QFont(FF, 22))
        icon.setFixedWidth(42)
        icon.setStyleSheet("background:transparent;border:none;")

        # Title + subtitle column
        title = QLabel("TM Lecture Assistant")
        title.setFont(QFont(FF, 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{C['text_primary']};background:transparent;border:none;")

        subtitle = QLabel("RAG-powered  ·  Text Mining")
        subtitle.setFont(QFont(FF, 8))
        subtitle.setStyleSheet(f"color:{C['text_muted']};background:transparent;border:none;")

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.addWidget(title)
        text_col.addWidget(subtitle)

        layout.addWidget(icon)
        layout.addSpacing(8)
        layout.addLayout(text_col)
        layout.addStretch()


# ══════════════════════════════════════════════════════════════════════════════
# Input bar
# ══════════════════════════════════════════════════════════════════════════════
class InputBar(QWidget):
    submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{C['input_area_bg']};")
        self._build()

    def _build(self):
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setSpacing(0)

        # top divider line
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{C['divider']};")
        wrapper.addWidget(line)

        # main row
        row = QHBoxLayout()
        row.setContentsMargins(18, 12, 18, 12)
        row.setSpacing(12)

        # text field
        self.field = QTextEdit()
        self.field.setPlaceholderText("Ask a Text Mining question…")
        self.field.setFixedHeight(50)
        self.field.setFont(QFont(FF, 10))
        self.field.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.field.installEventFilter(self)
        self.field.setStyleSheet(f"""
            QTextEdit {{
                background: {C['input_field']};
                color: {C['text_primary']};
                border: 1.5px solid {C['input_border']};
                border-radius: 25px;
                padding: 13px 20px;
                font-size: 10pt;
                selection-background-color: {C['user_bubble']};
            }}
            QTextEdit:focus {{
                border-color: {C['input_focus']};
            }}
        """)

        # send button
        self.send_btn = QPushButton("Send  ▶")
        self.send_btn.setFixedSize(QSize(96, 50))
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFont(QFont(FF, 9, QFont.Weight.Bold))
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['send_btn']};
                color: white;
                border-radius: 25px;
                border: none;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover  {{ background: {C['send_hover']}; }}
            QPushButton:pressed {{ background: #3251d0; }}
            QPushButton:disabled {{
                background: {C['send_dis']};
                color: {C['text_hint']};
            }}
        """)
        self.send_btn.clicked.connect(self._emit)

        row.addWidget(self.field)
        row.addWidget(self.send_btn)

        # hint label
        hint = QLabel("Enter  to send  ·  Shift+Enter  for new line")
        hint.setFont(QFont(FF, 7))
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"color:{C['text_hint']};background:transparent;border:none;padding-bottom:6px;")

        wrapper.addLayout(row)
        wrapper.addWidget(hint)

    # intercept Enter key in the text field
    def eventFilter(self, obj, event: QEvent):
        if obj is self.field and event.type() == QEvent.Type.KeyPress:
            key   = event.key()
            mods  = event.modifiers()
            enter = Qt.Key.Key_Return
            shift = Qt.KeyboardModifier.ShiftModifier
            if key == enter and not (mods & shift):
                self._emit()
                return True
        return super().eventFilter(obj, event)

    def _emit(self):
        text = self.field.toPlainText().strip()
        if text:
            self.submitted.emit(text)
            self.field.clear()

    def set_enabled(self, enabled: bool):
        self.field.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        if enabled:
            self.field.setFocus()


# ══════════════════════════════════════════════════════════════════════════════
# Main window
# ══════════════════════════════════════════════════════════════════════════════
class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TM Lecture Assistant")
        self.resize(1100, 820)
        self.setMinimumSize(640, 500)
        self._worker: GenerateWorker | None = None
        self._typing: TypingIndicator | None = None
        self._build_ui()
        self._apply_global_style()
        self._show_welcome()

    # ── global stylesheet ──────────────────────────────────────────────────
    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {C['app_bg']};
                font-family: "{FF}";
            }}
            QScrollArea {{
                border: none;
                background: {C['chat_bg']};
            }}
            QScrollBar:vertical {{
                background: {C['chat_bg']};
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {C['scrollbar']};
                border-radius: 3px;
                min-height: 28px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; border: 0; }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{ background: none; }}
        """)

    # ── layout ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # header
        root_layout.addWidget(HeaderBar())

        # scrollable chat area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet(f"background:{C['chat_bg']};")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 20, 0, 20)
        self.chat_layout.setSpacing(4)
        self.chat_layout.addStretch()       # keeps messages pushed to the bottom initially

        self.scroll.setWidget(self.chat_container)
        root_layout.addWidget(self.scroll, stretch=1)

        # input bar
        self.input_bar = InputBar()
        self.input_bar.submitted.connect(self._on_submit)
        root_layout.addWidget(self.input_bar)

        self.setCentralWidget(root)

    # ── welcome card ───────────────────────────────────────────────────────
    def _show_welcome(self):
        card = QLabel(
            "👋  Welcome!  I'm your Text Mining Teaching Assistant.\n\n"
            "Ask me anything about TM lectures, concepts, or slides.\n"
            "I'll search the lecture database and explain clearly."
        )
        card.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.setFont(QFont(FF, 10))
        card.setWordWrap(True)
        card.setStyleSheet(f"""
            color: {C['text_muted']};
            background: {C['welcome_bg']};
            border: 1px solid {C['welcome_bdr']};
            border-radius: 16px;
            padding: 24px 32px;
            margin: 10px 60px;
            line-height: 1.6;
        """)
        self.chat_layout.addWidget(card)

    # ── user submits query ─────────────────────────────────────────────────
    def _on_submit(self, query: str):
        self._add_bubble(query, is_user=True)
        self.input_bar.set_enabled(False)

        # typing indicator
        self._typing = TypingIndicator()
        self.chat_layout.addWidget(self._typing)
        QTimer.singleShot(30, self._scroll_to_bottom)

        # kick off worker
        self._worker = GenerateWorker(query)
        self._worker.finished.connect(self._on_success)
        self._worker.errored.connect(self._on_error)
        self._worker.start()

    # ── response callbacks ─────────────────────────────────────────────────
    def _on_success(self, text: str):
        self._remove_typing()
        self._add_bubble(text, is_user=False)
        self.input_bar.set_enabled(True)

    def _on_error(self, msg: str):
        self._remove_typing()
        self._add_bubble(f"⚠️  {msg}", is_user=False, is_error=True)
        self.input_bar.set_enabled(True)

    # ── helpers ────────────────────────────────────────────────────────────
    def _remove_typing(self):
        if self._typing:
            self._typing.stop()
            self._typing.setParent(None)
            self._typing = None

    def _add_bubble(self, text: str, *, is_user: bool, is_error: bool = False):
        bubble = MessageBubble(text, is_user, is_error)
        self.chat_layout.addWidget(bubble)
        QTimer.singleShot(30, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("TM Lecture Assistant")

    # force a clean dark palette so native widgets don't bleed light colors
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window,     QColor(C["app_bg"]))
    palette.setColor(palette.ColorRole.WindowText, QColor(C["text_primary"]))
    palette.setColor(palette.ColorRole.Base,       QColor(C["input_field"]))
    palette.setColor(palette.ColorRole.Text,       QColor(C["text_primary"]))
    app.setPalette(palette)

    window = ChatWindow()
    window.show()
    sys.exit(app.exec())