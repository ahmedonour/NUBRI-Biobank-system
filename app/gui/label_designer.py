import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QCheckBox, QSlider, QGroupBox, QFormLayout,
    QMessageBox, QScrollArea, QWidget, QColorDialog, QSpinBox,
    QLineEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage, QColor
from ..database.models import ColumnDefinition, SettingsModel
from ..printer.label_printer import LabelRenderer, DEFAULT_TEMPLATE


def load_template(settings_model):
    raw = settings_model.get("label_template")
    if raw:
        try:
            tpl = json.loads(raw)
            merged = dict(DEFAULT_TEMPLATE)
            merged.update(tpl)
            return merged
        except (json.JSONDecodeError, TypeError):
            pass
    return dict(DEFAULT_TEMPLATE)


def save_template(settings_model, template):
    settings_model.set("label_template", json.dumps(template))


class LabelDesignerDialog(QDialog):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.settings = SettingsModel(db) if db else None
        self.column_def = ColumnDefinition(db) if db else None
        self.template = load_template(self.settings)
        self._field_checkboxes = {}
        self._loading = True
        self._setup_ui()
        self._load_template()
        self._loading = False
        self._update_preview()

    def _setup_ui(self):
        self.setWindowTitle("Label Designer")
        self.setMinimumSize(820, 750)
        self.setModal(True)
        layout = QVBoxLayout(self)

        header = QLabel("Customise Label Layout")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #4da6ff; margin-bottom: 4px;")
        layout.addWidget(header)

        body = QHBoxLayout()

        # ═══════════════ Left: controls ═══════════════
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(320)
        left_content = QWidget()
        left = QVBoxLayout(left_content)
        left.setSpacing(6)

        # ── Label size ──
        size_group = QGroupBox("Printable Area (mm)")
        sf = QFormLayout(size_group)
        sw = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(20, 200)
        self.width_spin.setSuffix(" mm")
        self.width_spin.valueChanged.connect(lambda _: self._update_preview())
        sw.addWidget(self.width_spin)
        sw.addWidget(QLabel("×"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 150)
        self.height_spin.setSuffix(" mm")
        self.height_spin.valueChanged.connect(lambda _: self._update_preview())
        sw.addWidget(self.height_spin)
        sf.addRow("Size:", sw)
        left.addWidget(size_group)

        # ── Barcode ──
        qr_group = QGroupBox("Barcode")
        qf = QFormLayout(qr_group)

        self.show_qr = QCheckBox("Show barcode")
        self.show_qr.stateChanged.connect(lambda _: self._update_preview())
        qf.addRow("", self.show_qr)

        self.show_sample_id = QCheckBox("Show sample number")
        self.show_sample_id.stateChanged.connect(lambda _: self._update_preview())
        qf.addRow("", self.show_sample_id)

        self.bc_height = QSlider(Qt.Horizontal)
        self.bc_height.setRange(20, 90)
        self.bc_height.setTickPosition(QSlider.TicksBelow)
        self.bc_height.valueChanged.connect(lambda _: self._update_preview())
        qf.addRow("Height %:", self.bc_height)

        self.bc_width = QSlider(Qt.Horizontal)
        self.bc_width.setRange(30, 100)
        self.bc_width.setTickPosition(QSlider.TicksBelow)
        self.bc_width.valueChanged.connect(lambda _: self._update_preview())
        qf.addRow("Width %:", self.bc_width)

        self.show_qr_code = QCheckBox("Show QR code")
        self.show_qr_code.stateChanged.connect(lambda _: self._update_preview())
        qf.addRow("", self.show_qr_code)

        self.qr_code_size = QSlider(Qt.Horizontal)
        self.qr_code_size.setRange(20, 80)
        self.qr_code_size.setTickPosition(QSlider.TicksBelow)
        self.qr_code_size.valueChanged.connect(lambda _: self._update_preview())
        qf.addRow("QR size %:", self.qr_code_size)

        left.addWidget(qr_group)

        # ── Border ──
        border_group = QGroupBox("Border")
        bf = QFormLayout(border_group)
        self.show_border = QCheckBox("Show border")
        self.show_border.stateChanged.connect(lambda _: self._update_preview())
        bf.addRow("", self.show_border)

        self.border_width_sb = QSpinBox()
        self.border_width_sb.setRange(1, 5)
        self.border_width_sb.valueChanged.connect(lambda _: self._update_preview())
        bf.addRow("Width:", self.border_width_sb)

        self.border_color_btn = QPushButton()
        self.border_color_btn.setFixedHeight(36)
        self.border_color_btn.clicked.connect(lambda: self._pick_color("border_color"))
        bf.addRow("Color:", self.border_color_btn)
        left.addWidget(border_group)

        # ── Text ──
        text_group = QGroupBox("Text")
        tf = QFormLayout(text_group)

        self.font_scale = QSlider(Qt.Horizontal)
        self.font_scale.setRange(50, 180)
        self.font_scale.setTickPosition(QSlider.TicksBelow)
        self.font_scale.valueChanged.connect(lambda _: self._update_preview())
        tf.addRow("Font scale %:", self.font_scale)

        self.line_spacing = QSlider(Qt.Horizontal)
        self.line_spacing.setRange(60, 160)
        self.line_spacing.setTickPosition(QSlider.TicksBelow)
        self.line_spacing.valueChanged.connect(lambda _: self._update_preview())
        tf.addRow("Line spacing %:", self.line_spacing)

        self.show_labels_cb = QCheckBox("Show field labels (e.g. 'Type:')")
        self.show_labels_cb.stateChanged.connect(lambda _: self._update_preview())
        tf.addRow("", self.show_labels_cb)

        self.text_align_cb = QComboBox()
        self.text_align_cb.addItems(["left", "center", "right"])
        self.text_align_cb.currentTextChanged.connect(lambda _: self._update_preview())
        tf.addRow("Text align:", self.text_align_cb)

        self.max_fields_sb = QSpinBox()
        self.max_fields_sb.setRange(1, 10)
        self.max_fields_sb.valueChanged.connect(lambda _: self._update_preview())
        tf.addRow("Max fields:", self.max_fields_sb)

        left.addWidget(text_group)

        # ── Title ──
        title_group = QGroupBox("Title (optional)")
        tif = QFormLayout(title_group)
        self.title_text = QLineEdit()
        self.title_text.setPlaceholderText("Leave empty for no title")
        self.title_text.textChanged.connect(lambda _: self._update_preview())
        tif.addRow("Text:", self.title_text)

        self.title_font_scale = QSlider(Qt.Horizontal)
        self.title_font_scale.setRange(50, 180)
        self.title_font_scale.setTickPosition(QSlider.TicksBelow)
        self.title_font_scale.valueChanged.connect(lambda _: self._update_preview())
        tif.addRow("Size %:", self.title_font_scale)

        self.title_color_btn = QPushButton()
        self.title_color_btn.setFixedHeight(36)
        self.title_color_btn.clicked.connect(lambda: self._pick_color("title_color"))
        tif.addRow("Color:", self.title_color_btn)
        left.addWidget(title_group)

        # ── Colors ──
        color_group = QGroupBox("Colors")
        cf = QFormLayout(color_group)

        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedHeight(36)
        self.bg_color_btn.clicked.connect(lambda: self._pick_color("bg_color"))
        cf.addRow("Background:", self.bg_color_btn)

        self.text_color_btn = QPushButton()
        self.text_color_btn.setFixedHeight(36)
        self.text_color_btn.clicked.connect(lambda: self._pick_color("text_color"))
        cf.addRow("Value text:", self.text_color_btn)

        self.label_color_btn = QPushButton()
        self.label_color_btn.setFixedHeight(36)
        self.label_color_btn.clicked.connect(lambda: self._pick_color("label_color"))
        cf.addRow("Field labels:", self.label_color_btn)

        left.addWidget(color_group)

        # ── Fields ──
        fields_group = QGroupBox("Fields to show (unchecked = hidden)")
        ff = QVBoxLayout(fields_group)
        if self.column_def:
            for col in self.column_def.get_all():
                cb = QCheckBox(col["column_name"])
                cb.stateChanged.connect(lambda _: self._update_preview())
                self._field_checkboxes[col["column_name"]] = cb
                ff.addWidget(cb)
        else:
            ff.addWidget(QLabel("No columns defined."))
        left.addWidget(fields_group)
        left.addStretch()

        left_scroll.setWidget(left_content)
        body.addWidget(left_scroll, 1)

        # ═══════════════ Right: preview ═══════════════
        right = QVBoxLayout()
        preview_group = QGroupBox("Preview")
        pv = QVBoxLayout(preview_group)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(300, 220)
        scroll = QScrollArea()
        scroll.setWidget(self.preview_label)
        scroll.setWidgetResizable(True)
        pv.addWidget(scroll)
        right.addWidget(preview_group)
        body.addLayout(right, 2)

        layout.addLayout(body)

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Template")
        self.save_btn.setStyleSheet("""
            QPushButton { background-color: #4da6ff; color: white; padding: 14px 40px;
                border: none; border-radius: 6px; font-size: 15px; font-weight: bold; }
            QPushButton:hover { background-color: #3d8bd4; }
        """)
        self.save_btn.clicked.connect(self._save)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #555; color: #e0e0e0; padding: 14px 40px;
                border: none; border-radius: 6px; font-size: 15px; }
            QPushButton:hover { background-color: #666; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _load_template(self):
        self.width_spin.setValue(self.template.get("width_mm", 40))
        self.height_spin.setValue(self.template.get("height_mm", 13))
        self.show_qr.setChecked(self.template.get("show_qr", True))
        self.show_sample_id.setChecked(self.template.get("show_sample_id", True))
        self.bc_height.setValue(self.template.get("barcode_height_pct", 60))
        self.bc_width.setValue(self.template.get("barcode_width_pct", 90))
        self.show_qr_code.setChecked(self.template.get("show_qr_code", False))
        self.qr_code_size.setValue(self.template.get("qr_code_size_pct", 40))
        self.show_border.setChecked(self.template.get("show_border", True))
        self.border_width_sb.setValue(self.template.get("border_width", 1))
        self.font_scale.setValue(self.template.get("font_scale", 100))
        self.line_spacing.setValue(self.template.get("line_spacing_pct", 100))
        self.show_labels_cb.setChecked(self.template.get("show_labels", True))
        self.text_align_cb.setCurrentText(self.template.get("text_align", "left"))
        self.max_fields_sb.setValue(self.template.get("max_fields", 4))
        self.title_text.setText(self.template.get("title_text", ""))
        self.title_font_scale.setValue(self.template.get("title_font_scale", 100))
        self._apply_color_btn("bg_color", self.template.get("bg_color", "#ffffff"))
        self._apply_color_btn("text_color", self.template.get("text_color", "#000000"))
        self._apply_color_btn("label_color", self.template.get("label_color", "#666666"))
        self._apply_color_btn("border_color", self.template.get("border_color", "#555555"))
        self._apply_color_btn("title_color", self.template.get("title_color", "#000000"))
        selected = self.template.get("fields", [])
        for name, cb in self._field_checkboxes.items():
            cb.setChecked(not selected or name in selected)

    def _apply_color_btn(self, attr, color):
        btn = getattr(self, f"{attr}_btn", None)
        if btn:
            btn.setStyleSheet(f"background-color: {color}; border: 1px solid #555; border-radius: 4px;")
            btn.setProperty("color_val", color)

    def _pick_color(self, attr):
        current = QColor(getattr(self, f"{attr}_btn").property("color_val") or "#ffffff")
        color = QColorDialog.getColor(current, self, f"Pick {attr}")
        if color.isValid():
            hex_color = color.name()
            self._apply_color_btn(attr, hex_color)
            self._update_preview()

    def _build_template(self):
        selected = [n for n, cb in self._field_checkboxes.items() if cb.isChecked()]
        return {
            "width_mm": self.width_spin.value(),
            "height_mm": self.height_spin.value(),
            "show_qr": self.show_qr.isChecked(),
            "show_sample_id": self.show_sample_id.isChecked(),
            "barcode_height_pct": self.bc_height.value(),
            "barcode_width_pct": self.bc_width.value(),
            "show_qr_code": self.show_qr_code.isChecked(),
            "qr_code_size_pct": self.qr_code_size.value(),
            "show_border": self.show_border.isChecked(),
            "border_width": self.border_width_sb.value(),
            "border_color": self.border_color_btn.property("color_val") or "#555555",
            "bg_color": self.bg_color_btn.property("color_val") or "#ffffff",
            "text_color": self.text_color_btn.property("color_val") or "#000000",
            "label_color": self.label_color_btn.property("color_val") or "#666666",
            "font_scale": self.font_scale.value(),
            "line_spacing_pct": self.line_spacing.value(),
            "show_labels": self.show_labels_cb.isChecked(),
            "text_align": self.text_align_cb.currentText(),
            "max_fields": self.max_fields_sb.value(),
            "title_text": self.title_text.text(),
            "title_color": self.title_color_btn.property("color_val") or "#000000",
            "title_font_scale": self.title_font_scale.value(),
            "fields": selected,
        }

    def _update_preview(self):
        if getattr(self, '_loading', False):
            return
        tpl = self._build_template()
        w = tpl["width_mm"]
        h = tpl["height_mm"]
        dummy = {"Sample ID": "NU0000000001", "Type": "Blood", "Patient": "J. Doe"}
        renderer = LabelRenderer(width_mm=w, height_mm=h)
        img = renderer.render("NU0000000001", dummy, template=tpl)
        img = img.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimage = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        pw = min(400, pixmap.width())
        ph = int(pw * pixmap.height() / pixmap.width())
        scaled = pixmap.scaled(pw, ph, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled)

    def _save(self):
        tpl = self._build_template()
        if self.settings:
            save_template(self.settings, tpl)
            QMessageBox.information(self, "Saved", "Label template saved.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "No database connection.")
