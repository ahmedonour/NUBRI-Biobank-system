import os
import tempfile
from PIL import Image, ImageDraw, ImageFont
from escpos.printer import Network, Usb, Serial


class LabelPrinter:
    def __init__(self, backend="network", host="192.168.1.100", port=9100):
        self.backend = backend
        self.host = host
        self.port = port
        self.printer = None

    def connect(self):
        if self.backend == "network":
            self.printer = Network(self.host, port=self.port)
        elif self.backend == "usb":
            self.printer = Usb(0x0416, 0x5011, timeout=5)
        elif self.backend == "serial":
            self.printer = Serial(devfile="/dev/ttyS0", baudrate=9600)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def disconnect(self):
        if self.printer:
            self.printer.close()
            self.printer = None

    def print_label(self, qr_code, fields_dict, label_width_mm=100, label_height_mm=50):
        dpi = 203
        width_px = int(label_width_mm / 25.4 * dpi)
        height_px = int(label_height_mm / 25.4 * dpi)

        img = Image.new("RGB", (width_px, height_px), "white")
        draw = ImageDraw.Draw(img)

        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(height_px * 0.15))
            font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(height_px * 0.08))
        except (IOError, OSError):
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        qr_img_path = self._generate_qr_image(qr_code, int(height_px * 0.6))
        qr_img = Image.open(qr_img_path)
        qr_size = int(height_px * 0.6)
        qr_img = qr_img.resize((qr_size, qr_size))
        img.paste(qr_img, (int(width_px * 0.02), int(height_px * 0.2)))

        text_x = qr_size + int(width_px * 0.05)
        text_y = int(height_px * 0.05)
        line_height = int(height_px * 0.12)

        for i, (key, value) in enumerate(fields_dict.items()):
            if i > 5:
                break
            y = text_y + i * line_height
            draw.text((text_x, y), f"{key}: {value}", fill="black", font=font_small)

        if not self.printer:
            self.connect()

        temp_path = os.path.join(tempfile.gettempdir(), f"label_{qr_code}.png")
        img.save(temp_path)

        self.printer.image(temp_path)
        self.printer.cut()

        os.unlink(temp_path)
        os.unlink(qr_img_path)

        return temp_path

    def _generate_qr_image(self, qr_code, size):
        import qrcode
        qr = qrcode.QRCode(box_size=10, border=0)
        qr.add_data(qr_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        temp_path = os.path.join(tempfile.gettempdir(), f"qr_{qr_code}.png")
        img.save(temp_path)
        return temp_path

    def print_raw(self, text):
        if not self.printer:
            self.connect()
        self.printer.text(text)
        self.printer.cut()
