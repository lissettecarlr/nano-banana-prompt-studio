"""AI 连接配置对话框：对话模型 + 各图片渠道。

图片渠道列表、默认值和模型建议全部来自 Studio 的渠道声明，新增渠道不需要改这里。
"""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nano_banana.core import ProviderStatus, Studio

_DIALOG_STYLE = """
    QDialog {
        background-color: #f5f7fa;
    }
    QComboBox {
        padding: 8px 12px;
        border: 1px solid #d9d9d9;
        border-radius: 6px;
        background-color: white;
        min-height: 32px;
    }
    QComboBox:hover {
        border-color: #40a9ff;
    }
    QLineEdit, QTextEdit {
        padding: 8px;
        border: 1px solid #d9d9d9;
        border-radius: 6px;
        background-color: white;
    }
    QLineEdit:focus, QTextEdit:focus {
        border-color: #40a9ff;
    }
    QPushButton {
        padding: 8px 24px;
        border-radius: 6px;
        border: 1px solid #d9d9d9;
        background-color: #ffffff;
        font-size: 13px;
        min-width: 80px;
    }
    QPushButton:hover {
        border-color: #40a9ff;
        color: #40a9ff;
    }
    QPushButton#primaryButton {
        background-color: #1890ff;
        color: white;
        border: none;
        font-weight: 500;
    }
    QPushButton#primaryButton:hover {
        background-color: #40a9ff;
    }
"""

_SECTION_FRAME_STYLE = """
    QFrame#%(name)s {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 %(tint)s, stop:1 #ffffff);
        border: 2px solid %(accent)s;
        border-radius: 12px;
        padding: 4px;
    }
"""

_SECTION_TITLE_STYLE = """
    QWidget {
        background-color: %s;
        border-radius: 8px;
        padding: 12px;
    }
"""

_PROVIDER_LIST_STYLE = """
    QListWidget {
        background: transparent;
        border: none;
        outline: none;
        padding: 0;
    }
    QListWidget::item {
        background-color: #ffffff;
        border: 1px solid #e8e8e8;
        border-radius: 8px;
        color: #595959;
        padding: 9px 12px;
    }
    QListWidget::item:hover {
        background-color: #fffaf0;
        border-color: #ffc069;
    }
    QListWidget::item:selected {
        background-color: #fff7e6;
        border: 1px solid #fa8c16;
        color: #d46b08;
        font-weight: 600;
    }
"""

_CREDENTIAL_KEYS = ("base_url", "api_key", "model")


class UnifiedAIConfigDialog(QDialog):
    """分别管理 AI 对话和图片生成连接配置。"""

    config_saved = pyqtSignal()

    def __init__(
        self,
        studio: Studio,
        parent=None,
        initial_tab: str = "chat",
        image_provider: str | None = None,
    ):
        super().__init__(parent)
        self.studio = studio
        self._providers: dict[str, ProviderStatus] = {
            status.id: status for status in studio.provider_statuses()
        }
        self._image_drafts: dict[str, dict[str, str]] = {}
        self._current_image_provider: str | None = None
        self._initial_tab = initial_tab
        self._requested_image_provider = image_provider
        self._setup_ui()
        self._load_config()

    # ================= 界面 =================

    def _setup_ui(self):
        self.setWindowTitle("AI 配置")
        self.setMinimumWidth(600)
        self.setModal(True)
        self.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        title = QLabel("AI 配置")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #262626;")
        layout.addWidget(title)

        description = QLabel("对话模型与图片生成渠道完全独立，配置不会互相复用。")
        description.setStyleSheet("color: #8c8c8c; font-size: 12px;")
        layout.addWidget(description)

        self.config_tabs = QTabWidget()
        self.config_tabs.addTab(self._create_chat_tab(), "AI 对话")
        self.config_tabs.addTab(self._create_image_tab(), "图片生成")
        self.config_tabs.setCurrentIndex(1 if self._initial_tab == "image" else 0)
        layout.addWidget(self.config_tabs, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("保存配置")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _create_chat_tab(self) -> QFrame:
        frame, layout = _section_frame(
            "promptConfigFrame",
            "提示词生成/修改 AI",
            "用于 AI 生成/修改提示词，采用 OpenAI-compatible 接口。",
            accent="#1890ff",
            tint="#f0f7ff",
        )
        self.prompt_url_input = QLineEdit()
        self.prompt_url_input.setPlaceholderText("https://api.openai.com/v1")
        self.prompt_key_input = _secret_input()
        self.prompt_model_input = QLineEdit()
        self.prompt_model_input.setPlaceholderText("gpt-5.1")
        layout.addWidget(_labeled("Base URL", self.prompt_url_input))
        layout.addWidget(_labeled("API Key", self.prompt_key_input))
        layout.addWidget(_labeled("模型名称", self.prompt_model_input))
        return frame

    def _create_image_tab(self) -> QFrame:
        frame, layout = _section_frame(
            "imageConfigFrame",
            "图片生成 AI",
            "这里只管理各图片渠道的连接信息；当前使用渠道请在主界面切换。",
            accent="#fa8c16",
            tint="#fff7e6",
        )

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(16)

        nav = QWidget()
        nav.setFixedWidth(190)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)
        nav_title = QLabel("图片渠道")
        nav_title.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #8c8c8c; padding-left: 4px;"
        )
        nav_layout.addWidget(nav_title)

        self.image_provider_input = QListWidget()
        self.image_provider_input.setSpacing(6)
        self.image_provider_input.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.image_provider_input.setStyleSheet(_PROVIDER_LIST_STYLE)
        for status in self._providers.values():
            item = QListWidgetItem(status.label)
            item.setSizeHint(QSize(0, 54))
            item.setData(Qt.ItemDataRole.UserRole, status.id)
            self.image_provider_input.addItem(item)
        self.image_provider_input.currentRowChanged.connect(self._on_image_provider_changed)
        nav_layout.addWidget(self.image_provider_input, 1)
        body_layout.addWidget(nav)

        fields = QWidget()
        fields_layout = QVBoxLayout(fields)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(16)
        self.image_url_input = QLineEdit()
        self.image_key_input = _secret_input()
        self.image_model_input = QComboBox()
        self.image_model_input.setEditable(True)
        fields_layout.addWidget(_labeled("Base URL", self.image_url_input))
        fields_layout.addWidget(_labeled("API Key", self.image_key_input))
        fields_layout.addWidget(_labeled("模型名称", self.image_model_input))
        body_layout.addWidget(fields, 1)

        layout.addWidget(body, 1)
        return frame

    # ================= 读写 =================

    def _load_config(self):
        chat = self.studio.chat_settings()
        self.prompt_url_input.setText(chat.base_url)
        self.prompt_key_input.setText(chat.api_key)
        self.prompt_model_input.setText(chat.model)

        # 草稿里 base_url / model 已用渠道默认值补齐，方便用户直接填密钥
        for provider_id in self._providers:
            credentials = self.studio.settings.credentials(provider_id)
            self._image_drafts[provider_id] = {
                "base_url": credentials.base_url,
                "api_key": credentials.api_key,
                "model": credentials.model,
            }
        self._refresh_provider_labels()

        provider = self._requested_image_provider or self.studio.settings.active_provider()
        row = next(
            (
                index
                for index in range(self.image_provider_input.count())
                if self._provider_at(index) == provider
            ),
            0,
        )
        if self.image_provider_input.currentRow() == row:
            self._on_image_provider_changed()
        else:
            self.image_provider_input.setCurrentRow(row)

    def _provider_at(self, row: int) -> str | None:
        item = self.image_provider_input.item(row)
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _refresh_provider_labels(self) -> None:
        for row in range(self.image_provider_input.count()):
            provider = self._provider_at(row)
            draft = self._image_drafts.get(provider, {})
            configured = all(draft.get(key, "").strip() for key in _CREDENTIAL_KEYS)
            status = "✓ 已配置" if configured else "未配置"
            self.image_provider_input.item(row).setText(
                f"{self._providers[provider].label}\n{status}"
            )

    def _stash_current_draft(self) -> None:
        """把输入框里的值收进当前渠道的草稿，切换渠道时不丢编辑。"""
        if self._current_image_provider in self._image_drafts:
            self._image_drafts[self._current_image_provider] = {
                "base_url": self.image_url_input.text(),
                "api_key": self.image_key_input.text(),
                "model": self.image_model_input.currentText(),
            }

    def _on_image_provider_changed(self, _row: int = -1):
        self._stash_current_draft()
        self._refresh_provider_labels()

        provider = self._provider_at(self.image_provider_input.currentRow())
        self._current_image_provider = provider
        if provider is None:
            return
        status = self._providers[provider]
        draft = self._image_drafts[provider]

        self.image_url_input.setPlaceholderText(status.url_placeholder)
        self.image_url_input.setText(draft["base_url"])
        self.image_key_input.setText(draft["api_key"])

        self.image_model_input.blockSignals(True)
        self.image_model_input.clear()
        self.image_model_input.addItems(list(status.model_suggestions))
        index = self.image_model_input.findText(draft["model"])
        if index >= 0:
            self.image_model_input.setCurrentIndex(index)
        else:
            self.image_model_input.setEditText(draft["model"])
        self.image_model_input.blockSignals(False)

    def _save_config(self):
        self._stash_current_draft()
        patch = {
            "chat": {
                "base_url": self.prompt_url_input.text().strip(),
                "api_key": self.prompt_key_input.text().strip(),
                "model": self.prompt_model_input.text().strip(),
            },
            "image": {
                "providers": {
                    provider_id: {key: draft[key].strip() for key in _CREDENTIAL_KEYS}
                    for provider_id, draft in self._image_drafts.items()
                }
            },
        }
        try:
            self.studio.settings.update(patch)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "错误", f"保存配置失败，请重试\n{exc}")
            return
        self.config_saved.emit()
        self.accept()


def _secret_input() -> QLineEdit:
    """密码输入框，右侧带显示/隐藏切换。"""
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setPlaceholderText("sk-...")
    action = QAction("显示", field)
    field.addAction(action, QLineEdit.ActionPosition.TrailingPosition)

    def toggle(_checked=False):
        hidden = field.echoMode() == QLineEdit.EchoMode.Password
        field.setEchoMode(QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password)
        action.setText("隐藏" if hidden else "显示")

    action.triggered.connect(toggle)
    return field


def _labeled(label_text: str, widget: QWidget) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    label = QLabel(label_text)
    label.setStyleSheet("font-weight: 600; font-size: 13px; color: #262626;")
    layout.addWidget(label)
    layout.addWidget(widget)
    return container


def _section_frame(
    name: str, title_text: str, hint_text: str, *, accent: str, tint: str
) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName(name)
    frame.setStyleSheet(_SECTION_FRAME_STYLE % {"name": name, "accent": accent, "tint": tint})
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(16)

    title_container = QWidget()
    title_container.setStyleSheet(_SECTION_TITLE_STYLE % accent)
    title_layout = QHBoxLayout(title_container)
    title_layout.setContentsMargins(0, 0, 0, 0)
    title_layout.setSpacing(10)
    title = QLabel(title_text)
    title.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
    title_layout.addWidget(title)
    title_layout.addStretch()
    layout.addWidget(title_container)

    hint = QLabel(hint_text)
    hint.setWordWrap(True)
    hint.setStyleSheet("color: #595959; font-size: 12px;")
    layout.addWidget(hint)
    return frame, layout
