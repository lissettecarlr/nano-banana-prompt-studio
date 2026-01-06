"""应用样式表 - 极简白色主题"""

# ========== 颜色变量 ==========
# 背景色
BG_PRIMARY = "#FFFFFF"       # 主背景 - 纯白
BG_SECONDARY = "#FAFAFA"     # 次要背景 - 极浅灰
BG_TERTIARY = "#F5F5F5"      # 第三背景 - 浅灰

# 边框色
BORDER_LIGHT = "#D0D0D0"     # 轻边框（加深）
BORDER_DEFAULT = "#C8C8C8"   # 默认边框（加深）
BORDER_FOCUS = "#A0A0A0"     # 聚焦边框

# 文字色
TEXT_PRIMARY = "#2B2B2B"     # 主文字 - 深灰（非纯黑，更柔和）
TEXT_SECONDARY = "#757575"   # 次要文字 - 中灰
TEXT_MUTED = "#9E9E9E"       # 弱化文字 - 浅灰

# 强调色 - 使用温暖的金棕色作为点睛
ACCENT = "#B8956B"           # 金棕色强调
ACCENT_LIGHT = "#D4B896"     # 浅金棕
ACCENT_HOVER = "#A07D52"     # 深金棕 hover

# 交互色
HOVER_BG = "#F7F7F7"         # hover 背景
ACTIVE_BG = "#F0F0F0"        # active 背景
SELECTION_BG = "#FBF7F2"     # 选中背景（带点暖色）

LIGHT_THEME = f"""
/* ========================================
   全局重置 - 完全覆盖系统样式
   ======================================== */

* {{
    font-family: "Microsoft YaHei", "PingFang SC", "SF Pro Text", system-ui, sans-serif;
    outline: none;
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
}}

/* 主窗口 */
QMainWindow {{
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
}}

QMainWindow > QWidget {{
    background-color: {BG_PRIMARY};
}}

QWidget {{
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    font-size: 13px;
    selection-background-color: {SELECTION_BG};
    selection-color: {TEXT_PRIMARY};
}}

/* ========================================
   滚动区域
   ======================================== */

QScrollArea {{
    border: none;
    background-color: {BG_PRIMARY};
}}

QScrollArea > QWidget > QWidget {{
    background-color: {BG_PRIMARY};
}}

QScrollBar:vertical {{
    background-color: {BG_PRIMARY};
    width: 8px;
    margin: 4px 2px;
}}

QScrollBar::handle:vertical {{
    background-color: {BORDER_DEFAULT};
    border-radius: 4px;
    min-height: 40px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {BORDER_FOCUS};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
    height: 0;
    border: none;
}}

QScrollBar:horizontal {{
    background-color: {BG_PRIMARY};
    height: 8px;
    margin: 2px 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: {BORDER_DEFAULT};
    border-radius: 4px;
    min-width: 40px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {BORDER_FOCUS};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: transparent;
    width: 0;
    border: none;
}}

/* ========================================
   字段分组卡片
   ======================================== */

#fieldGroup {{
    background-color: {BG_PRIMARY};
    border: 2px solid {BORDER_DEFAULT};
    border-radius: 8px;
    padding: 0;
}}

#groupTitle {{
    color: {TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 0 0 8px 0;
    border: none;
    border-bottom: 2px solid {BORDER_DEFAULT};
}}

/* 主分类标题颜色 - 区分不同分类 */
#groupTitle_basic {{
    color: #6366F1;  /* 靛蓝色 - 基础设置 */
    border-bottom-color: #C7D2FE;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 0 0 8px 0;
    border: none;
    border-bottom: 2px solid #C7D2FE;
}}

#groupTitle_scene {{
    color: #059669;  /* 绿色 - 场景设置 */
    border-bottom-color: #A7F3D0;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 0 0 8px 0;
    border: none;
    border-bottom: 2px solid #A7F3D0;
}}

#groupTitle_subject {{
    color: #DB2777;  /* 玫瑰色 - 主体细节 */
    border-bottom-color: #FBCFE8;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 0 0 8px 0;
    border: none;
    border-bottom: 2px solid #FBCFE8;
}}

#groupTitle_camera {{
    color: #D97706;  /* 橙色 - 相机与构图 */
    border-bottom-color: #FDE68A;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 0 0 8px 0;
    border: none;
    border-bottom: 2px solid #FDE68A;
}}

#groupTitle_aesthetic {{
    color: #7C3AED;  /* 紫色 - 审美控制 */
    border-bottom-color: #DDD6FE;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 0 0 8px 0;
    border: none;
    border-bottom: 2px solid #DDD6FE;
}}

#groupTitle_aspect {{
    color: #64748B;  /* 灰蓝色 - 画幅设置 */
    border-bottom-color: #CBD5E1;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 0 0 8px 0;
    border: none;
    border-bottom: 2px solid #CBD5E1;
}}

#groupTitle_negative {{
    color: #DC2626;  /* 红色 - 反向提示词 */
    border-bottom-color: #FECACA;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 0 0 8px 0;
    border: none;
    border-bottom: 2px solid #FECACA;
}}

#groupTitle_special {{
    color: #0891B2;  /* 青色 - 特别要求 */
    border-bottom-color: #A5F3FC;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 0 0 8px 0;
    border: none;
    border-bottom: 2px solid #A5F3FC;
}}

#fieldLabel {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 500;
}}

/* ========================================
   下拉框 (ComboBox)
   ======================================== */

QComboBox {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
    padding: 8px 12px;
    padding-right: 32px;
    color: {TEXT_PRIMARY};
    min-height: 20px;
}}

QComboBox:hover {{
    border-color: {BORDER_FOCUS};
}}

QComboBox:focus {{
    border-color: {ACCENT};
}}

QComboBox:disabled {{
    background-color: {BG_SECONDARY};
    color: {TEXT_MUTED};
}}

QComboBox::drop-down {{
    border: none;
    width: 28px;
    background-color: {BG_PRIMARY};
}}

QComboBox::down-arrow {{
    image: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {TEXT_SECONDARY};
    margin-right: 8px;
}}

QComboBox::down-arrow:hover {{
    border-top-color: {ACCENT};
}}

QComboBox QAbstractItemView {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
    padding: 4px;
    outline: none;
    selection-background-color: transparent;
}}

QComboBox QAbstractItemView::item {{
    padding: 8px 12px;
    border-radius: 4px;
    color: {TEXT_PRIMARY};
    background-color: {BG_PRIMARY};
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: {HOVER_BG};
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {SELECTION_BG};
    color: {ACCENT_HOVER};
}}

/* ========================================
   输入框 (LineEdit)
   ======================================== */

QLineEdit {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
    padding: 8px 12px;
    color: {TEXT_PRIMARY};
    selection-background-color: {SELECTION_BG};
}}

QLineEdit:hover {{
    border-color: {BORDER_FOCUS};
}}

QLineEdit:focus {{
    border-color: {ACCENT};
}}

QLineEdit:disabled {{
    background-color: {BG_SECONDARY};
    color: {TEXT_MUTED};
}}

/* ========================================
   按钮
   ======================================== */

QPushButton {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
    padding: 8px 16px;
    color: {TEXT_PRIMARY};
    font-weight: 500;
    min-height: 18px;
}}

QPushButton:hover {{
    background-color: {HOVER_BG};
    border-color: {BORDER_FOCUS};
}}

QPushButton:pressed {{
    background-color: {ACTIVE_BG};
}}

QPushButton:disabled {{
    background-color: {BG_SECONDARY};
    color: {TEXT_MUTED};
    border-color: {BORDER_LIGHT};
}}

/* 主要按钮 - 实心强调色 */
#primaryButton {{
    background-color: {ACCENT};
    border: none;
    color: {BG_PRIMARY};
    font-weight: 600;
    padding: 10px 24px;
    font-size: 13px;
}}

#primaryButton:hover {{
    background-color: {ACCENT_HOVER};
}}

#primaryButton:pressed {{
    background-color: #8A6B42;
}}

/* ========================================
   复选框
   ======================================== */

QCheckBox {{
    spacing: 8px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 4px;
    background-color: {BG_PRIMARY};
}}

QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTAuNSAzTDQuNSA5TDEuNSA2IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==);
}}

#negativePromptToggle, #aspectToggle, #specialRequirementToggle, #lineArtModeToggle {{
    padding: 8px 0;
    margin-bottom: 4px;
    font-weight: 500;
}}

/* 次要按钮 - 边框强调 */
#secondaryButton {{
    background-color: {BG_PRIMARY};
    border: 1px solid {ACCENT};
    color: {ACCENT};
    padding: 9px 20px;
}}

#secondaryButton:hover {{
    background-color: {SELECTION_BG};
    border-color: {ACCENT_HOVER};
    color: {ACCENT_HOVER};
}}

/* 危险按钮 */
#dangerButton {{
    background-color: #DC3545;
    border: none;
    color: white;
}}

#dangerButton:hover {{
    background-color: #C82333;
}}

/* ========================================
   文本编辑区
   ======================================== */

QTextEdit, QPlainTextEdit {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
    padding: 12px;
    color: {TEXT_PRIMARY};
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 12px;
    selection-background-color: {SELECTION_BG};
}}

QTextEdit:hover, QPlainTextEdit:hover {{
    border-color: {BORDER_FOCUS};
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {ACCENT};
}}

/* ========================================
   标签页
   ======================================== */

QTabWidget::pane {{
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
    background-color: {BG_PRIMARY};
    top: -1px;
}}

QTabBar::tab {{
    background-color: {BG_SECONDARY};
    border: 1px solid {BORDER_DEFAULT};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 20px;
    margin-right: 2px;
    color: {TEXT_SECONDARY};
}}

QTabBar::tab:selected {{
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    font-weight: 500;
}}

QTabBar::tab:hover:!selected {{
    background-color: {HOVER_BG};
}}

/* ========================================
   分割器
   ======================================== */

QSplitter::handle {{
    background-color: {BORDER_LIGHT};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

QSplitter::handle:hover {{
    background-color: {ACCENT_LIGHT};
}}

/* ========================================
   标题区域
   ======================================== */

#appTitle {{
    color: {TEXT_PRIMARY};
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
}}

#appSubtitle {{
    color: {TEXT_MUTED};
    font-size: 12px;
    letter-spacing: 0.3px;
}}

#previewTitle {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 600;
    padding: 8px 0;
}}

/* ========================================
   预设选择器
   ======================================== */

#presetSelector {{
    background-color: {BG_PRIMARY};
    border: 1px solid {ACCENT_LIGHT};
    border-radius: 6px;
    padding: 8px 16px;
    color: {ACCENT_HOVER};
    font-weight: 500;
    min-width: 200px;
}}

#presetSelector:hover {{
    border-color: {ACCENT};
    background-color: {SELECTION_BG};
}}

#presetSelector:focus {{
    border-color: {ACCENT};
}}

#presetSelector::drop-down {{
    border: none;
    border-left: 1px solid {BORDER_LIGHT};
    width: 32px;
    background-color: {BG_PRIMARY};
}}

#presetSelector::down-arrow {{
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {ACCENT};
}}

#presetBar {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    padding: 8px 16px;
}}

#presetLabel {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

/* ========================================
   状态栏
   ======================================== */

QStatusBar {{
    background-color: {BG_PRIMARY};
    border-top: 1px solid {BORDER_LIGHT};
    color: {TEXT_MUTED};
    padding: 4px 12px;
    font-size: 12px;
}}

/* ========================================
   工具提示
   ======================================== */

QToolTip {{
    background-color: {TEXT_PRIMARY};
    border: none;
    border-radius: 4px;
    padding: 6px 10px;
    color: {BG_PRIMARY};
    font-size: 12px;
}}

/* ========================================
   对话框
   ======================================== */

QMessageBox {{
    background-color: {BG_PRIMARY};
}}

QMessageBox QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}

QMessageBox QPushButton {{
    min-width: 72px;
}}

QInputDialog {{
    background-color: {BG_PRIMARY};
}}

QInputDialog QLabel {{
    color: {TEXT_PRIMARY};
}}

QInputDialog QLineEdit {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
    padding: 8px 12px;
    color: {TEXT_PRIMARY};
}}

QInputDialog QLineEdit:focus {{
    border-color: {ACCENT};
}}

/* ========================================
   菜单
   ======================================== */

QMenu {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px 8px 12px;
    color: {TEXT_PRIMARY};
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {HOVER_BG};
    color: {TEXT_PRIMARY};
}}

QMenu::separator {{
    height: 1px;
    background-color: {BORDER_LIGHT};
    margin: 4px 8px;
}}

QMenu::indicator {{
    width: 16px;
    height: 16px;
    margin-left: 4px;
}}

/* ========================================
   Frame 边框
   ======================================== */

QFrame {{
    border: none;
}}

#presetBar {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_LIGHT};
}}

/* ========================================
   画幅设置组件
   ======================================== */

#aspectPresetBtn {{
    background-color: {BG_SECONDARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 18px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
    color: {TEXT_SECONDARY};
    min-width: 80px;
}}

#aspectPresetBtn:hover {{
    background-color: {HOVER_BG};
    border-color: {ACCENT_LIGHT};
    color: {TEXT_PRIMARY};
}}

#aspectPresetBtn:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: {BG_PRIMARY};
    font-weight: 600;
}}

#aspectPresetBtn:checked:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}

#aspectParamsContainer {{
    background-color: {BG_SECONDARY};
    border: 1px dashed {BORDER_DEFAULT};
    border-radius: 8px;
}}

#aspectFieldLabel {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 500;
}}

#aspectFieldCombo {{
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 6px;
    padding: 6px 10px;
    padding-right: 28px;
    font-size: 12px;
    min-height: 18px;
}}

#aspectFieldCombo:hover {{
    border-color: {BORDER_FOCUS};
}}

#aspectFieldCombo:focus {{
    border-color: {ACCENT};
}}

/* ========================================
   AI生成按钮 - 特殊强调样式
   ======================================== */

#aiGenerateButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #8B5CF6, stop:1 #A855F7);
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    color: white;
    font-weight: 600;
    font-size: 13px;
}}

#aiGenerateButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7C3AED, stop:1 #9333EA);
}}

#aiGenerateButton:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6D28D9, stop:1 #7E22CE);
}}
"""
