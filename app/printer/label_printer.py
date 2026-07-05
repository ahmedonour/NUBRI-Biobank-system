import os, tempfile
from PIL import Image, ImageDraw, ImageFont
from escpos.printer import Network, Usb, Serial


FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
]


def _load_font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except (IOError, OSError):
                continue
    return ImageFont.load_default()


DEFAULT_TEMPLATE = {
    "width_mm": 50,
    "height_mm": 30,
    "qr_position": "left",
    "qr_size_pct": 65,
    "qr_margin_pct": 3,
    "show_qr": True,
    "show_border": True,
    "border_color": "#555555",
    "border_width": 1,
    "bg_color": "#ffffff",
    "text_color": "#000000",
    "label_color": "#666666",
    "font_scale": 100,
    "line_spacing_pct": 100,
    "show_labels": True,
    "text_align": "left",
    "fields": [],
    "max_fields": 4,
    "title_text": "",
    "title_color": "#000000",
    "title_font_scale": 100,
}


class LabelRenderer:
    def __init__(self, width_mm=50, height_mm=30, dpi=203):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.dpi = dpi

    @property
    def width_px(self):
        return int(self.width_mm / 25.4 * self.dpi)

    @property
    def height_px(self):
        return int(self.height_mm / 25.4 * self.dpi)

    def render(self, qr_code, fields_dict, max_fields=None, template=None):
        tpl = dict(DEFAULT_TEMPLATE)
        if template:
            tpl.update(template)

        w, h = self.width_px, self.height_px
        bg = tpl["bg_color"]
        img = Image.new("RGB", (w, h), bg)
        draw = ImageDraw.Draw(img)

        if tpl["show_border"]:
            bw = tpl["border_width"]
            draw.rectangle([0, 0, w - 1, h - 1], outline=tpl["border_color"], width=bw)

        margin_pct = tpl.get("qr_margin_pct", 3)
        margin = max(1, int(w * margin_pct / 100))
        font_ratio = tpl["font_scale"] / 100
        line_ratio = tpl.get("line_spacing_pct", 100) / 100
        show_labels = tpl.get("show_labels", True)
        text_align = tpl.get("text_align", "left")
        show_qr = tpl.get("show_qr", True)
        max_f = max_fields if max_fields is not None else tpl.get("max_fields", 4)

        gap = int(w * 0.05)
        text_area_left = margin
        text_area_width = w - 2 * margin

        qr_size = int(h * tpl["qr_size_pct"] / 100) if show_qr else 0
        qr_x = 0
        if show_qr:
            qr_left = tpl["qr_position"] == "left"
            if qr_left:
                qr_x = margin
                text_area_left = qr_x + qr_size + gap
            else:
                qr_x = w - margin - qr_size
                text_area_left = margin
            qr_y = max(0, (h - qr_size) // 2)
            qr_path = self._generate_qr(qr_code, qr_size)
            qr_img = Image.open(qr_path).resize((qr_size, qr_size), Image.LANCZOS)
            img.paste(qr_img, (qr_x, qr_y))
            os.unlink(qr_path)

            if not qr_left:
                text_area_width = w - margin - text_area_left

        text_x = text_area_left
        text_w = text_area_width - gap if show_qr else text_area_width

        if text_w > 0 and text_area_width > 0:
            fs_main = max(8, int(h * 0.14 * font_ratio))
            fs_label = max(8, int(h * 0.10 * font_ratio))
            font_main = _load_font(fs_main)
            font_small = _load_font(fs_label) if show_labels else font_main

            if tpl["fields"]:
                ordered = [(f, fields_dict.get(f, "")) for f in tpl["fields"] if f in fields_dict]
            else:
                ordered = list(fields_dict.items())

            items = ordered[:max_f]
            line_h = max(fs_main + 2, int(h * 0.17 * font_ratio * line_ratio))

            title = tpl.get("title_text", "")
            start_y = int(h * 0.06)

            if title:
                ts = max(8, int(h * 0.12 * tpl.get("title_font_scale", 100) / 100))
                ft = _load_font(ts)
                tw = draw.textlength(title, ft)
                tx = text_x
                if text_align == "center":
                    tx = text_x + (text_w - tw) // 2
                elif text_align == "right":
                    tx = text_x + text_w - tw
                draw.text((tx, start_y), title, fill=tpl.get("title_color", "#000000"), font=ft)
                start_y += int(line_h * 0.8)

            for i, (key, value) in enumerate(items):
                y = start_y + i * line_h
                if show_labels:
                    label = f"{key}:"
                    lw = draw.textlength(label, font_small)
                    val = str(value)
                    draw.text((text_x, y), label, fill=tpl["label_color"], font=font_small)
                    draw.text((text_x + lw + 3, y), val, fill=tpl["text_color"], font=font_main)
                else:
                    val = str(value)
                    draw.text((text_x, y), val, fill=tpl["text_color"], font=font_main)

        return img

    def _generate_qr(self, data, size):
        import qrcode
        qr = qrcode.QRCode(box_size=2, border=0)
        qr.add_data(data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        path = os.path.join(tempfile.gettempdir(), f"qr_{data}.png")
        qr_img.save(path)
        return path


class ThermalPrinter:
    def __init__(self, backend="network", host="192.168.1.100", port=9100):
        self.backend = backend
        self.host = host
        self.port = port
        self._printer = None

    def connect(self):
        if self.backend == "network":
            self._printer = Network(self.host, port=self.port)
        elif self.backend == "usb":
            self._printer = Usb(0x0416, 0x5011, timeout=5)
        elif self.backend == "serial":
            self._printer = Serial(devfile="/dev/ttyS0", baudrate=9600)
        else:
            raise ValueError(f"Unknown thermal backend: {self.backend}")

    def disconnect(self):
        if self._printer:
            self._printer.close()
            self._printer = None

    def print_label(self, img):
        if not self._printer:
            self.connect()
        path = os.path.join(tempfile.gettempdir(), f"thermal_label_{id(img)}.png")
        img.save(path)
        self._printer.image(path)
        self._printer.cut()
        os.unlink(path)


class SystemPrinter:
    def __init__(self, printer_name=None):
        self.printer_name = printer_name

    def print_label(self, img, copies=1, width_mm=50, height_mm=30):
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
        from PyQt5.QtGui import QPixmap, QPainter
        from PyQt5.QtCore import Qt, QSizeF

        app = QApplication.instance()
        if not app:
            return

        printer = QPrinter(QPrinter.HighResolution)
        printer.setFullPage(True)

        printer.setPaperSize(QSizeF(width_mm, height_mm), QPrinter.Millimeter)
        printer.setOutputFormat(QPrinter.NativeFormat)
        printer.setCopyCount(copies)

        if self.printer_name:
            printer.setPrinterName(self.printer_name)

        dialog = QPrintDialog(printer)
        if dialog.exec_() != QPrintDialog.Accepted:
            return

        pixmap = QPixmap.fromImage(self._pil_to_qimage(img))
        painter = QPainter(printer)
        try:
            page_rect = printer.pageRect(QPrinter.DevicePixel)
            scaled = pixmap.scaled(
                page_rect.size().toSize(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            x = (page_rect.width() - scaled.width()) / 2
            y = (page_rect.height() - scaled.height()) / 2
            painter.drawPixmap(int(x), int(y), scaled)
        finally:
            painter.end()

    def _pil_to_qimage(self, img):
        from PyQt5.QtGui import QImage
        img = img.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        return QImage(data, img.width, img.height, QImage.Format_RGBA8888)


def print_label(qr_code, fields_dict, printer_mode="system", printer_name=None,
                backend="network", host="192.168.1.100", port=9100,
                thermal_copies=1, label_width_mm=50, label_height_mm=30,
                template=None):
    renderer = LabelRenderer(width_mm=label_width_mm, height_mm=label_height_mm)
    img = renderer.render(qr_code, fields_dict, template=template)

    if printer_mode == "thermal":
        tp = ThermalPrinter(backend, host, port)
        try:
            tp.print_label(img)
        finally:
            tp.disconnect()
    else:
        sp = SystemPrinter(printer_name)
        sp.print_label(img, copies=thermal_copies, width_mm=label_width_mm, height_mm=label_height_mm)
