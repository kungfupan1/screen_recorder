# -*- coding: utf-8 -*-
"""
支付对话框 - 使用 qfluentwidgets 组件
"""
import qrcode
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QFrame, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor
from PySide6.QtCore import QPoint

from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton, LineEdit,
    BodyLabel, StrongBodyLabel, CaptionLabel, SubtitleLabel,
    InfoBar, InfoBarPosition, setTheme, Theme, setThemeColor,
    isDarkTheme, TransparentToolButton, RoundMenu, Action,
    ProgressRing, HyperlinkLabel,
)
from qfluentwidgets import FluentIcon as FIF

from license.machine_code import get_machine_code
from license.activation import activate_with_code
from license import api_client
from license.cache_manager import save_plans_cache
from utils.config import sc

DIALOG_W = sc(680)
DIALOG_H = sc(860)


class PlanCard(CardWidget):
    """方案卡片 - 使用 qfluentwidgets CardWidget 自带悬停效果"""

    def __init__(self, plan_data: dict, parent=None):
        super().__init__(parent)
        self.plan_data = plan_data
        self.selected = False
        self.setFixedHeight(sc(90))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setBorderRadius(8)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(sc(16), sc(10), sc(16), sc(10))
        layout.setSpacing(sc(4))

        name = StrongBodyLabel(self.plan_data.get("name", ""))
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name)

        price_val = self.plan_data.get("price", "0")
        try:
            price_val = "{:.2f}".format(float(price_val))
        except (ValueError, TypeError):
            pass

        price = SubtitleLabel("{}".format(price_val), self)
        price.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price.setStyleSheet("color: #70c0e8;")
        layout.addWidget(price)

    def set_selected(self, sel: bool):
        self.selected = sel
        if sel:
            self.setStyleSheet(
                "PlanCard, QWidget { background-color: rgba(112, 192, 232, 0.15); "
                "border: 1px solid #70c0e8; border-radius: 8px; }"
            )
        else:
            self.setStyleSheet("")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            parent = self.parent()
            while parent and not isinstance(parent, PayDialog):
                parent = parent.parent()
            if parent:
                parent.select_plan(self)
        super().mousePressEvent(event)


class PayDialog(QWidget):
    """支付对话框"""

    payment_success = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(DIALOG_W, DIALOG_H)
        self._drag_pos = None

        self._plans = []
        self._selected_plan = None
        self._order_no = ""
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_order)

        # 设置主题色
        setTheme(Theme.DARK)
        setThemeColor("#70c0e8")

        self._build_ui()
        self._load_plans()

    def _build_ui(self):
        # 主卡片容器
        self._main_card = QFrame(self)
        self._main_card.setGeometry(0, 0, DIALOG_W, DIALOG_H)
        self._main_card.setStyleSheet(
            "QFrame { background-color: #202020; border-radius: 12px; "
            "border: 1px solid #3d3d3d; }"
        )

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self._main_card)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self._main_card.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self._main_card)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === 标题栏 ===
        title_bar = QFrame()
        title_bar.setFixedHeight(sc(50))
        title_bar.setStyleSheet(
            "QFrame { background-color: #252525; border-top-left-radius: 12px; "
            "border-top-right-radius: 12px; border-bottom: 1px solid #3d3d3d; }"
        )
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(sc(22), 0, sc(12), 0)

        title_text = StrongBodyLabel("激活录屏王")
        title_layout.addWidget(title_text)
        title_layout.addStretch()

        # 更多菜单按钮
        self._more_btn = TransparentToolButton(FIF.MORE, self)
        self._more_menu = RoundMenu(parent=self)
        redeem_action = Action(FIF.TAG, "兑换码激活", triggered=self._toggle_redeem)
        self._more_menu.addAction(redeem_action)

        btn_size = sc(36)
        self._more_btn.setFixedSize(btn_size, btn_size)
        self._more_btn.clicked.connect(
            lambda: self._more_menu.exec(
                self._more_btn.mapToGlobal(
                    self._more_btn.rect().bottomRight() - QPoint(0, 0)
                )
            )
        )
        title_layout.addWidget(self._more_btn)

        close_btn = TransparentToolButton(FIF.CLOSE, self)
        close_btn.setFixedSize(btn_size, btn_size)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)

        main_layout.addWidget(title_bar)

        # === 内容区 ===
        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(sc(30), sc(22), sc(30), sc(22))
        self._content_layout.setSpacing(sc(14))

        # 选择方案提示
        hint_label = BodyLabel("选择授权方案:")
        self._content_layout.addWidget(hint_label)

        # 方案卡片网格
        self._plans_grid = QGridLayout()
        self._plans_grid.setSpacing(sc(12))
        self._content_layout.addLayout(self._plans_grid)

        # 加载中
        self._loading_label = BodyLabel("正在加载方案...")
        self._content_layout.addWidget(self._loading_label)

        # === 二维码区域 (默认隐藏) ===
        self._qr_frame = QFrame()
        self._qr_frame.setVisible(False)
        self._qr_frame.setStyleSheet(
            "QFrame { background-color: #2a2a2a; border-radius: 8px; "
            "border: 1px solid #3d3d3d; }"
        )
        qr_layout = QVBoxLayout(self._qr_frame)
        qr_layout.setContentsMargins(sc(22), sc(18), sc(22), sc(18))
        qr_layout.setSpacing(sc(12))

        qr_img_size = sc(240)
        self._qr_label = QLabel()
        self._qr_label.setFixedSize(qr_img_size, qr_img_size)
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_label.setStyleSheet(
            "background-color: #ffffff; border-radius: 6px;"
        )
        qr_layout.addWidget(self._qr_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._pay_hint = StrongBodyLabel()
        self._pay_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_layout.addWidget(self._pay_hint)

        self._order_hint = CaptionLabel()
        self._order_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_layout.addWidget(self._order_hint)

        self._content_layout.addWidget(self._qr_frame)

        # === 购买按钮 ===
        self._buy_btn = PrimaryPushButton("立即购买")
        self._buy_btn.setFixedHeight(sc(44))
        self._buy_btn.clicked.connect(self._create_order)
        self._content_layout.addWidget(self._buy_btn)

        # 状态标签
        self._status_label = BodyLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_layout.addWidget(self._status_label)

        self._content_layout.addStretch()

        # === 专属客服 ===
        service_frame = CardWidget()
        service_frame.setBorderRadius(6)
        service_h_layout = QHBoxLayout(service_frame)
        service_h_layout.setContentsMargins(sc(16), sc(10), sc(16), sc(10))
        service_h_layout.setSpacing(sc(12))

        svc_title = StrongBodyLabel("专属客服")
        service_h_layout.addWidget(svc_title)

        svc_wechat = HyperlinkLabel("微信: 13450445253")
        svc_wechat.setUrl("weixin://dl/chat?13450445253")
        service_h_layout.addWidget(svc_wechat)

        service_h_layout.addStretch()

        copy_btn = PushButton("复制")
        copy_btn.setFixedSize(sc(60), sc(32))
        copy_btn.clicked.connect(lambda: self._copy_to_clipboard("13450445253"))
        service_h_layout.addWidget(copy_btn)

        self._content_layout.addWidget(service_frame)

        # === 兑换码区域 (默认隐藏) ===
        self._redeem_frame = CardWidget()
        self._redeem_frame.setVisible(False)
        self._redeem_frame.setBorderRadius(8)
        redeem_layout = QVBoxLayout(self._redeem_frame)
        redeem_layout.setContentsMargins(sc(18), sc(14), sc(18), sc(14))
        redeem_layout.setSpacing(sc(12))

        # 机器码行
        mc_layout = QHBoxLayout()
        mc_layout.setSpacing(sc(8))
        mc_label = BodyLabel("机器码:")
        mc_label.setFixedWidth(sc(56))
        mc_layout.addWidget(mc_label)

        machine_code = get_machine_code()
        mc_text = CaptionLabel(machine_code)
        mc_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        mc_text.setStyleSheet("color: #70c0e8;")
        mc_layout.addWidget(mc_text)

        copy_mc_btn = PushButton("复制")
        copy_mc_btn.setFixedSize(sc(56), sc(30))
        copy_mc_btn.clicked.connect(lambda: self._copy_to_clipboard(machine_code))
        mc_layout.addWidget(copy_mc_btn)
        redeem_layout.addLayout(mc_layout)

        # 注册码输入行
        code_layout = QHBoxLayout()
        code_layout.setSpacing(sc(8))
        code_label = BodyLabel("注册码:")
        code_label.setFixedWidth(sc(56))
        code_layout.addWidget(code_label)

        self._code_input = LineEdit()
        self._code_input.setPlaceholderText("REC-xxxx...")
        self._code_input.setFixedHeight(sc(36))
        code_layout.addWidget(self._code_input)

        activate_btn = PrimaryPushButton("激活")
        activate_btn.setFixedSize(sc(64), sc(36))
        activate_btn.clicked.connect(self._do_activate)
        code_layout.addWidget(activate_btn)
        redeem_layout.addLayout(code_layout)

        self._redeem_msg = CaptionLabel("")
        self._redeem_msg.setStyleSheet("color: #f38ba8;")
        redeem_layout.addWidget(self._redeem_msg)

        self._content_layout.addWidget(self._redeem_frame)

        main_layout.addWidget(content)

        # 居中
        if self.parent():
            pg = self.parent().geometry()
            self.move(
                pg.x() + (pg.width() - DIALOG_W) // 2,
                pg.y() + (pg.height() - DIALOG_H) // 2,
            )

    # ---- 业务逻辑 ----

    def _load_plans(self):
        self._loading_label.setText("正在加载方案...")
        QTimer.singleShot(50, self._fetch_plans)

    def _fetch_plans(self):
        plans, public_key = api_client.fetch_plans()
        if plans:
            self._public_key = public_key
            save_plans_cache(plans, public_key)
            self._render_plans(plans)
        else:
            from license.cache_manager import load_plans_cache as load_cache
            cached_plans, cached_key = load_cache()
            if cached_plans:
                self._public_key = cached_key
                self._render_plans(cached_plans)
            else:
                self._loading_label.setText("无法连接服务器，请检查网络")
                self._loading_label.setStyleSheet("color: #f38ba8;")

    def _render_plans(self, plans):
        self._plans = plans
        self._loading_label.setVisible(False)

        while self._plans_grid.count():
            item = self._plans_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, p in enumerate(plans):
            card = PlanCard(p, self)
            row = i // 3
            col = i % 3
            self._plans_grid.addWidget(card, row, col)

        if plans:
            first = self._plans_grid.itemAt(0).widget()
            if first:
                self.select_plan(first)

    def _get_all_cards(self):
        cards = []
        for i in range(self._plans_grid.count()):
            w = self._plans_grid.itemAt(i).widget()
            if isinstance(w, PlanCard):
                cards.append(w)
        return cards

    def select_plan(self, card: PlanCard):
        for w in self._get_all_cards():
            w.set_selected(w == card)
        self._selected_plan = card.plan_data if card else None

    def _create_order(self):
        if not self._selected_plan:
            return
        plan_id = self._selected_plan.get("id")
        machine_code = get_machine_code()

        self._status_label.setText("正在创建订单...")

        result = api_client.create_order(plan_id, machine_code)
        if not result or "order_no" not in result:
            self._status_label.setText("创建订单失败，请重试")
            self._status_label.setStyleSheet("color: #f38ba8;")
            return

        self._order_no = result["order_no"]
        code_url = result.get("code_url", "")
        amount = result.get("amount", "0")

        if code_url:
            self._show_qr(code_url, amount)
            self._poll_timer.start(3000)
        else:
            self._status_label.setText("未获取到支付链接")
            self._status_label.setStyleSheet("color: #f38ba8;")

    def _show_qr(self, url: str, amount):
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        img = img.convert("RGB")
        data = img.tobytes("raw", "RGB")
        qimage = QImage(data, img.width, img.height, 3 * img.width, QImage.Format.Format_RGB888)
        qr_img_size = sc(240)
        pixmap = QPixmap.fromImage(qimage).scaled(
            qr_img_size, qr_img_size, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._qr_label.setPixmap(pixmap)

        self._buy_btn.setVisible(False)

        try:
            amount = "{:.2f}".format(float(amount))
        except (ValueError, TypeError):
            pass
        self._pay_hint.setText("微信扫码支付  {}".format(amount))
        self._order_hint.setText("订单号: {}   等待支付中...".format(self._order_no))
        self._qr_frame.setVisible(True)
        self._loading_label.setVisible(False)

    def _poll_order(self):
        if not self._order_no:
            return
        result = api_client.check_order(self._order_no)
        if result.get("status") == "paid":
            self._poll_timer.stop()
            license_code = result.get("license_code", "")
            if license_code:
                act = activate_with_code(license_code)
                if act["success"]:
                    self._status_label.setText("支付成功！正在开始录制...")
                    self._status_label.setStyleSheet("color: #70c0e8;")
                    QTimer.singleShot(800, self._on_success)
                else:
                    self._status_label.setText("激活失败: {}".format(act["message"]))
                    self._status_label.setStyleSheet("color: #f38ba8;")
            else:
                self._status_label.setText("支付成功，但未获取到许可证")
                self._status_label.setStyleSheet("color: #f38ba8;")
        elif result.get("status") == "expired":
            self._poll_timer.stop()
            self._status_label.setText("订单已过期，请重新选择方案")
            self._status_label.setStyleSheet("color: #f38ba8;")
            self._qr_frame.setVisible(False)
            self._buy_btn.setVisible(True)

    def _toggle_redeem(self):
        self._redeem_frame.setVisible(not self._redeem_frame.isVisible())

    def _do_activate(self):
        code = self._code_input.text().strip()
        if not code:
            self._redeem_msg.setText("请输入注册码")
            return

        result = activate_with_code(code)
        if result["success"]:
            self._redeem_msg.setText("激活成功！")
            self._redeem_msg.setStyleSheet("color: #70c0e8;")
            QTimer.singleShot(800, self._on_success)
        else:
            self._redeem_msg.setText(result["message"])
            self._redeem_msg.setStyleSheet("color: #f38ba8;")

    def _copy_to_clipboard(self, text: str):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def _on_success(self):
        self.close()
        self.payment_success.emit()

    # === 窗口拖拽 ===
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def closeEvent(self, event):
        self._poll_timer.stop()
        super().closeEvent(event)
