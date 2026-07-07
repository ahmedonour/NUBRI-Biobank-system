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
    "width_mm": 40,
    "height_mm": 13,
    "show_qr": True,
    "show_qr_code": False,
    "show_sample_id": True,
    "barcode_height_pct": 60,
    "barcode_width_pct": 90,
    "qr_code_size_pct": 40,
    "bg_color": "#ffffff",
    "text_color": "#000000",
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
        img = Image.new("RGB", (w, h), tpl["bg_color"])
        draw = ImageDraw.Draw(img)

        margin = max(1, int(h * 3 / 100))
        gap = max(2, int(h * 2 / 100))
        qr_gap = max(4, int(h * 4 / 100))

        show_bc = tpl.get("show_qr", True)
        show_qr = tpl.get("show_qr_code", False)
        barcode_data = fields_dict.get("Sample ID", qr_code) or ""

        bar_h = 0
        bar_w = 0
        bar_x = 0
        bar_y = margin
        qr_size = 0
        qr_x = 0
        qr_y = margin

        if show_bc:
            bar_h = int(h * tpl.get("barcode_height_pct", 60) / 100)
            bar_h = min(bar_h, h - 2 * margin)
            bar_w = int(w * tpl.get("barcode_width_pct", 90) / 100)
            bar_w = max(bar_w, 1)

        if show_qr:
            qr_size = int(h * tpl.get("qr_code_size_pct", 40) / 100)
            qr_size = min(qr_size, h - 2 * margin)
            qr_size = max(qr_size, 1)

        # Center the group (barcode [+ gap + QR]) horizontally
        group_w = 0
        if show_bc:
            group_w += bar_w
        if show_bc and show_qr:
            group_w += qr_gap
        if show_qr:
            group_w += qr_size

        group_x = (w - group_w) // 2
        content_bottom = margin

        if show_bc:
            bar_x = group_x
            self._draw_code128(draw, barcode_data, bar_x, bar_y, bar_w, bar_h)
            content_bottom = bar_y + bar_h
            cur_x = bar_x + bar_w
        else:
            cur_x = group_x

        if show_qr:
            qr_x = cur_x + (qr_gap if show_bc else 0)
            if show_bc and bar_h > 0:
                qr_y = bar_y + (bar_h - qr_size) // 2
            self._draw_qr_code(img, barcode_data, qr_x, qr_y, qr_size)
            content_bottom = max(content_bottom, qr_y + qr_size)

        show_text = tpl.get("show_sample_id", True)
        if show_text and barcode_data:
            text_y = content_bottom + gap
            avail_text_h = h - text_y - margin
            if avail_text_h > 6:
                fs = max(8, min(int(avail_text_h * 0.9), int(w * 0.15)))
                font = _load_font(fs)
                tw = draw.textlength(barcode_data, font)
                tx = (w - tw) / 2
                draw.text((tx, text_y), barcode_data, fill=tpl["text_color"], font=font)

        return img

    def _draw_qr_code(self, img, data, x, y, size):
        import qrcode
        qr = qrcode.QRCode(box_size=2, border=0)
        qr.add_data(data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        qr_img = qr_img.resize((size, size), Image.LANCZOS)
        img.paste(qr_img, (x, y))

    def _draw_code128(self, draw, data, x, y, width, height):
        import barcode
        code128 = barcode.get_barcode_class("code128")
        pattern = code128(data).build()[0]

        total = len(pattern)
        boundaries = [int(x + i * width / total) for i in range(total + 1)]

        for i, bit in enumerate(pattern):
            if bit == "1":
                x1 = boundaries[i]
                x2 = boundaries[i + 1]
                if x2 > x1:
                    draw.rectangle([x1, y, x2 - 1, y + height], fill="black")


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

    def print_label(self, img, copies=1, gap_mm=0):
        if not self._printer:
            self.connect()

        gap_px = int(gap_mm / 25.4 * 203) if gap_mm > 0 else 0

        # Combine all copies + gaps into a single image for reliability
        total_h = img.height * copies + gap_px * (copies - 1)
        combined = Image.new("RGB", (img.width, max(1, total_h)), "white")
        for i in range(copies):
            y = i * (img.height + gap_px)
            combined.paste(img, (0, y))

        path = os.path.join(tempfile.gettempdir(), f"thermal_label_{id(img)}_combined.png")
        combined.save(path)
        self._printer.image(path)
        os.unlink(path)
        self._printer.cut()


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
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation
            )
            painter.drawPixmap(0, 0, scaled)
        finally:
            painter.end()

    def _pil_to_qimage(self, img):
        from PyQt5.QtGui import QImage
        img = img.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        return QImage(data, img.width, img.height, QImage.Format_RGBA8888)


def print_label(qr_code, fields_dict, printer_mode="system", printer_name=None,
                backend="network", host="192.168.1.100", port=9100,
                thermal_copies=1, label_width_mm=40, label_height_mm=13,
                label_gap_mm=3, template=None):
    renderer = LabelRenderer(width_mm=label_width_mm, height_mm=label_height_mm)
    img = renderer.render(qr_code, fields_dict, template=template)

    if printer_mode == "thermal":
        tp = ThermalPrinter(backend, host, port)
        try:
            tp.print_label(img, copies=thermal_copies, gap_mm=label_gap_mm)
        finally:
            tp.disconnect()
    else:
        sp = SystemPrinter(printer_name)
        sp.print_label(img, copies=thermal_copies, width_mm=label_width_mm, height_mm=label_height_mm)
