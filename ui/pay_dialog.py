# -*- coding: utf-8 -*-
"""
支付对话框 - 顶级 UI 终极版 (暗黑深空光斑 + 果冻卡片 + 纯净毛玻璃 + 窗口等比缩放)
"""
import qrcode
import random
import math

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QGraphicsDropShadowEffect,
    QTextBrowser, QApplication
)
from PySide6.QtGui import (
    QPixmap, QImage, QColor, QFont, QPainter, QPainterPath, QRadialGradient
)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QVariantAnimation, QEasingCurve

from qfluentwidgets import (
    setTheme, Theme, setThemeColor,
    TransparentToolButton, RoundMenu, Action,
)
from qfluentwidgets import FluentIcon as FIF

# --- 业务逻辑导入 (绝对保留) ---
from license.machine_code import get_machine_code
from license.activation import activate_with_code, check_activation
from datetime import datetime
from license import api_client
from license.cache_manager import save_plans_cache
from utils.config import sc, wsc

# 设计稿基准尺寸
_PAY_BASE_W = 760
_PAY_BASE_H = 740


# ────────── 会员服务协议 ──────────
AGREEMENT_HTML = """
<html><body style="font-family: 'Microsoft YaHei'; color: #e0e0e0; font-size: 15px; line-height: 2.0; padding: 10px;">
<h2 style="text-align: center; color: #00d9ff; font-size: 18px;">录屏王用户服务协议</h2>
<p style="text-align: center; color: #888; font-size: 14px;">更新日期：2026年4月</p>
<p style="color: #ff8c00; font-size: 16px; font-weight: bold;">重要须知：请您在使用录屏王软件及服务前，认真阅读本协议全部条款。您一旦使用本软件，即视为已充分理解并同意接受本协议的约束。如您不同意本协议任何条款，请勿使用本软件。</p>

<p><b style="color:#ff8c00; font-size: 16px;">一、服务内容</b></p>
<p>1.1 录屏王是一款 Windows 平台屏幕录制工具，提供全屏录制、区域录制、多显示器录制等功能。</p>
<p>1.2 部分功能需购买会员后方可使用。会员类型、价格及权益以购买时页面展示的内容为准。</p>
<p>1.3 我们有权根据产品规划对服务内容进行更新、调整或优化，届时将以软件内公告等方式通知用户。</p>

<p><b style="color:#ff8c00; font-size: 16px;">二、用户权利</b></p>
<p>2.1 用户在购买会员并获得合法授权后，有权在授权期限及授权设备范围内使用录屏王的会员功能。</p>
<p>2.2 用户获得的授权为有限的、非独占的、不可转让的使用许可，用户不因此获得软件的所有权。</p>
<p>2.3 用户须妥善保管自己的激活码及授权信息，因用户自身原因导致授权信息泄露或被他人使用，我们不承担任何责任。</p>
<p>2.4 用户不得对本软件进行反编译、反汇编、修改、破解或以其他方式试图获取软件源代码，不得将会员服务通过借用、租用、转让、售卖等方式提供他人使用。</p>

<p><b style="color:#ff8c00; font-size: 16px;">三、免责声明</b></p>
<p>3.1 本软件按"现状"提供，我们不对其作任何明示或暗示的担保，包括但不限于适销性、特定用途的适用性及非侵权性。</p>
<p>3.2 因不可抗力、计算机病毒、黑客攻击、系统故障、网络中断等原因导致的服务中断或数据损失，我们不承担责任。</p>
<p>3.3 用户使用本软件录制的内容由用户自行负责。用户应确保其录制行为符合相关法律法规，不得利用本软件侵犯他人合法权益。因用户使用不当产生的任何纠纷及损失，由用户自行承担全部责任。</p>
<p>3.4 在法律允许的最大范围内，我们对用户因使用本软件而遭受的任何直接或间接损失不承担赔偿责任。</p>

<p><b style="color:#ff8c00; font-size: 16px;">四、知识产权</b></p>
<p>4.1 录屏王软件的所有权及知识产权（包括但不限于著作权、商标权、专利权）均归我们所有，受中华人民共和国知识产权法律法规及国际公约保护。</p>
<p>4.2 未经我们书面许可，用户不得以任何形式复制、传播、展示、修改本软件或其任何部分，不得删除或篡改软件中的知识产权声明。</p>
<p>4.3 用户使用本软件生成的视频文件，其知识产权归用户所有。我们不对其内容承担任何审查义务。</p>

<p><b style="color:#ff8c00; font-size: 16px;">五、退款政策</b></p>
<p>5.1 会员服务属于数字化虚拟服务，用户购买后会员权益即时生效。</p>
<p>5.2 因会员服务的虚拟商品性质，购买后原则上不予退款。但以下情形除外：</p>
<p>&nbsp;&nbsp;&nbsp;&nbsp;（1）因系统故障导致用户多次被扣款，对重复扣款部分予以退还；</p>
<p>&nbsp;&nbsp;&nbsp;&nbsp;（2）因我方原因导致会员服务自购买之日起七日内无法正常使用的，用户可申请全额退款。</p>
<p>5.3 退款申请请通过软件内客服渠道提交，我们将在核实后七个工作日内处理。</p>

<p><b style="color:#ff8c00; font-size: 16px;">六、协议变更</b></p>
<p>6.1 我们有权在必要时对本协议条款进行修订。修订后的协议将在软件内或官方渠道公布。</p>
<p>6.2 协议修订后，若用户继续使用本软件，则视为接受修订后的协议。如用户不同意变更内容，可停止使用本软件并申请注销授权。</p>
<p>6.3 本协议的订立、执行、解释及争议解决均适用中华人民共和国法律。如发生争议，双方应友好协商解决；协商不成的，任何一方均可向我们所在地有管辖权的人民法院提起诉讼。</p>

<p style="text-align: center; color: #666; margin-top: 16px; font-size: 14px;">— 录屏王 版权所有 —</p>
</body></html>
"""

class AnimatedPriceLabel(QLabel):
    """支持数字丝滑滚动动画的金额标签"""
    def __init__(self, zoom=1.0, parent=None):
        super().__init__("￥0.00", parent)
        self._zoom = zoom
        self._current_val = 0.0
        self._target_val = 0.0

        font_price = int(wsc(36, zoom))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "color: #00d9ff; font-size: %dpx; font-weight: bold; background: transparent; outline: none;" % font_price
        )

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(400)  # 动画持续 400 毫秒
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic) # 缓动效果：先快后慢，更自然
        self._anim.valueChanged.connect(self._on_value_changed)

    def set_price(self, target_price: float, animate=True):
        # 【防抖核心】：如果目标价格和当前一模一样，直接拦截，绝对不乱跳！
        if self._target_val == target_price:
            return

        self._target_val = target_price

        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._current_val)
            self._anim.setEndValue(target_price)
            self._anim.start()
        else:
            self._anim.stop()
            self._current_val = target_price
            self.setText(f"￥{target_price:.2f}")

    def _on_value_changed(self, val):
        self._current_val = float(val)
        self.setText(f"￥{self._current_val:.2f}")
# ────────────────── 动态失焦光斑背景底层 ──────────────────
class BokehBackground(QWidget):
    """纯代码渲染的动态失焦光斑背景"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #1a1a2e; border-radius: 12px;")

        self._particles = []
        self._num_particles = 3
        self._colors = [
            QColor(0, 217, 255, 40),
            QColor(138, 43, 226, 30),
            QColor(255, 255, 255, 20),
            QColor(100, 149, 237, 35)
        ]

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_particles)
        self._timer.start(33)
        self._initialized = False

    def _init_particles(self, zoom=1.0):
        w, h = self.width(), self.height()
        if w == 0 or h == 0: return
        self._particles.clear()
        for _ in range(self._num_particles):
            radius = random.randint(wsc(80, zoom), wsc(220, zoom))
            x, y = random.randint(0, w), random.randint(0, h)
            vx, vy = random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)
            color = random.choice(self._colors)
            self._particles.append({'x': x, 'y': y, 'vx': vx, 'vy': vy, 'radius': radius, 'color': color})
        self._initialized = True

    def _update_particles(self):
        if not self._initialized: return
        w, h = self.width(), self.height()
        for p in self._particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            if p['x'] - p['radius'] > w or p['x'] + p['radius'] < 0: p['vx'] *= -1
            if p['y'] - p['radius'] > h or p['y'] + p['radius'] < 0: p['vy'] *= -1
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._initialized: self._init_particles()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._initialized: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self._particles:
            gradient = QRadialGradient(p['x'], p['y'], p['radius'])
            center_color = p['color']
            edge_color = QColor(center_color)
            edge_color.setAlpha(0)
            gradient.setColorAt(0, center_color)
            gradient.setColorAt(0.7, center_color)
            gradient.setColorAt(1, edge_color)
            painter.setBrush(gradient)
            painter.drawEllipse(int(p['x'] - p['radius']), int(p['y'] - p['radius']), int(p['radius'] * 2), int(p['radius'] * 2))


# ────────────────── 方案卡片 (Apple Dock 泡泡动效版) ──────────────────
class PlanCard(QWidget):
    """方案卡片 - 果冻呼吸动效"""

    def __init__(self, plan_data: dict, zoom=1.0, parent=None):
        super().__init__(parent)
        self._zoom = zoom
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.plan_data = plan_data
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        days = self.plan_data.get("duration_days", 0)
        try:
            days = int(days)
        except:
            days = 0

        self._is_annual = (days == 365)
        self._is_permanent = (days >= 9999)
        self._has_badge = self._is_annual or self._is_permanent

        self._build_ui()

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(350)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim.valueChanged.connect(self._on_anim_step)

        self._on_anim_step(0.0)
        self.setStyleSheet(
            "PlanCard { background-color: rgba(255, 255, 255, 0.04); border: 2px solid transparent; border-radius: 8px; }")

    def _build_ui(self):
        z = self._zoom
        layout = QHBoxLayout(self)
        layout.setContentsMargins(wsc(16, z), wsc(10, z), wsc(16, z), wsc(10, z))
        layout.setSpacing(wsc(4, z))

        days = self.plan_data.get("duration_days", 0)
        try:
            days = int(days)
        except:
            days = 0

        if days == 1:
            name_text = "单日体验包"
        elif days == 30:
            name_text = "月度畅享包"
        elif days == 180 or days == 90:
            name_text = "季度畅享包"
        elif days == 365:
            name_text = "年度畅享包"
        elif days >= 9999:
            name_text = "永久养老包"
        else:
            name_text = self.plan_data.get("name", "高级授权包")

        self._name_lbl = QLabel(name_text)
        layout.addWidget(self._name_lbl)
        layout.addStretch()

        right_vbox = QVBoxLayout()
        right_vbox.setSpacing(wsc(2, z))
        right_vbox.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        price_val = self.plan_data.get("price", "0")
        try:
            price_val = "{:.2f}".format(float(price_val))
        except:
            price_val = "0.00"

        self._price_lbl = QLabel(f"￥{price_val}")
        self._price_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_vbox.addWidget(self._price_lbl)

        if self._is_permanent:
            desc = "永久买断"
        elif days >= 365:
            desc = f"{days // 365}年授权"
        elif days > 0:
            desc = f"{days}天有效"
        else:
            desc = ""

        if desc:
            self._dur_lbl = QLabel(desc)
            self._dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            right_vbox.addWidget(self._dur_lbl)

        layout.addLayout(right_vbox)

        if self._has_badge:
            badge = QLabel("限时特惠", self)
            badge.setStyleSheet(
                "color: #ffffff; background-color: #e94560; font-size: 15px; font-weight: bold; "
                "border-top-left-radius: 8px; border-bottom-right-radius: 5px; "
                "padding: 1px 6px;"
            )
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.move(0, 0)

    def _on_anim_step(self, v: float):
        z = self._zoom
        # 高度：58(常态) -> 72(选中)
        h = int(wsc(58, z) + wsc(14, z) * v)
        self.setFixedHeight(h)
        name_sz = int(wsc(12, z) + wsc(3, z) * v)
        price_sz = int(wsc(19, z) + wsc(5, z) * v)
        self._name_lbl.setStyleSheet(
            f"color: #ffffff; font-size: {name_sz}px; font-weight: bold; background: transparent;")
        self._price_lbl.setStyleSheet(
            f"color: #ffffff; font-size: {price_sz}px; font-weight: bold; background: transparent;")
        if hasattr(self, '_dur_lbl'):
            dur_sz = int(wsc(10, z) + wsc(3, z) * v)
            self._dur_lbl.setStyleSheet(f"color: #999999; font-size: {dur_sz}px; background: transparent;")
        m_lr = int(wsc(16, z) + wsc(4, z) * v)
        m_tb = int(wsc(8, z) + wsc(2, z) * v)
        self.layout().setContentsMargins(m_lr, m_tb, m_lr, m_tb)

    def set_selected(self, sel: bool):
        if self.selected == sel: return
        self.selected = sel
        self._anim.stop()
        if sel:
            self.setStyleSheet(
                "PlanCard { background-color: rgba(0, 217, 255, 0.08); "
                "border: 2px solid #00d9ff; border-radius: 8px; }"
            )
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
        else:
            self.setStyleSheet(
                "PlanCard { background-color: rgba(255, 255, 255, 0.04); "
                "border: 2px solid transparent; border-radius: 8px; }"
            )
            self._anim.setStartValue(1.0)
            self._anim.setEndValue(0.0)
        self._anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            parent = self.parent()
            while parent and not hasattr(parent, 'select_plan'):
                parent = parent.parent()
            if parent:
                parent.select_plan(self)
        super().mousePressEvent(event)


# ────────────────── 会员协议弹窗 ──────────────────
class AgreementDialog(QWidget):
    def __init__(self, zoom=1.0, parent=None):
        super().__init__(parent)
        z = zoom
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._drag_pos = None
        w, h = wsc(520, z), wsc(540, z)
        self.setFixedSize(w, h)

        font_md = wsc(15, z)

        self.setObjectName("agreeCard")
        self.setStyleSheet("QWidget#agreeCard { background-color: #1a1a2e; border-radius: 10px; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        tb = QFrame()
        tb.setFixedHeight(wsc(40, z))
        tb.setStyleSheet(
            "QFrame { background-color: #16213e; border-top-left-radius: 10px; border-top-right-radius: 10px; }")
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(wsc(16, z), 0, wsc(10, z), 0)
        tt = QLabel("会员服务协议")
        tt.setStyleSheet("color: #ffffff; font-size: %dpx; font-weight: bold; background: transparent;" % font_md)
        tbl.addWidget(tt)
        tbl.addStretch()
        cb = TransparentToolButton(FIF.CLOSE, self)
        cb.setFixedSize(wsc(34, z), wsc(34, z))
        cb.clicked.connect(self.close)
        tbl.addWidget(cb)
        outer.addWidget(tb)

        browser = QTextBrowser()
        browser.setHtml(AGREEMENT_HTML)
        browser.setStyleSheet(
            "QTextBrowser { background-color: #16213e; border: none; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px; padding: 12px; }")
        browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(browser)

        if parent:
            pg = parent.geometry()
            self.move(pg.x() + (pg.width() - w) // 2, pg.y() + (pg.height() - h) // 2)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton: self.move(
            e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None


# ────────────────── 兑换码弹窗 (科技玻璃升级版) ──────────────────
class RedeemDialog(QWidget):
    activate_success = Signal()

    def __init__(self, zoom=1.0, parent=None):
        super().__init__(parent)
        z = zoom
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos = None

        font_xs = wsc(12, z)
        font_sm = wsc(13, z)
        font_md = wsc(15, z)

        w, h = wsc(460, z), wsc(210, z)
        self.setFixedSize(w, h)

        self._bg_frame = QFrame(self)
        self._bg_frame.setGeometry(0, 0, w, h)
        self._bg_frame.setObjectName("RedeemBg")
        self._bg_frame.setStyleSheet(
            "QFrame#RedeemBg { background-color: #1a1a2e; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08); }")
        outer = QVBoxLayout(self._bg_frame)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        tb = QFrame()
        tb.setFixedHeight(wsc(40, z))
        tb.setStyleSheet("background: transparent;")
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(wsc(16, z), 0, wsc(10, z), 0)
        tt = QLabel("兑换码激活")
        tt.setStyleSheet("color: #ffffff; font-size: %dpx; font-weight: bold; background: transparent;" % font_md)
        tbl.addWidget(tt)
        tbl.addStretch()
        cb = TransparentToolButton(FIF.CLOSE, self)
        cb.setFixedSize(wsc(34, z), wsc(34, z))
        cb.clicked.connect(self.close)
        tbl.addWidget(cb)
        outer.addWidget(tb)

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(wsc(24, z), wsc(10, z), wsc(24, z), wsc(20, z))
        bl.setSpacing(wsc(14, z))

        mc_row = QHBoxLayout()
        mc_row.setSpacing(wsc(10, z))
        mc_lbl = QLabel("设备特征码:")
        mc_lbl.setStyleSheet("color: #888888; font-size: %dpx; background: transparent;" % font_sm)
        mc_row.addWidget(mc_lbl)

        machine_code = get_machine_code()
        mc_text = QLabel(machine_code)
        mc_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        mc_text.setStyleSheet(
            "color: #00d9ff; font-size: %dpx; font-family: Consolas; background: transparent;" % font_sm)
        mc_row.addWidget(mc_text)

        mc_row.addStretch()
        cp_btn = QPushButton("复制")
        cp_btn.setFixedSize(wsc(56, z), wsc(28, z))
        cp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cp_btn.setStyleSheet(
            "QPushButton { background-color: rgba(255,255,255,0.05); color: #aaaaaa; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 0px; font-size: %dpx; } QPushButton:hover { background-color: rgba(255,255,255,0.1); color: #ffffff; }" % font_xs)
        cp_btn.clicked.connect(lambda: QApplication.clipboard().setText(machine_code))
        mc_row.addWidget(cp_btn)
        bl.addLayout(mc_row)

        cd_row = QHBoxLayout()
        cd_row.setSpacing(wsc(10, z))

        self._code_input = QLineEdit()
        self._code_input.setPlaceholderText("请输入 REC- 开头的激活码...")
        self._code_input.setFixedHeight(wsc(36, z))
        self._code_input.setStyleSheet(
            "QLineEdit { background-color: rgba(0, 0, 0, 0.2); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 0 %dpx; font-size: %dpx; } QLineEdit:focus { border-color: #00d9ff; background-color: rgba(0, 217, 255, 0.05); }" % (
            wsc(10, z), font_sm))
        cd_row.addWidget(self._code_input)

        act_btn = QPushButton("立即激活")
        act_btn.setFixedSize(wsc(84, z), wsc(36, z))
        act_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        act_btn.setStyleSheet(
            "QPushButton { background-color: #00d9ff; color: #111111; border: none; border-radius: 6px; padding: 0px; font-weight: bold; font-size: %dpx; } QPushButton:hover { background-color: #33e5ff; }" % font_sm)
        act_btn.clicked.connect(self._do_activate)
        cd_row.addWidget(act_btn)
        bl.addLayout(cd_row)

        self._msg = QLabel("")
        self._msg.setStyleSheet("color: #e94560; font-size: %dpx; background: transparent;" % font_sm)
        bl.addWidget(self._msg)
        outer.addWidget(body)

        if parent:
            pg = parent.geometry()
            self.move(pg.x() + (pg.width() - w) // 2, pg.y() + (pg.height() - h) // 2)

    def _do_activate(self):
        font_sm = wsc(13, 1.0)  # msg 样式不需要 zoom
        code = self._code_input.text().strip()
        if not code:
            self._msg.setText("请输入激活码")
            return
        res = activate_with_code(code)
        if res["success"]:
            self._msg.setText("✅ 激活成功！")
            self._msg.setStyleSheet("color: #00d9ff; font-size: %dpx; background: transparent;" % font_sm)
            QTimer.singleShot(800, lambda: [self.close(), self.activate_success.emit()])
        else:
            self._msg.setText(f"❌ {res['message']}")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton: self.move(
            e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None


# ────────────────── 关于弹窗 ──────────────────
class AboutDialog(QWidget):
    def __init__(self, zoom=1.0, parent=None):
        super().__init__(parent)
        z = zoom
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos = None

        font_xs = wsc(12, z)
        font_sm = wsc(13, z)
        font_md = wsc(15, z)

        w, h = wsc(420, z), wsc(280, z)
        self.setFixedSize(w, h)

        self._bg_frame = QFrame(self)
        self._bg_frame.setGeometry(0, 0, w, h)
        self._bg_frame.setObjectName("AboutBg")
        self._bg_frame.setStyleSheet(
            "QFrame#AboutBg { background-color: #1a1a2e; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08); }")
        outer = QVBoxLayout(self._bg_frame)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 标题栏
        tb = QFrame()
        tb.setFixedHeight(wsc(40, z))
        tb.setStyleSheet("background: transparent;")
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(wsc(16, z), 0, wsc(10, z), 0)
        tt = QLabel("关于录屏王")
        tt.setStyleSheet("color: #ffffff; font-size: %dpx; font-weight: bold; background: transparent;" % font_md)
        tbl.addWidget(tt)
        tbl.addStretch()
        cb = TransparentToolButton(FIF.CLOSE, self)
        cb.setFixedSize(wsc(34, z), wsc(34, z))
        cb.clicked.connect(self.close)
        tbl.addWidget(cb)
        outer.addWidget(tb)

        # 内容区
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(wsc(24, z), wsc(14, z), wsc(24, z), wsc(24, z))
        bl.setSpacing(wsc(10, z))

        info_items = [
            ("开发者", "汕头市潮南区白雪歌软件开发服务中心"),
            ("客服QQ", "3772591697"),
            ("客服邮箱", "kungfupan1@gmail.com"),
        ]
        for label_text, value_text in info_items:
            row = QVBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(wsc(2, z))
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #888888; font-size: %dpx; background: transparent;" % font_xs)
            row.addWidget(lbl)
            val = QLabel(value_text)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val.setStyleSheet("color: #ffffff; font-size: %dpx; background: transparent;" % font_sm)
            row.addWidget(val)
            bl.addLayout(row)

        bl.addStretch()
        outer.addWidget(body)

        if parent:
            pg = parent.geometry()
            self.move(pg.x() + (pg.width() - w) // 2, pg.y() + (pg.height() - h) // 2)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None


# ────────────────── 主支付对话框 ──────────────────
class PayDialog(QWidget):
    payment_success = Signal()
    qr_preload_done = Signal(list)  # <--- 【新增】：用于后台向主界面传递二维码数据的信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 1. 动态获取显示器高度并设置为 50% 作为【绝对固定尺寸】
        screen = self.screen()
        monitor_h = screen.geometry().height() if screen else 1080
        default_h = int(monitor_h * 0.6)
        default_w = int(default_h * (_PAY_BASE_W / _PAY_BASE_H))

        self.setFixedSize(default_w, default_h)

        # 2. 【核心修复】：计算出正确的静态缩放比例 _zoom，这样下面就不会报错了！
        self._zoom = default_w / sc(_PAY_BASE_W)
        self._drag_pos = None

        # 3. 利用本地证书缓存计算剩余天数 (终极稳健版)
        self.days_left = -2
        self.raw_expire_str = ""
        try:
            act_info = check_activation()
            if isinstance(act_info, dict) and act_info.get("activated"):
                self.days_left = -1
                exp_date_str = act_info.get("expire_date", "") or act_info.get("expire_time", "") or act_info.get(
                    "deadline", "")

                # 无论传进来什么，强制转为字符串并去掉首尾空格
                self.raw_expire_str = str(exp_date_str).strip()

                if self.raw_expire_str:
                    if "9999" in self.raw_expire_str or "永久" in self.raw_expire_str:
                        self.days_left = 99999
                    else:
                        try:
                            # 终极暴力：不管多长，我们只切取最前面的 10 个字符
                            # 因为截图显示后端传回的就是 2025-04-08 这种格式
                            clean_date_str = self.raw_expire_str[:10]

                            # 转换成时间对象
                            exp_date = datetime.strptime(clean_date_str, "%Y-%m-%d")

                            # 获取今天的时间，并将时分秒清零，保证天数计算准确
                            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

                            # 计算差值（直接得出一个整数，可能是正数、0、负数）
                            self.days_left = (exp_date - today).days
                        except Exception as e:
                            # 如果这里报错了，才会在控制台打印，并且保留 days_left = -1
                            print(f"日期解析彻底失败，错误信息: {e}")
                            pass
        except Exception:
            pass

        self._plans = []
        self._selected_plan = None
        self._order_no = ""
        self._qr_cache = {}
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_order)
        self._creating = False

        # <--- 【新增】：告诉程序，只要收到 qr_preload_done 信号，就执行 _on_preload_done 替换图片
        self.qr_preload_done.connect(self._on_preload_done)

        setTheme(Theme.DARK)
        setThemeColor("#00d9ff")
        self.setStyleSheet("PayDialog { background: transparent; } * { outline: none; }")

        self._build_ui()
        self._load_plans()

    def _build_ui(self):
        # 启用光斑底板
        self._main_card = BokehBackground(self)
        # 【核心修复】：让光斑背景和当前窗口一样大，不要写死！
        self._main_card.setFixedSize(self.width(), self.height())

        self._build_content(self._zoom)
    def _build_content(self, zoom):
        """根据 zoom 构建 BokehBackground 内的全部内容"""
        z = zoom
        font_xs = wsc(12, z)
        font_sm = wsc(13, z)
        font_md = wsc(15, z)
        font_lg = wsc(18, z)
        font_price = wsc(36, z)

        main_layout = QVBoxLayout(self._main_card)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === 标题栏 ===
        title_bar = QFrame()
        title_bar.setFixedHeight(wsc(46, z))
        title_bar.setStyleSheet("background: transparent;")
        tbl = QHBoxLayout(title_bar)
        tbl.setContentsMargins(wsc(20, z), 0, wsc(10, z), 0)

        title_text = QLabel("激活录屏王")
        title_text.setStyleSheet(
            "color: #ffffff; font-size: %dpx; font-weight: bold; background: transparent;" % font_lg)
        tbl.addWidget(title_text)

        # 弹簧，把后面的控件推到最右边
        tbl.addStretch()

        # 右上角显示剩余天数 (精准状态展示)
        if self.days_left == -2:
            days_str = "当前未订阅"
        elif self.days_left == -1:
            # 读取到了激活状态，但日期没解析出来，直接显示原文字符串
            days_str = f"👑 已激活 ({self.raw_expire_str})" if self.raw_expire_str else "👑 已激活"
        elif self.days_left > 9000:
            days_str = "👑 永久授权"
        elif self.days_left > 0:
            days_str = f"👑 当前剩余: {self.days_left} 天"
        elif self.days_left == 0:
            days_str = "⚠️ 订阅今日到期"
        else:
            days_str = f"⚠️ 订阅已过期 {-self.days_left} 天"

        self.vip_days_label = QLabel(days_str)
        self.vip_days_label.setStyleSheet(
            "color: #ffda6a; font-weight: bold; font-size: %dpx; background: transparent; outline: none;" % font_md)
        tbl.addWidget(self.vip_days_label)

        self._more_btn = TransparentToolButton(FIF.MORE, self)
        self._more_menu = RoundMenu(parent=self)

        # 放大菜单字体
        menu_font = QFont("Microsoft YaHei")
        menu_font.setPixelSize(wsc(64, z))
        self._more_menu.setFont(menu_font)

        redeem_action = Action(FIF.TAG, "兑换码激活", triggered=self._open_redeem)
        self._more_menu.addAction(redeem_action)
        btn_sz = wsc(44, z)
        self._more_btn.setFixedSize(btn_sz, btn_sz)
        self._more_btn.clicked.connect(lambda: self._more_menu.exec(
            self._more_btn.mapToGlobal(self._more_btn.rect().bottomRight() - QPoint(0, 0))))
        tbl.addWidget(self._more_btn)

        close_btn = TransparentToolButton(FIF.CLOSE, self)
        close_btn.setFixedSize(btn_sz, btn_sz)
        close_btn.clicked.connect(self.close)
        tbl.addWidget(close_btn)
        main_layout.addWidget(title_bar)

        # === 左右分栏 ===
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(wsc(20, z), wsc(14, z), wsc(20, z), wsc(14, z))
        body_layout.setSpacing(wsc(20, z))

        # ──── 左栏 ────
        left = QWidget()
        left.setStyleSheet("background: transparent;")
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(wsc(6, z))

        hint = QLabel("选择订阅方案")
        hint.setStyleSheet("color: #a0a0a0; font-size: %dpx; font-weight: bold; background: transparent;" % font_md)
        left_lay.addWidget(hint)

        self._plans_layout = QVBoxLayout()
        self._plans_layout.setSpacing(wsc(12, z))
        left_lay.addLayout(self._plans_layout)

        self._loading_label = QLabel("正在加载方案...")
        self._loading_label.setStyleSheet("color: #a0a0a0; font-size: %dpx; background: transparent;" % font_md)
        left_lay.addWidget(self._loading_label)
        left_lay.addStretch()

        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #a0a0a0; font-size: %dpx; background: transparent;" % font_sm)
        left_lay.addWidget(self._status_label)
        body_layout.addWidget(left, stretch=4)

        # ──── 右栏 ────
        right = QFrame()
        right.setObjectName("RightPanel")
        right.setStyleSheet(
            "QFrame#RightPanel { background-color: rgba(255, 255, 255, 0.03); border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.06); }")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(wsc(16, z), wsc(24, z), wsc(16, z), wsc(20, z))
        right_lay.setSpacing(wsc(10, z))
        right_lay.addStretch(1)

        scan_hint = QLabel("微信扫码支付")
        scan_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scan_hint.setStyleSheet("color: #a0a0a0; font-size: %dpx; background: transparent;" % font_md)
        right_lay.addWidget(scan_hint)

        # 使用顶部我们定义好的丝滑跳动数字组件
        self._amount_label = AnimatedPriceLabel(zoom=z)
        right_lay.addWidget(self._amount_label)

        qr_size = wsc(190, z)
        self._qr_label = QLabel("选择方案后生成二维码")
        self._qr_label.setFixedSize(qr_size, qr_size)
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_label.setStyleSheet(
            "background-color: rgba(255,255,255,0.05); border-radius: 6px; color: #a0a0a0; font-size: %dpx;" % font_sm)
        right_lay.addWidget(self._qr_label, alignment=Qt.AlignmentFlag.AlignCenter)
        right_lay.addSpacing(wsc(14, z))

        self._order_hint = QLabel("")
        self._order_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._order_hint.setStyleSheet("color: #777777; font-size: %dpx; background: transparent;" % font_xs)
        right_lay.addWidget(self._order_hint)
        right_lay.addSpacing(wsc(4, z))

        agree_label = QLabel(
            "<a href='#' style='color: #00d9ff; text-decoration: none; font-size: %dpx;'>《会员服务协议》</a>" % font_sm)
        agree_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        agree_label.setStyleSheet("background: transparent;")
        agree_label.linkActivated.connect(self._open_agreement)
        right_lay.addWidget(agree_label)
        right_lay.addStretch(1)

        body_layout.addWidget(right, stretch=5)
        main_layout.addWidget(body, stretch=1)

        # === 底部: 会员特权 ===
        bottom = QWidget()
        bottom.setStyleSheet("background: transparent;")
        bottom_lay = QVBoxLayout(bottom)
        bottom_lay.setContentsMargins(wsc(20, z), 0, wsc(20, z), wsc(12, z))
        bottom_lay.setSpacing(wsc(8, z))

        perks_title = QLabel("录屏会员核心特权")
        perks_title.setStyleSheet(
            "color: #a0a0a0; font-size: %dpx; font-weight: bold; background: transparent;" % font_md)
        bottom_lay.addWidget(perks_title)

        perks_layout = QHBoxLayout()
        perks_layout.setContentsMargins(0, 0, 0, 0)
        perks_layout.setSpacing(wsc(16, z))
        perk_data = [
            ("🎬", "不限时长录制", "高清录制不间断"),
            ("🎥", "原画/高帧率", "24~60帧极致高清"),
            ("📺", "全屏/区域录制", "自定义录制区域"),
        ]
        for icon_text, title, subtitle in perk_data:
            box = QFrame()
            box.setObjectName("PerkBox")
            box.setStyleSheet(
                "QFrame#PerkBox { background-color: rgba(255, 255, 255, 0.04); border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.06); }")
            col = QVBoxLayout(box)
            col.setContentsMargins(wsc(10, z), wsc(14, z), wsc(10, z), wsc(14, z))
            col.setSpacing(wsc(4, z))
            icon = QLabel(icon_text)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setStyleSheet("color: #ffffff; font-size: %dpx; background: transparent; border: none;" % wsc(28, z))
            col.addWidget(icon)
            t = QLabel(title)
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setStyleSheet(
                "color: #00d9ff; font-size: %dpx; font-weight: bold; background: transparent; border: none;" % font_md)
            col.addWidget(t)
            s = QLabel(subtitle)
            s.setAlignment(Qt.AlignmentFlag.AlignCenter)
            s.setStyleSheet("color: #888888; font-size: %dpx; background: transparent; border: none;" % font_xs)
            col.addWidget(s)
            perks_layout.addWidget(box)
        bottom_lay.addLayout(perks_layout)

        about_row = QHBoxLayout()
        about_row.addStretch()
        about_label = QLabel(
            "<a href='#' style='color: #555555; text-decoration: none; font-size: %dpx;'>关于我们</a>" % font_sm)
        about_label.setStyleSheet("background: transparent;")
        about_label.setCursor(Qt.CursorShape.PointingHandCursor)
        about_label.linkActivated.connect(self._open_about)
        about_row.addWidget(about_label)
        bottom_lay.addLayout(about_row)

        main_layout.addWidget(bottom)

        # 从 self._plans 重建方案列表
        if self._plans:
            self._render_plans_content(z)

        # 从 self._qr_cache 恢复选中方案的二维码
        if self._selected_plan:
            pid = self._selected_plan.get("id")
            if pid in self._qr_cache:
                self._show_cached(pid, z)

        if self.parent():
            pg = self.parent().geometry()
            self.move(pg.x() + (pg.width() - self.width()) // 2,
                      pg.y() + (pg.height() - self.height()) // 2)

    # ──────────── 缩放相关 ────────────

        # ──────────── 极简丝滑拖拽逻辑 ────────────
    def mousePressEvent(self, event):
        # 只要鼠标左键按下，就记录当前位置与窗口左上角的偏移量
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # 如果鼠标左键按住并且在移动，直接移动整个窗口
        if hasattr(self, '_drag_pos') and self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # 鼠标松开，清空偏移量记录
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    # ──────────── 以下是完整的核心业务逻辑 ────────────

    def _load_plans(self):
        self._loading_label.setText("正在加载方案...")
        QTimer.singleShot(50, self._fetch_plans)

    def _fetch_plans(self):
        plans, public_key = api_client.fetch_plans()
        if plans:
            self._public_key = public_key
            save_plans_cache(plans, public_key)
            self._plans = plans
            self._render_plans()
        else:
            from license.cache_manager import load_plans_cache as load_cache
            cached_plans, cached_key = load_cache()
            if cached_plans:
                self._public_key = cached_key
                self._plans = cached_plans
                self._render_plans()
            else:
                self._loading_label.setText("无法连接服务器，请检查网络")
                self._loading_label.setStyleSheet("color: #e94560; font-size: %dpx; background: transparent;" % wsc(15, self._zoom))

    def _render_plans(self):
        self._loading_label.setVisible(False)
        self._render_plans_content(self._zoom)

    def _render_plans_content(self, z):
        """渲染方案卡片（可被 rebuild 调用）"""
        self._loading_label.setVisible(False)

        while self._plans_layout.count():
            item = self._plans_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for p in self._plans:
            card = PlanCard(p, zoom=z, parent=self)
            self._plans_layout.addWidget(card)

        default_card = None
        # 【修改】：直接获取布局里的最后一个组件作为默认选中
        count = self._plans_layout.count()
        if count > 0:
            default_card = self._plans_layout.itemAt(count - 1).widget()

        if default_card:
            self.select_plan(default_card)

        QTimer.singleShot(200, self._preload_all_orders)

    def _get_all_cards(self):
        cards = []
        for i in range(self._plans_layout.count()):
            w = self._plans_layout.itemAt(i).widget()
            if isinstance(w, PlanCard):
                cards.append(w)
        return cards

    def select_plan(self, card: PlanCard):
        """点击套餐卡片时，瞬间切换选中状态，并尝试显示缓存的二维码"""
        self._poll_timer.stop()
        self._selected_plan = card.plan_data

        # 瞬间更新左侧卡片的选中视觉效果
        for w in self._get_all_cards():
            w.set_selected(w == card)

        plan_id = self._selected_plan.get("id")

        # 尝试显示当前选中的套餐二维码（如果没有缓存，_show_cached 内部会处理显示 Loading）
        # 传入 animate=True 让价格丝滑跳动
        self._show_cached(plan_id, animate=True)

    def _make_qr_pixmap(self, url: str):
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        qimage = QImage(img.tobytes("raw", "RGB"), img.width, img.height, 3 * img.width, QImage.Format.Format_RGB888)
        qr_img_size = wsc(190, self._zoom)
        return QPixmap.fromImage(qimage).scaled(qr_img_size, qr_img_size, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation)

    def _preload_all_orders(self):
        # 【核心修复】：开启后台专属线程去拉取微信订单，绝对不阻塞拖拽和动画！
        import threading
        threading.Thread(target=self._preload_thread, daemon=True).start()

    def _preload_thread(self):
        machine_code = get_machine_code()

        # 【核心策略修改】：加上 reversed()，让它从后往前加载！
        # 这样就能和上面默认选中最后一个套餐的逻辑完美对齐，秒出二维码！
        for plan in reversed(self._plans):
            plan_id = plan.get("id")
            # 如果缓存里已经有了，就跳过
            if not plan_id or plan_id in self._qr_cache:
                continue

            try:
                # 这里的网络请求会在后台默默进行
                result = api_client.create_order(plan_id, machine_code)
                if result and "order_no" in result:
                    # 把套餐原本的价格塞进去备用
                    result['fallback_amount'] = plan.get("price", "0")

                    # 拿到一个，就立刻打包这“一个”发射给主界面！
                    self.qr_preload_done.emit([(plan_id, result)])
            except Exception:
                pass

    def _on_preload_done(self, results):
        for plan_id, result in results:
            code_url = result.get("code_url", "")
            amount = result.get("amount", result.get("fallback_amount", "0"))

            # 生成二维码图像并存入缓存
            self._qr_cache[plan_id] = {
                "pixmap": self._make_qr_pixmap(code_url) if code_url else None,
                "order_no": result["order_no"],
                "amount": amount,
            }

        # 如果预加载完成时，用户正好看的就是这个套餐，顺便刷新一下显示
        if self._selected_plan:
            pid = self._selected_plan.get("id")
            if pid in self._qr_cache:
                # 传入 animate=False 防止数字乱跳
                self._show_cached(pid, animate=False)

    def _create_single_order(self):
        if not self._selected_plan or self._creating:
            return
        self._creating = True
        self._status_label.setText("正在生成二维码...")

        plan_id = self._selected_plan.get("id")
        machine_code = get_machine_code()
        result = api_client.create_order(plan_id, machine_code)

        if not result or "order_no" not in result:
            self._status_label.setText("创建订单失败，请重试")
            self._status_label.setStyleSheet("color: #e94560; font-size: %dpx; background: transparent;" % wsc(13, self._zoom))
            self._creating = False
            return

        self._order_no = result["order_no"]
        code_url = result.get("code_url", "")
        amount = result.get("amount", "0")
        pixmap = self._make_qr_pixmap(code_url) if code_url else None

        self._qr_cache[plan_id] = {
            "pixmap": pixmap,
            "order_no": self._order_no,
            "amount": amount
        }

        if pixmap:
            self._qr_label.setPixmap(pixmap)
            self._qr_label.setStyleSheet("background-color: #ffffff; border-radius: 6px;")
            try:
                amount = "{:.2f}".format(float(amount))
            except:
                pass
            self._amount_label.setText("￥{}".format(amount))
            self._order_hint.setText("订单号: {}  等待支付...".format(self._order_no))
            self._status_label.setText("")
            self._poll_timer.start(3000)
        else:
            self._status_label.setText("未获取到支付链接")
            self._status_label.setStyleSheet("color: #e94560; font-size: %dpx; background: transparent;" % wsc(13, self._zoom))

        self._creating = False

    def _show_cached(self, plan_id, z=None, animate=True):
        """显示指定套餐的支付信息，如果未加载完则显示 Loading 状态"""
        if z is None:
            z = self._zoom

        # 1. 如果二维码还没加载完（后台线程还在跑）
        if plan_id not in self._qr_cache:
            # 清空二维码，显示优雅的 Loading 提示
            self._qr_label.setPixmap(QPixmap())
            self._qr_label.setText("正在生成专属支付码...")
            self._qr_label.setStyleSheet(
                "background-color: rgba(255,255,255,0.05); border-radius: 6px; color: #00d9ff; font-size: %dpx; outline: none;" % wsc(
                    14, z))

            self._order_hint.setText("加载中...")
            self._status_label.setText("")

            # 从原始计划数据中读取价格，先行展示价格
            try:
                amount_val = float(self._selected_plan.get("price", "0"))
            except:
                amount_val = 0.0
            self._amount_label.set_price(amount_val, animate=animate)

            # 【！！！最关键的一行！！！】
            # 必须用 return 结束函数，绝对不能让它继续往下走去读取空缓存！
            return

        # 2. 如果二维码已经加载完毕，从缓存中取出数据并展示
        cache = self._qr_cache[plan_id]
        self._order_no = cache.get("order_no", "")

        if cache.get("pixmap"):
            self._qr_label.setPixmap(cache["pixmap"])
            self._qr_label.setStyleSheet("background-color: #ffffff; border-radius: 6px; outline: none;")
        else:
            self._qr_label.setPixmap(QPixmap())
            self._qr_label.setText("二维码生成失败")
            self._qr_label.setStyleSheet(
                "background-color: #0f3460; border-radius: 6px; color: #a0a0a0; font-size: %dpx; outline: none;" % wsc(
                    13, z))

        try:
            amount_val = float(cache.get("amount", 0))
        except:
            amount_val = 0.0

        self._amount_label.set_price(amount_val, animate=animate)
        self._order_hint.setText("订单号: {}  等待支付...".format(self._order_no))
        self._status_label.setText("")

        # 只有真正显示了二维码，才开始轮询支付状态
        self._poll_timer.start(3000)

    def _poll_order(self):
        if not self._order_no: return
        result = api_client.check_order(self._order_no)
        if result.get("status") == "paid":
            self._poll_timer.stop()
            license_code = result.get("license_code", "")
            if license_code:
                act = activate_with_code(license_code)
                if act["success"]:
                    self._status_label.setText("支付成功！")
                    self._status_label.setStyleSheet(
                        "color: #00d9ff; font-size: %dpx; background: transparent;" % wsc(13, self._zoom))
                    QTimer.singleShot(800, self._on_success)
                else:
                    self._status_label.setText("激活失败: {}".format(act["message"]))
                    self._status_label.setStyleSheet(
                        "color: #e94560; font-size: %dpx; background: transparent;" % wsc(13, self._zoom))
            else:
                self._status_label.setText("支付成功，但未获取到许可证")
                self._status_label.setStyleSheet("color: #e94560; font-size: %dpx; background: transparent;" % wsc(13, self._zoom))
        elif result.get("status") == "expired":
            self._poll_timer.stop()
            self._status_label.setText("订单已过期，请重新选择")
            self._status_label.setStyleSheet("color: #e94560; font-size: %dpx; background: transparent;" % wsc(13, self._zoom))
            self._qr_label.setPixmap(QPixmap())
            self._qr_label.setText("选择方案后生成二维码")
            self._qr_label.setStyleSheet(
                "background-color: rgba(255,255,255,0.05); border-radius: 6px; color: #a0a0a0; font-size: %dpx;" % wsc(13, self._zoom))

    def _open_redeem(self):
        dlg = RedeemDialog(zoom=self._zoom, parent=self)
        dlg.activate_success.connect(self._on_success)
        dlg.show()

    def _open_about(self):
        dlg = AboutDialog(zoom=self._zoom, parent=self)
        dlg.show()

    def _open_agreement(self):
        dlg = AgreementDialog(zoom=self._zoom, parent=self)
        dlg.show()

    def _on_success(self):
        self.close()
        self.payment_success.emit()

    def closeEvent(self, event):
        self._poll_timer.stop()
        super().closeEvent(event)
