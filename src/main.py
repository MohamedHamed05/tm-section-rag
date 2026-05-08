import sys
import re
import markdown as md_lib
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QPushButton, QLabel, QFrame, QSizePolicy, QTextEdit,
    QTextBrowser, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent, QSize
from PyQt6.QtGui import QFont, QColor, QPalette
from generation.generate import generate_response


# ══════════════════════════════════════════════════════════════════════════════
# MODERN COLOR PALETTE  —  Deep space indigo with vibrant accents
# ══════════════════════════════════════════════════════════════════════════════
C = {
    # Backgrounds
    "app_bg":          "#060611",
    "header_bg":       "#0b0b1e",
    "chat_bg":         "#08081a",
    # Bubbles
    "user_bubble":     "#4f46e5",
    "user_bubble_h":   "#6366f1",
    "bot_bubble":      "#111128",
    "bot_border":      "#1e1e45",
    # Input
    "input_area_bg":   "#0a0a1a",
    "input_field":     "#0f0f25",
    "input_border":    "#1e1e40",
    "input_focus":     "#6366f1",
    # Buttons
    "send_btn":        "#4f46e5",
    "send_hover":      "#6366f1",
    "send_dis":        "#1a1a35",
    # Text
    "text_primary":    "#eef0ff",
    "text_user":       "#ffffff",
    "text_muted":      "#7878a8",
    "text_hint":       "#3e3e6e",
    # Accents
    "accent":          "#818cf8",
    "accent_dim":      "#3730a3",
    "accent_mid":      "#4f46e5",
    "green_dot":       "#34d399",
    "divider":         "#151530",
    "avatar_bg":       "#1a1a38",
    "avatar_bdr":      "#2a2a50",
    # Welcome
    "welcome_bg":      "#0d0d24",
    "welcome_bdr":     "#2a2a55",
    "welcome_glow":    "#4f46e5",
    # Scroll
    "scrollbar":       "#252550",
    # Error
    "error_bubble":    "#1f0a18",
    "error_border":    "#4c1d4a",
    "error_text":      "#f472b6",
    # Gradient stops
    "grad_start":      "#4f46e5",
    "grad_end":        "#7c3aed",
    # Glow
    "glow_user":       "#4f46e540",
    "glow_bot":        "#818cf820",
    # Table
    "th_bg":           "#0f0f28",
    "th_border":       "#4f46e5",
    "td_border":       "#161635",
    "td_alt":          "#0c0c22",
    # Header specific
    "nav_active":      "#4f46e5",
    "nav_hover":       "#1e1e45",
    "badge_bg":        "#1a1a38",
    "badge_bdr":       "#2a2a55",
    "new_chat_bg":     "#1e1e45",
}

FF = "Carlito"
FF_MONO = "Sarasa Mono SC"


def _md(text: str) -> str:
    """Convert a markdown string to an HTML fragment."""
    return md_lib.markdown(text.strip(), extensions=["extra"])


def _parse_sections(text: str) -> tuple[str, str, str]:
    """
    Split the structured LLM answer into (answer, key_terms, sources).
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


_BOT_CSS = f"""
<style>
body  {{ font-family:'{FF}','Noto Sans SC',system-ui,sans-serif; font-size:14px;
        color:#eef0ff; line-height:1.85; margin:0; padding:0;
        background:transparent; }}
p     {{ margin:0 0 10px 0; }}
strong{{ color:#a5b4fc; }}
em    {{ color:#c7d2fe; font-style:italic; }}
ul,ol {{ margin:4px 0 10px 0; padding-left:22px; }}
li    {{ margin:4px 0; }}
code  {{ background:#0a0a22; color:#a5b4fc; padding:2px 8px;
        border-radius:5px; font-size:12.5px; font-family:'{FF_MONO}','DejaVu Sans Mono',monospace;
        border:1px solid #1a1a40; }}
h1,h2,h3 {{ color:#c7d2fe; margin:14px 0 6px; font-size:15px; font-weight:700; letter-spacing:0.3px; }}
a     {{ color:#818cf8; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
</style>
"""

_TH_STYLE = (
    "background-color:#0f0f28;"
    "color:#a5b4fc;"
    "padding:10px 18px;"
    "border-bottom:2px solid #4f46e5;"
    "text-align:left;"
    "font-weight:700;"
    "font-size:12.5px;"
    "white-space:nowrap;"
    "letter-spacing:0.3px;"
)

_TD_STYLE = (
    "color:#dde0ff;"
    "padding:9px 18px;"
    "border-bottom:1px solid #161635;"
    "vertical-align:top;"
    "font-size:13px;"
)

_TD_ALT_STYLE = (
    "background-color:#0c0c22;"
    "color:#dde0ff;"
    "padding:9px 18px;"
    "border-bottom:1px solid #161635;"
    "vertical-align:top;"
    "font-size:13px;"
)


def _fix_tables(html: str) -> str:
    html = re.sub(
        r'<table>',
        '<table cellspacing="0" cellpadding="0" width="100%" '
        'style="margin:14px 0; border-collapse:collapse; border-radius:8px; overflow:hidden;">',
        html,
    )
    html = re.sub(r'<th>', f'<th style="{_TH_STYLE}">', html)

    result: list[str] = []
    in_tbody = False
    row_index = 0

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
    answer, key_terms, sources = _parse_sections(text)
    html = _BOT_CSS
    html += f'<div style="margin:0;">{_fix_tables(_md(answer))}</div>'

    if key_terms:
        html += f"""
        <table width="100%" cellspacing="0" cellpadding="0"
               style="margin-top:14px;">
          <tr><td style="background-color:#0c0c24;
                         border-left:3px solid #4f46e5;
                         border-radius:0 8px 8px 0;
                         padding:10px 14px;">
            <p style="font-size:9.5px; font-weight:bold; letter-spacing:1.5px;
                      color:#6366f1; margin:0 0 6px 0;">KEY TERMS</p>
            {_fix_tables(_md(key_terms))}
          </td></tr>
        </table>"""

    if sources:
        html += f"""
        <table width="100%" cellspacing="0" cellpadding="0"
               style="margin-top:12px; border-top:1px solid #1e1e45;">
          <tr><td style="padding-top:10px;">
            <p style="font-size:9.5px; font-weight:bold; letter-spacing:1.5px;
                      color:#6366f1; margin:0 0 5px 0;">SOURCES</p>
            <div style="color:#7878a8; font-size:11.5px;">{_fix_tables(_md(sources))}</div>
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
# Pulsing dot typing indicator
# ══════════════════════════════════════════════════════════════════════════════
class TypingIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._step = 0

        outer = QHBoxLayout(self)
        outer.setContentsMargins(24, 6, 24, 6)
        outer.setSpacing(12)

        av = QLabel("📚")
        av.setFixedSize(38, 38)
        av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        av.setFont(QFont(FF, 16))
        av.setStyleSheet(f"""
            background: {C['avatar_bg']};
            border: 1.5px solid {C['avatar_bdr']};
            border-radius: 19px;
        """)
        outer.addWidget(av, 0, Qt.AlignmentFlag.AlignTop)

        self._bubble = QWidget()
        self._bubble.setObjectName("typingBubble")
        self._bubble.setStyleSheet(f"""
            #typingBubble {{
                background: {C['bot_bubble']};
                border: 1px solid {C['bot_border']};
                border-radius: 20px;
                border-top-left-radius: 6px;
            }}
        """)
        bubble_layout = QHBoxLayout(self._bubble)
        bubble_layout.setContentsMargins(18, 12, 18, 12)
        bubble_layout.setSpacing(6)

        self._dots = []
        for i in range(3):
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background: {C['accent']}; border-radius: 4px;")
            bubble_layout.addWidget(dot)
            self._dots.append(dot)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(C["glow_bot"]))
        shadow.setOffset(0, 2)
        self._bubble.setGraphicsEffect(shadow)

        outer.addWidget(self._bubble)
        outer.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(400)

    def _tick(self):
        active = self._step % 3
        for i, dot in enumerate(self._dots):
            if i == active:
                dot.setStyleSheet(f"background: {C['accent']}; border-radius: 4px;")
                dot.setFixedSize(10, 10)
            else:
                dot.setStyleSheet(f"background: {C['accent_dim']}; border-radius: 4px;")
                dot.setFixedSize(7, 7)
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
        outer.setContentsMargins(24, 6, 24, 6)
        outer.setSpacing(12)

        if not is_user:
            av = QLabel("📚")
            av.setFixedSize(38, 38)
            av.setAlignment(Qt.AlignmentFlag.AlignCenter)
            av.setFont(QFont(FF, 16))
            av.setStyleSheet(f"""
                background: {C['avatar_bg']};
                border: 1.5px solid {C['avatar_bdr']};
                border-radius: 19px;
            """)
            outer.addWidget(av, 0, Qt.AlignmentFlag.AlignTop)

        if is_user:
            bubble = QLabel(text)
            bubble.setWordWrap(True)
            bubble.setFont(QFont(FF, 16))
            bubble.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            bubble.setMaximumWidth(250)
            bubble.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse |
                Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            bubble.setObjectName("userBubble")
            bubble.setStyleSheet(f"""
                #userBubble {{
                    background: {C['user_bubble']};
                    color: {C['text_user']};
                    border-radius: 20px;
                    border-bottom-right-radius: 6px;
                    padding: 12px 20px;
                    font-weight: 500;
                    font-size: 13pt;
                    letter-spacing: 0.2px;
                }}
            """)

            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(18)
            shadow.setColor(QColor(C["glow_user"]))
            shadow.setOffset(0, 3)
            bubble.setGraphicsEffect(shadow)

            outer.addStretch()
            outer.addWidget(bubble)
            return

        if is_error:
            bubble = QLabel(f"  {text}")
            bubble.setWordWrap(True)
            bubble.setFont(QFont(FF, 11))
            bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
            bubble.setMaximumWidth(800)
            bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            bubble.setObjectName("errorBubble")
            bubble.setStyleSheet(f"""
                #errorBubble {{
                    background: {C['error_bubble']};
                    color: {C['error_text']};
                    border: 1px solid {C['error_border']};
                    border-radius: 20px;
                    border-top-left-radius: 6px;
                    padding: 11px 18px;
                    font-weight: 500;
                }}
            """)
            outer.addWidget(bubble)
            outer.addStretch()
            return

        # BOT bubble — wrapper with content + copy button
        bot_col = QVBoxLayout()
        bot_col.setSpacing(0)
        bot_col.setContentsMargins(0, 0, 0, 0)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        browser.setObjectName("botBrowser")
        browser.setStyleSheet(f"""
            #botBrowser {{
                background: {C['bot_bubble']};
                color: {C['text_primary']};
                border: 1px solid {C['bot_border']};
                border-radius: 20px;
                border-top-left-radius: 6px;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
                padding: 12px 16px;
                selection-background-color: {C['accent_dim']};
                font-size: 14px;
            }}
            #botBrowser:focus {{ border-color: {C['bot_border']}; }}
        """)

        html = build_bot_html(text)
        browser.setHtml(html)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(14)
        shadow.setColor(QColor(C["glow_bot"]))
        shadow.setOffset(0, 2)
        browser.setGraphicsEffect(shadow)

        # Copy button row
        copy_row = QWidget()
        copy_row.setObjectName("copyRow")
        copy_row.setStyleSheet(f"#copyRow {{ background: transparent; border: none; }}")
        copy_layout = QHBoxLayout(copy_row)
        copy_layout.setContentsMargins(8, 2, 0, 0)
        copy_layout.setSpacing(0)

        copy_btn = QPushButton("  Copy")
        copy_btn.setObjectName("copyBtn")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setFont(QFont(FF, 8))
        copy_btn.setFixedHeight(24)
        copy_btn.setStyleSheet(f"""
            #copyBtn {{
                background: transparent;
                color: {C['text_hint']};
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 2px 10px;
                letter-spacing: 0.5px;
                font-weight: 500;
            }}
            #copyBtn:hover {{
                background: {C['badge_bg']};
                color: {C['accent']};
                border-color: {C['bot_border']};
            }}
            #copyBtn:pressed {{
                background: {C['accent_dim']};
                color: white;
            }}
        """)

        def _copy_response():
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            copy_btn.setText("  Copied!")
            copy_btn.setStyleSheet(f"""
                #copyBtn {{
                    background: transparent;
                    color: {C['green_dot']};
                    border: 1px solid transparent;
                    border-radius: 6px;
                    padding: 2px 10px;
                    letter-spacing: 0.5px;
                    font-weight: 600;
                }}
                #copyBtn:hover {{
                    background: {C['badge_bg']};
                    border-color: {C['bot_border']};
                }}
            """)
            QTimer.singleShot(2000, lambda: (
                copy_btn.setText("  Copy"),
                copy_btn.setStyleSheet(f"""
                    #copyBtn {{
                        background: transparent;
                        color: {C['text_hint']};
                        border: 1px solid transparent;
                        border-radius: 6px;
                        padding: 2px 10px;
                        letter-spacing: 0.5px;
                        font-weight: 500;
                    }}
                    #copyBtn:hover {{
                        background: {C['badge_bg']};
                        color: {C['accent']};
                        border-color: {C['bot_border']};
                    }}
                """)
            ))

        copy_btn.clicked.connect(_copy_response)
        copy_layout.addWidget(copy_btn)
        copy_layout.addStretch()

        bot_col.addWidget(browser)
        bot_col.addWidget(copy_row)

        def _fit():
            h = int(browser.document().size().height())
            browser.setFixedHeight(h + 24)

        QTimer.singleShot(0,  _fit)
        QTimer.singleShot(80, _fit)

        outer.addLayout(bot_col)
        outer.addStretch()


# ══════════════════════════════════════════════════════════════════════════════
# Header bar  —  FULLY POPULATED with useful content
# ══════════════════════════════════════════════════════════════════════════════
class HeaderBar(QWidget):
    new_chat_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(68)
        self.setObjectName("headerBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(0)

        # ── Left: App icon + title ──────────────────────────────────────
        icon_frame = QLabel("📚")
        icon_frame.setObjectName("headerIcon")
        icon_frame.setFont(QFont(FF, 20))
        icon_frame.setFixedSize(42, 42)
        icon_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_frame.setStyleSheet(f"""
            #headerIcon {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {C['accent_mid']}, stop:1 {C['grad_end']});
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 20px;
            }}
        """)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.setContentsMargins(0, 0, 0, 0)

        title = QLabel("TM Lecture Assistant")
        title.setObjectName("headerTitle")
        title.setFont(QFont(FF, 13, QFont.Weight.Bold))
        title.setContentsMargins(0, 0, 0, -2)
        title.setFixedHeight(20)
        title.setStyleSheet(f"""
            #headerTitle {{
                color: {C['text_primary']};
                background: transparent;
                border: none;
                letter-spacing: 0.4px;
                padding: 0;
                margin: 0;
            }}
        """)

        subtitle = QLabel("RAG-powered  ·  Text Mining")
        subtitle.setObjectName("headerSubtitle")
        subtitle.setFont(QFont(FF, 8))
        subtitle.setContentsMargins(0, -2, 0, 0)
        subtitle.setFixedHeight(14)
        subtitle.setStyleSheet(f"""
            #headerSubtitle {{
                color: {C['accent']};
                background: transparent;
                border: none;
                letter-spacing: 1px;
            }}
        """)

        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        layout.addWidget(icon_frame)
        layout.addSpacing(12)
        layout.addLayout(title_col)
        layout.addStretch()

        # ── Right: New Chat button ──────────────────────────────────────
        right_layout = QHBoxLayout()
        right_layout.setSpacing(10)

        # Online status with green dot
        status_dot = QLabel()
        status_dot.setObjectName("statusDot")
        status_dot.setFixedSize(8, 8)
        status_dot.setStyleSheet(f"""
            #statusDot {{
                background: {C['green_dot']};
                border-radius: 4px;
            }}
        """)
        dot_glow = QGraphicsDropShadowEffect()
        dot_glow.setBlurRadius(8)
        dot_glow.setColor(QColor(C["green_dot"]))
        dot_glow.setOffset(0, 0)
        status_dot.setGraphicsEffect(dot_glow)

        status_label = QLabel("Online")
        status_label.setObjectName("statusLabel")
        status_label.setFont(QFont(FF, 8, QFont.Weight.Bold))
        status_label.setStyleSheet(f"""
            #statusLabel {{
                color: {C['green_dot']};
                background: transparent;
                border: none;
                letter-spacing: 0.5px;
            }}
        """)

        right_layout.addWidget(status_dot)
        right_layout.addWidget(status_label)
        right_layout.addSpacing(16)

        new_chat = QPushButton("+ New Chat")
        new_chat.setObjectName("newChatBtn")
        new_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        new_chat.setFont(QFont(FF, 9, QFont.Weight.Bold))
        new_chat.setFixedHeight(32)
        new_chat.setStyleSheet(f"""
            #newChatBtn {{
                background: {C['new_chat_bg']};
                color: {C['accent']};
                border: 1px solid {C['badge_bdr']};
                border-radius: 8px;
                padding: 0 14px;
                letter-spacing: 0.5px;
            }}
            #newChatBtn:hover {{
                background: {C['accent_dim']};
                color: white;
                border-color: {C['accent_mid']};
            }}
            #newChatBtn:pressed {{
                background: {C['accent_mid']};
                color: white;
            }}
        """)
        new_chat.clicked.connect(self.new_chat_requested.emit)
        right_layout.addWidget(new_chat)

        layout.addLayout(right_layout)

    def paintEvent(self, event):
        """Override paint to draw the gradient accent line at the bottom."""
        super().paintEvent(event)
        from PyQt6.QtGui import QPainter, QLinearGradient as QGrad
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        grad = QGrad(0, self.height() - 2, self.width(), self.height())
        grad.setColorAt(0.0, QColor(C["accent_dim"]).darker(150))
        grad.setColorAt(0.3, QColor(C["accent_mid"]))
        grad.setColorAt(0.5, QColor(C["send_btn"]))
        grad.setColorAt(0.7, QColor(C["accent_mid"]))
        grad.setColorAt(1.0, QColor(C["accent_dim"]).darker(150))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawRect(0, self.height() - 2, self.width(), 2)
        painter.end()


# ══════════════════════════════════════════════════════════════════════════════
# Input bar
# ══════════════════════════════════════════════════════════════════════════════
class InputBar(QWidget):
    submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inputBar")
        self.setStyleSheet(f"#inputBar {{ background:{C['input_area_bg']}; }}")
        self._build()

    def _build(self):
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setSpacing(0)

        # top gradient divider
        line = QFrame()
        line.setObjectName("inputDivider")
        line.setFixedHeight(1)
        line.setStyleSheet(f"""
            #inputDivider {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent, stop:0.2 {C['divider']},
                    stop:0.5 {C['accent_dim']}, stop:0.8 {C['divider']},
                    stop:1 transparent);
            }}
        """)
        wrapper.addWidget(line)

        row = QHBoxLayout()
        row.setContentsMargins(24, 14, 24, 14)
        row.setSpacing(14)

        self._min_height = 54
        self._max_height = 160

        self.field = QTextEdit()
        self.field.setObjectName("chatInput")
        self.field.setPlaceholderText("Ask a Text Mining question...")
        self.field.setMinimumHeight(self._min_height)
        self.field.setMaximumHeight(self._min_height)
        self.field.setFont(QFont(FF, 13))
        self.field.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.field.installEventFilter(self)
        self.field.setStyleSheet(f"""
            #chatInput {{
                background: {C['input_field']};
                color: {C['text_primary']};
                border: 1.5px solid {C['input_border']};
                border-radius: 27px;
                padding: 12px 24px;
                font-size: 13pt;
                selection-background-color: {C['accent_dim']};
                letter-spacing: 0.2px;
            }}
            #chatInput:focus {{
                border-color: {C['input_focus']};
                background: #0e0e28;
            }}
            #chatInput:disabled {{
                background: {C['send_dis']};
                color: {C['text_hint']};
            }}
        """)
        self.field.textChanged.connect(self._auto_grow)

        self.send_btn = QPushButton("Send  ➤")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setFixedSize(QSize(108, 54))
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFont(QFont(FF, 10, QFont.Weight.Bold))
        self.send_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.send_btn.setStyleSheet(f"""
            #sendBtn {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {C['grad_start']}, stop:1 {C['grad_end']});
                color: white;
                border-radius: 26px;
                border: none;
                letter-spacing: 0.8px;
                font-weight: 700;
            }}
            #sendBtn:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {C['send_hover']}, stop:1 #8b5cf6);
            }}
            #sendBtn:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4338ca, stop:1 #6d28d9);
            }}
            #sendBtn:disabled {{
                background: {C['send_dis']};
                color: {C['text_hint']};
            }}
        """)
        self.send_btn.clicked.connect(self._emit)

        self._send_shadow = QGraphicsDropShadowEffect()
        self._send_shadow.setBlurRadius(16)
        self._send_shadow.setColor(QColor(C["glow_user"]))
        self._send_shadow.setOffset(0, 3)
        self.send_btn.setGraphicsEffect(self._send_shadow)

        row.addWidget(self.field, 1)  # stretch=1 so field takes all space
        row.addWidget(self.send_btn, 0, Qt.AlignmentFlag.AlignVCenter)  # fixed size, vertically centered

        hint = QLabel("Enter to send  ·  Shift+Enter for new line")
        hint.setObjectName("inputHint")
        hint.setFont(QFont(FF, 8))
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"""
            #inputHint {{
                color: {C['text_hint']};
                background: transparent;
                border: none;
                padding-bottom: 8px;
                letter-spacing: 0.5px;
            }}
        """)

        wrapper.addLayout(row)
        wrapper.addWidget(hint)

    def _auto_grow(self):
        """Expand the input field height as the user types multiple lines."""
        doc = self.field.document()
        # Calculate the height the document needs
        doc_height = int(doc.size().height())
        # Add padding for border + internal margins
        new_height = doc_height + 28
        # Clamp between min and max
        new_height = max(self._min_height, min(new_height, self._max_height))
        self.field.setFixedHeight(new_height)

    def eventFilter(self, obj, event: QEvent):
        if obj is self.field and event.type() == QEvent.Type.KeyPress:
            key   = event.key()
            mods  = event.modifiers()
            if key == Qt.Key.Key_Return and not (mods & Qt.KeyboardModifier.ShiftModifier):
                self._emit()
                return True
        return super().eventFilter(obj, event)

    def _emit(self):
        text = self.field.toPlainText().strip()
        if text:
            self.submitted.emit(text)
            self.field.clear()
            # Reset height after clearing
            self.field.setFixedHeight(self._min_height)

    def set_enabled(self, enabled: bool):
        self.field.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self._send_shadow.setEnabled(enabled)
        if enabled:
            self.field.setFocus()


# ══════════════════════════════════════════════════════════════════════════════
# Welcome card  —  with CLICKABLE suggestion chips
# ══════════════════════════════════════════════════════════════════════════════
class WelcomeCard(QWidget):
    suggestion_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(48, 20, 48, 20)

        frame = QFrame()
        frame.setObjectName("welcomeFrame")
        frame.setStyleSheet(f"""
            #welcomeFrame {{
                background: {C['welcome_bg']};
                border: 1px solid {C['welcome_bdr']};
                border-radius: 20px;
            }}
        """)

        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(24)
        glow.setColor(QColor(C["welcome_glow"] + "30"))
        glow.setOffset(0, 4)
        frame.setGraphicsEffect(glow)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(32, 28, 32, 28)
        frame_layout.setSpacing(10)
        frame_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon in a gradient circle
        icon_bg = QLabel("📚")
        icon_bg.setObjectName("welcomeIcon")
        icon_bg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_bg.setFont(QFont(FF, 28))
        icon_bg.setFixedSize(64, 64)
        icon_bg.setStyleSheet(f"""
            #welcomeIcon {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {C['accent_mid']}, stop:1 {C['grad_end']});
                border: none;
                border-radius: 32px;
                color: white;
            }}
        """)
        frame_layout.addWidget(icon_bg, 0, Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Welcome to TM Lecture Assistant")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont(FF, 14, QFont.Weight.Bold))
        title.setStyleSheet(f"""
            #welcomeTitle {{
                color: {C['text_primary']};
                background: transparent;
                border: none;
                letter-spacing: 0.5px;
            }}
        """)
        frame_layout.addWidget(title)

        desc = QLabel(
            "I'm your AI-powered Text Mining teaching assistant.\n"
            "Ask me anything about TM lectures, concepts, or slides\n"
            "and I'll search the knowledge base to help you learn."
        )
        desc.setObjectName("welcomeDesc")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setFont(QFont(FF, 10))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"""
            #welcomeDesc {{
                color: {C['text_muted']};
                background: transparent;
                border: none;
                line-height: 1.7;
                letter-spacing: 0.2px;
            }}
        """)
        frame_layout.addWidget(desc)

        frame_layout.addSpacing(8)

        # Section label
        section_lbl = QLabel("TRY ASKING")
        section_lbl.setObjectName("sectionLabel")
        section_lbl.setFont(QFont(FF, 8, QFont.Weight.Bold))
        section_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        section_lbl.setStyleSheet(f"""
            #sectionLabel {{
                color: {C['accent']};
                background: transparent;
                border: none;
                letter-spacing: 2px;
            }}
        """)
        frame_layout.addWidget(section_lbl)

        # Clickable suggestion chips — full-width stacked
        suggestions = [
            ("How do I classify customer reviews as positive or negative using a sentiment dictionary?", "📝"),
            ("What is the difference between constituency parsing and dependency parsing?", "🔀"),
            ("How can LLMs be used to build a knowledge graph from unstructured text?", "🧠"),
            ("What is the difference between bagging and boosting, and when should I use each?", "⚖️"),
        ]

        chips_col = QVBoxLayout()
        chips_col.setSpacing(8)
        chips_col.setContentsMargins(0, 0, 0, 0)

        for text, emoji in suggestions:
            chip = QPushButton(f"  {emoji}  {text}")
            chip.setObjectName("suggestionChip")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setFont(QFont(FF, 9))
            chip.setFixedHeight(40)
            chip.setStyleSheet(f"""
                #suggestionChip {{
                    background: {C['input_field']};
                    color: {C['accent']};
                    border: 1px solid {C['bot_border']};
                    border-radius: 10px;
                    padding: 0 18px;
                    font-weight: 500;
                    letter-spacing: 0.3px;
                    text-align: left;
                }}
                #suggestionChip:hover {{
                    background: {C['nav_hover']};
                    border-color: {C['accent_mid']};
                    color: {C['text_primary']};
                }}
                #suggestionChip:pressed {{
                    background: {C['accent_dim']};
                    color: white;
                }}
            """)
            chip.clicked.connect(lambda checked, t=text: self.suggestion_clicked.emit(t))
            chips_col.addWidget(chip)

        frame_layout.addLayout(chips_col)
        outer_layout.addWidget(frame)


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
        self._welcome: WelcomeCard | None = None
        self._build_ui()
        self._apply_global_style()
        self._show_welcome()

    def _apply_global_style(self):
        # Use object-name selectors to avoid overriding child widget styles
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {C['app_bg']};
                font-family: "{FF}", "Noto Sans SC", system-ui;
            }}
            QScrollArea {{
                border: none;
                background: {C['chat_bg']};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 5px;
                margin: 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['scrollbar']};
                border-radius: 2.5px;
                min-height: 32px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {C['accent_dim']};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; border: 0; }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{ background: none; }}
        """)

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("rootWidget")
        root.setStyleSheet(f"#rootWidget {{ background: {C['app_bg']}; }}")

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # header
        header = HeaderBar()
        header.setObjectName("headerBarOuter")
        header.setStyleSheet(f"""
            #headerBarOuter {{
                background: {C['header_bg']};
                border-bottom: none;
            }}
        """)
        header.new_chat_requested.connect(self._new_chat)
        root_layout.addWidget(header)

        # scrollable chat area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.chat_container = QWidget()
        self.chat_container.setObjectName("chatContainer")
        self.chat_container.setStyleSheet(f"#chatContainer {{ background:{C['chat_bg']}; }}")

        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(0, 20, 0, 20)
        self.chat_layout.setSpacing(4)
        self.chat_layout.addStretch()

        self.scroll.setWidget(self.chat_container)
        root_layout.addWidget(self.scroll, stretch=1)

        # input bar
        self.input_bar = InputBar()
        self.input_bar.submitted.connect(self._on_submit)
        root_layout.addWidget(self.input_bar)

        self.setCentralWidget(root)

    def _show_welcome(self):
        self._welcome = WelcomeCard()
        self._welcome.suggestion_clicked.connect(self._on_suggestion)
        self.chat_layout.addWidget(self._welcome)

    def _on_suggestion(self, text: str):
        """Handle clicking a suggestion chip — send it as a query."""
        self._on_submit(text)

    def _new_chat(self):
        """Clear chat and show welcome again."""
        # Remove all widgets from chat layout (except the stretch)
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
            layout = item.layout()
            if layout:
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().setParent(None)
        self.chat_layout.addStretch()
        self._show_welcome()

    def _on_submit(self, query: str):
        # Remove welcome card on first message
        if self._welcome:
            self._welcome.setParent(None)
            self._welcome = None

        self._add_bubble(query, is_user=True)
        self.input_bar.set_enabled(False)

        self._typing = TypingIndicator()
        self.chat_layout.addWidget(self._typing)
        QTimer.singleShot(30, self._scroll_to_bottom)

        self._worker = GenerateWorker(query)
        self._worker.finished.connect(self._on_success)
        self._worker.errored.connect(self._on_error)
        self._worker.start()

    def _on_success(self, text: str):
        self._remove_typing()
        self._add_bubble(text, is_user=False)
        self.input_bar.set_enabled(True)

    def _on_error(self, msg: str):
        self._remove_typing()
        self._add_bubble(f"  {msg}", is_user=False, is_error=True)
        self.input_bar.set_enabled(True)

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

    palette = app.palette()
    palette.setColor(palette.ColorRole.Window,          QColor(C["app_bg"]))
    palette.setColor(palette.ColorRole.WindowText,      QColor(C["text_primary"]))
    palette.setColor(palette.ColorRole.Base,            QColor(C["input_field"]))
    palette.setColor(palette.ColorRole.Text,            QColor(C["text_primary"]))
    palette.setColor(palette.ColorRole.Button,          QColor(C["send_btn"]))
    palette.setColor(palette.ColorRole.ButtonText,      QColor("#ffffff"))
    palette.setColor(palette.ColorRole.Highlight,       QColor(C["accent_dim"]))
    palette.setColor(palette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = ChatWindow()
    window.show()
    sys.exit(app.exec())
