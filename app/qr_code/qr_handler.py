import os
import io
import qrcode
from PIL import Image


class QRHandler:
    @staticmethod
    def generate(data, box_size=10, border=2):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white")

    @staticmethod
    def generate_and_save(data, filepath, box_size=10, border=2):
        img = QRHandler.generate(data, box_size, border)
        img.save(filepath)
        return filepath

    @staticmethod
    def generate_base64(data, box_size=10, border=2):
        import base64
        img = QRHandler.generate(data, box_size, border)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    @staticmethod
    def decode_from_camera(timeout=30):
        import cv2
        from pyzbar.pyzbar import decode as pyzbar_decode

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        while timeout > 0:
            ret, frame = cap.read()
            if not ret:
                continue

            results = pyzbar_decode(frame)
            for result in results:
                cap.release()
                cv2.destroyAllWindows()
                return result.data.decode("utf-8")

            cv2.imshow("QR Scanner - Press ESC to cancel", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
            timeout -= 0.05

        cap.release()
        cv2.destroyAllWindows()
        return None
