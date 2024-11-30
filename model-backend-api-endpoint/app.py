from dotenv import load_dotenv
import os
import numpy as np
import tensorflow as tf
import requests  # Add this import
import firebase_admin
from firebase_admin import credentials, db
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from flask import Flask, request, jsonify
from PIL import Image, UnidentifiedImageError
import io
import logging
import traceback
import colorsys
import time

# Konfigurasi Firebase
# firebase_config = {
#     'projectId': 'smartfit-capstone',
#     'databaseURL': 'https://db-smartfit.firebaseio.com'
# }
# Inisialisasi Firebase Admin SDK dengan kredensial
cred = credentials.Certificate("./db-smartfit-firebase-adminsdk.json")
firebase_admin.initialize_app(
    cred,
    {
        "databaseURL": "https://smartfit-capstone-default-rtdb.asia-southeast1.firebasedatabase.app/"
    },
)

# Mendapatkan referensi ke Realtime Database
ref = db.reference("/")

# Konfigurasi Logging yang Lebih Komprehensif
logging.basicConfig(
    level=logging.INFO,  # Level log ditetapkan pada INFO untuk menangkap semua log penting
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Format log
    handlers=[
        logging.FileHandler(
            "color_analysis_comprehensive.log", encoding="utf-8"
        ),  # Menyimpan log ke file
        logging.StreamHandler(),  # Menampilkan log di terminal
    ],
)
logger = logging.getLogger(
    __name__
)  # Membuat logger untuk aplikasi, digunakan di seluruh kode


# Mendefinisikan exception khusus untuk kesalahan pemuatan model dan pemrosesan gambar
class ModelLoadError(Exception):
    """
    Exception khusus untuk menangani kesalahan saat memuat model.
    Diperlukan untuk menangani kesalahan khusus saat model tidak dapat dimuat.
    """

    pass


class ImageProcessingError(Exception):
    """
    Exception khusus untuk menangani kesalahan saat memproses gambar.
    Diperlukan untuk menangani masalah yang terjadi selama validasi dan preprocessing gambar.
    """

    pass


# Kelas untuk memuat model dan menganalisis data gambar
class ModelAnalyzer:
    def __init__(self, seasonal_model_path, skintone_model_path):
        """
        Konstruktor untuk ModelAnalyzer.

        Args:
            seasonal_model_path (str): Path ke file model untuk analisis warna musiman.
            skintone_model_path (str): Path ke file model untuk analisis warna kulit.
        """
        self.seasonal_model_path = seasonal_model_path  # Menyimpan path model musiman
        self.skintone_model_path = skintone_model_path  # Menyimpan path model kulit
        self.seasonal_model = None  # Inisialisasi model warna musiman sebagai None
        self.skintone_model = None  # Inisialisasi model warna kulit sebagai None

    def load_models(self):
        """
        Memuat model dari file. Jika model gagal dimuat, exception akan dilemparkan.

        Menangani kesalahan yang mungkin terjadi saat memuat model, seperti FileNotFoundError,
        kesalahan I/O, atau masalah dengan TensorFlow.
        """
        try:
            # Memeriksa apakah path model ada dan file dapat diakses
            if not os.path.exists(self.seasonal_model_path):
                raise FileNotFoundError(
                    f"Model warna musiman tidak ditemukan di {self.seasonal_model_path}"
                )

            if not os.path.exists(self.skintone_model_path):
                raise FileNotFoundError(
                    f"Model warna kulit tidak ditemukan di {self.skintone_model_path}"
                )

            # Memuat model TensorFlow
            self.seasonal_model = load_model(self.seasonal_model_path)
            logger.info(
                f"Model warna musiman berhasil dimuat dari {self.seasonal_model_path}"
            )

            self.skintone_model = load_model(self.skintone_model_path)
            logger.info(
                f"Model warna kulit berhasil dimuat dari {self.skintone_model_path}"
            )

        except (FileNotFoundError, IOError) as path_error:
            # Menangani kesalahan terkait file yang tidak ditemukan atau kesalahan input/output
            error_msg = f"Kesalahan dalam path model: {path_error}"
            logger.error(error_msg)
            raise ModelLoadError(error_msg) from path_error

        except tf.errors.InvalidArgumentError as tf_error:
            # Menangani kesalahan spesifik dari TensorFlow jika model tidak valid
            error_msg = f"Model TensorFlow tidak valid: {tf_error}"
            logger.error(error_msg)
            raise ModelLoadError(error_msg) from tf_error

        except Exception as e:
            # Menangani kesalahan yang tidak diketahui
            error_msg = f"Kesalahan yang tidak diketahui saat memuat model: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())  # Menyimpan jejak error secara rinci
            raise ModelLoadError(error_msg) from e

    def get_skin_tone_hex(self, skin_tone_label):
        """
        Menghasilkan kode warna hexadecimal untuk kategori warna kulit yang berbeda.

        Args:
            skin_tone_label (str): Label kategori warna kulit (misalnya 'Light', 'Medium', 'Dark').

        Returns:
            str: Kode warna hex yang sesuai dengan kategori warna kulit yang diberikan.
        """
        skin_tone_hex_map = {
            "Light": "#F0D2B6",  # Peach Muda
            "Medium": "#C19A6B",  # Camel
            "Dark": "#6B4423",  # Coklat Gelap
            "Unknown": "#FFFFFF",  # Putih sebagai default
        }
        return skin_tone_hex_map.get(
            skin_tone_label, "#FFFFFF"
        )  # Mengembalikan default '#FFFFFF' jika tidak ada kecocokan

    def validate_image(self, image_file):
        """
        Memvalidasi gambar yang diunggah sebelum diproses lebih lanjut.

        Validasi meliputi pengecekan format gambar dan ukuran yang sesuai.

        Args:
            image_file (bytes): Gambar dalam bentuk byte yang diterima melalui HTTP.

        Returns:
            PIL.Image: Objek gambar yang sudah diverifikasi dan disesuaikan ke format RGB/ RGBA.

        Raises:
            ImageProcessingError: Jika gambar rusak atau tidak valid.
        """
        try:
            # Membuka gambar dari byte stream
            img = Image.open(io.BytesIO(image_file))

            # Memeriksa ukuran gambar agar tidak terlalu kecil atau terlalu besar
            min_size, max_size = 50, 4000  # Ukuran gambar minimal dan maksimal
            width, height = img.size
            if width < min_size or height < min_size:
                raise ImageProcessingError(
                    f"Gambar terlalu kecil. Ukuran minimal {min_size}x{min_size} piksel."
                )

            if width > max_size or height > max_size:
                raise ImageProcessingError(
                    f"Gambar terlalu besar. Ukuran maksimal {max_size}x{max_size} piksel."
                )

            # Memastikan gambar berada dalam mode RGB atau RGBA
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")

            return img

        except UnidentifiedImageError:
            # Menangani kesalahan jika gambar tidak dapat dikenali
            raise ImageProcessingError("Format gambar tidak dikenal atau rusak.")
        except IOError:
            # Menangani kesalahan jika gambar gagal dibuka
            raise ImageProcessingError(
                "Gagal membuka gambar. Pastikan file gambar valid."
            )

    def preprocess_image(self, image_file):
        """
        Memproses gambar dengan beberapa ukuran untuk meningkatkan akurasi prediksi.

        Gambar akan diresize menjadi beberapa ukuran yang berbeda, dan setelah itu, diubah menjadi
        array NumPy untuk digunakan dalam model.

        Args:
            image_file (bytes): Gambar yang diterima dalam format byte.

        Returns:
            list: Daftar array gambar yang sudah diproses dalam berbagai ukuran.

        Raises:
            ImageProcessingError: Jika tidak ada gambar yang valid setelah preprocessing.
        """
        processed_images = []
        resize_strategies = [
            (224, 224),
            (128, 128),
            (256, 256),
        ]  # Daftar ukuran yang dicoba untuk resizing

        try:
            # Validasi gambar terlebih dahulu
            img = self.validate_image(image_file)

            for size in resize_strategies:
                try:
                    # Resize gambar ke ukuran yang ditentukan
                    img_resized = img.resize(size)

                    # Mengubah gambar ke array NumPy dan menormalkan nilai pixel
                    img_array = img_to_array(img_resized) / 255.0
                    img_array = np.expand_dims(
                        img_array, axis=0
                    )  # Menambah dimensi untuk batch

                    # Menyimpan gambar yang sudah diproses
                    processed_images.append((img_array, size))

                except Exception as resize_error:
                    # Log kesalahan jika resizing gagal pada ukuran tertentu
                    logger.warning(
                        f"Preprocessing gagal untuk ukuran {size}: {resize_error}"
                    )

            # Jika tidak ada gambar yang berhasil diproses, naikkan kesalahan
            if not processed_images:
                raise ImageProcessingError(
                    "Tidak dapat memproses gambar dengan strategi yang tersedia."
                )

            return processed_images

        except ImageProcessingError as img_error:
            logger.error(f"Kesalahan pemrosesan gambar: {img_error}")
            raise

    def predict(self, image_file, outfit_type="casual"):
        """
        Melakukan prediksi berdasarkan gambar yang diunggah.

        Gambar diproses melalui berbagai ukuran dan model akan digunakan untuk memprediksi
        warna musiman dan warna kulit. Jika hasil prediksi memiliki probabilitas rendah,
        peringatan akan diberikan.

        Args:
            image_file (bytes): Gambar yang akan diprediksi dalam format byte.

        Returns:
            dict: Hasil prediksi dalam format JSON, termasuk label musim dan warna kulit,
                  serta probabilitas prediksi masing-masing.

        Raises:
            ImageProcessingError: Jika kesalahan terjadi selama pemrosesan gambar.
            ValueError: Jika tidak ada hasil prediksi yang valid ditemukan.
        """

        try:
            # Melakukan preprocessing gambar
            processed_images = self.preprocess_image(image_file)

            for processed_image, size in processed_images:
                try:
                    # Memprediksi hasil berdasarkan model warna musiman dan model warna kulit
                    seasonal_prediction = self.seasonal_model.predict(processed_image)
                    skintone_prediction = self.skintone_model.predict(processed_image)

                    # Ambil label dan probabilitas prediksi warna musiman dan warna kulit
                    seasonal_label = int(np.argmax(seasonal_prediction))
                    seasonal_probability = float(np.max(seasonal_prediction)) * 100

                    skintone_label = int(np.argmax(skintone_prediction))
                    skintone_probability = float(np.max(skintone_prediction)) * 100

                    # Tentukan deskripsi label berdasarkan prediksi dan probabilitas
                    seasonal_color_label = ["Winter", "Spring", "Summer", "Autumn"][
                        seasonal_label
                    ]
                    skin_tone_label = ["Light", "Medium", "Dark"][skintone_label]
                    skin_tone_hex = self.get_skin_tone_hex(skin_tone_label)

                    # Menyusun hasil prediksi dalam format JSON
                    return {
                        "seasonal_color_label": seasonal_color_label,
                        "seasonal_probability": seasonal_probability,
                        "skin_tone_label": skin_tone_label,
                        "skin_tone_probability": skintone_probability,
                        "skin_tone_hex": skin_tone_hex,
                    }

                except Exception as prediction_error:
                    logger.warning(
                        f"Prediksi gagal untuk ukuran {size}: {prediction_error}"
                    )

            raise ValueError("Prediksi gagal untuk semua strategi preprocessing")

        except ImageProcessingError as img_error:
            logger.error(f"Kesalahan pemrosesan gambar: {img_error}")
            raise
        except Exception as e:
            logger.error(f"Kesalahan yang tidak diketahui dalam prediksi: {e}")
            raise

    @staticmethod
    def predict_outfit(seasonal_color, skin_tone, clothing_type):
        """
        Generate outfit recommendations based on seasonal color, skin tone, and clothing type.
        """
        recommendations = {
            "formal-men": {
                "Summer": {
                    "Light": [
                        (
                            "Formal Light Blue Blazer",
                            "Blazer biru muda ini menciptakan kesan segar dan cerah, cocok dengan warna kulit terang.",
                        ),
                        (
                            "White Dress Shirt",
                            "Baju putih netral yang sangat cocok dengan warna kulit terang, memberikan kesan bersih dan profesional.",
                        ),
                        (
                            "Light Gray Tailored Trousers",
                            "Celana abu-abu muda melengkapi warna kulit terang Anda dengan kesan yang ringan dan bersih.",
                        ),
                        (
                            "Silver Tie Clip",
                            "Aksen metalik perak memberikan sentuhan elegan yang sederhana.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Professional Suit",
                            "Setelan biru navy ini memberi kesan profesional dan percaya diri, cocok untuk kulit medium.",
                        ),
                        (
                            "Lavender Dress Shirt",
                            "Baju lavender memberi sentuhan unik dan segar pada penampilan formal Anda.",
                        ),
                        (
                            "Charcoal Gray Blazer",
                            "Blazer abu-abu gelap memberikan kontras elegan dengan kulit medium.",
                        ),
                        (
                            "Purple Pocket Square",
                            "Pocket square ungu menambah dimensi warna yang menarik.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Turquoise Blazer",
                            "Blazer biru kehijauan gelap cocok untuk kulit gelap dengan kesan yang lebih tajam dan modern.",
                        ),
                        (
                            "Pale Green Dress Shirt",
                            "Baju hijau pucat memberikan nuansa segar yang cocok dengan warna kulit gelap.",
                        ),
                        (
                            "Beige Dress Trousers",
                            "Celana krem memberikan tampilan yang tenang namun tetap profesional.",
                        ),
                        (
                            "Silver Cufflinks",
                            "Cufflinks perak memberikan aksen yang menambah kesan berkelas.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Soft Yellow Blazer",
                            "Blazer kuning lembut ini memberikan kesan ceria dan hangat, cocok dengan warna kulit terang.",
                        ),
                        (
                            "Light Pink Dress Shirt",
                            "Baju pink muda memberi kesan segar dan lembut.",
                        ),
                        (
                            "Light Brown Chinos",
                            "Celana chinos cokelat muda memberikan tampilan yang lebih ringan namun tetap profesional.",
                        ),
                        (
                            "Light Green Tie",
                            "Kerah hijau muda memberikan aksen segar pada penampilan musim semi Anda.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Pale Blue Blazer",
                            "Blazer biru pucat memberi tampilan profesional namun santai, cocok untuk kulit medium.",
                        ),
                        (
                            "Off-White Dress Shirt",
                            "Baju putih krem memberikan tampilan cerah dan bersih.",
                        ),
                        (
                            "Beige Tailored Trousers",
                            "Celana krem memberikan nuansa elegan namun tidak berlebihan.",
                        ),
                        (
                            "Floral Pocket Square",
                            "Aksesori bermotif bunga memberi kesan dinamis.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Forest Green Blazer",
                            "Blazer hijau tua ini memberi kesan kuat dan elegan, cocok dengan kulit gelap.",
                        ),
                        (
                            "Charcoal Gray Shirt",
                            "Baju abu-abu gelap memberikan kontras yang elegan.",
                        ),
                        (
                            "Olive Green Trousers",
                            "Celana hijau zaitun memberi kesan berani namun tetap santai.",
                        ),
                        (
                            "Muted Purple Tie",
                            "Kerah ungu lembut memberi sentuhan yang menyatu dengan tema warna musim semi.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Blazer",
                            "Blazer oranye terbakar ini memberikan kesan hangat dan menenangkan, cocok untuk kulit terang.",
                        ),
                        (
                            "Light Tan Dress Shirt",
                            "Baju tan lembut memberikan sentuhan elegan dan alami.",
                        ),
                        (
                            "Khaki Trousers",
                            "Celana khaki memberi tampilan santai namun tetap rapi.",
                        ),
                        (
                            "Brown Leather Belt",
                            "Sabuk kulit coklat ini memberi kesan alami dan profesional.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Olive Green Blazer",
                            "Blazer hijau zaitun memberikan kesan profesional dan hangat, cocok dengan kulit medium.",
                        ),
                        (
                            "Deep Red Dress Shirt",
                            "Baju merah tua memberi kesan percaya diri dan berkelas.",
                        ),
                        (
                            "Dark Brown Tailored Trousers",
                            "Celana coklat tua memberikan tampilan yang berkelas dan tegas.",
                        ),
                        (
                            "Plaid Pocket Square",
                            "Pocket square bermotif kotak-kotak memberi kesan dinamis.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Maroon Blazer",
                            "Blazer marun ini memberi kesan kaya dan elegan, cocok untuk kulit gelap.",
                        ),
                        (
                            "Dark Brown Shirt",
                            "Baju coklat tua memberi kesan tegas dan berkelas.",
                        ),
                        (
                            "Dark Green Trousers",
                            "Celana hijau gelap memberi tampilan solid dan terstruktur.",
                        ),
                        (
                            "Leather Watch",
                            "Jam tangan kulit memberi aksen elegan pada penampilan Anda.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Gray Blazer",
                            "Blazer abu-abu terang cocok dengan kulit terang, memberikan kesan profesional dan bersih.",
                        ),
                        (
                            "White Dress Shirt",
                            "Baju putih memberikan kesan netral yang sangat cocok dengan warna kulit terang.",
                        ),
                        (
                            "Charcoal Gray Chinos",
                            "Celana chinos abu-abu gelap memberi tampilan yang profesional dan elegan.",
                        ),
                        (
                            "Silver Tie Bar",
                            "Aksen perak memberi sentuhan elegan yang sederhana.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Suit",
                            "Setelan biru navy memberi kesan formal dan berkelas, sangat cocok dengan kulit medium.",
                        ),
                        (
                            "Light Blue Dress Shirt",
                            "Baju biru muda memberi kesan segar dan menenangkan.",
                        ),
                        (
                            "Gray Wool Trousers",
                            "Celana wol abu-abu memberikan kesan terstruktur dan profesional.",
                        ),
                        (
                            "Striped Pocket Square",
                            "Pocket square dengan motif garis memberi aksen dinamis pada tampilan formal Anda.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Midnight Blue Blazer",
                            "Blazer biru gelap memberi kesan formal dan berkelas, sangat cocok untuk kulit gelap.",
                        ),
                        (
                            "Black Dress Shirt",
                            "Baju hitam memberi kesan tajam dan profesional.",
                        ),
                        (
                            "Black Tailored Trousers",
                            "Celana hitam memberi kesan solid dan sangat elegan.",
                        ),
                        (
                            "Black Leather Shoes",
                            "Sepatu kulit hitam menambah kesan berkelas pada penampilan Anda.",
                        ),
                    ],
                },
            },
            "formal-women": {
                "Summer": {
                    "Light": [
                        (
                            "Pastel Pink Blazer",
                            "Blazer pink pastel ini memberikan kesan segar dan ceria, cocok untuk warna kulit putih.",
                        ),
                        (
                            "White Silk Blouse",
                            "Blus sutra putih memberi kesan elegan dan ringan, sempurna untuk musim panas.",
                        ),
                        (
                            "Beige Pencil Skirt",
                            "Rok pensil beige melengkapi warna kulit putih dengan sentuhan yang lembut dan profesional.",
                        ),
                        (
                            "Silver Hoop Earrings",
                            "Anting lingkaran perak memberikan aksen yang modern dan berkelas.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Coral Blazer",
                            "Blazer coral ini memberikan kesan hangat dan ceria, cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Light Blue Dress Shirt",
                            "Baju biru muda memberikan kontras yang menyegarkan dengan kulit medium.",
                        ),
                        (
                            "White Tailored Trousers",
                            "Celana putih memberikan tampilan yang bersih dan elegan.",
                        ),
                        (
                            "Gold Bracelet",
                            "Gelang emas memberikan aksen yang berkelas dan menarik.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Bright Yellow Blazer",
                            "Blazer kuning cerah ini memberi kesan energik dan modern, cocok untuk kulit hitam.",
                        ),
                        (
                            "Cream Silk Shirt",
                            "Baju sutra krem memberikan kontras yang anggun dan elegan.",
                        ),
                        (
                            "Navy Blue Dress Trousers",
                            "Celana biru navy memberikan tampilan yang profesional dan solid.",
                        ),
                        (
                            "Pearl Necklace",
                            "Kalung mutiara memberikan aksen klasik yang berkelas.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Soft Lavender Blazer",
                            "Blazer lavender lembut ini memberikan kesan segar dan feminin, cocok dengan warna kulit putih.",
                        ),
                        (
                            "Light Green Dress Shirt",
                            "Baju hijau muda memberikan tampilan yang ceria dan natural.",
                        ),
                        (
                            "Light Brown Chinos",
                            "Celana chinos cokelat muda memberikan tampilan yang santai namun tetap elegan.",
                        ),
                        (
                            "Floral Scarf",
                            "Syal bermotif bunga memberikan sentuhan musim semi yang segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Sky Blue Blazer",
                            "Blazer biru langit memberikan tampilan yang cerah dan profesional, cocok untuk kulit medium.",
                        ),
                        (
                            "White Cotton Blouse",
                            "Blus katun putih memberikan tampilan yang ringan dan nyaman.",
                        ),
                        (
                            "Khaki Tailored Trousers",
                            "Celana khaki memberikan kesan elegan namun tetap santai.",
                        ),
                        (
                            "Silver Stud Earrings",
                            "Anting stud perak memberikan aksen sederhana yang berkelas.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Emerald Green Blazer",
                            "Blazer hijau zamrud ini memberikan tampilan yang kuat dan elegan, cocok dengan kulit hitam.",
                        ),
                        (
                            "Black Silk Shirt",
                            "Baju sutra hitam memberikan kesan anggun dan profesional.",
                        ),
                        (
                            "Charcoal Gray Dress Trousers",
                            "Celana abu-abu gelap memberikan tampilan yang solid dan terstruktur.",
                        ),
                        (
                            "Gold Necklace",
                            "Kalung emas memberikan aksen elegan dan berkelas.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Blazer",
                            "Blazer oranye terbakar ini memberikan kesan hangat dan menenangkan, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Cream Wool Sweater",
                            "Sweter wol krem memberikan kesan hangat dan nyaman.",
                        ),
                        (
                            "Brown Tailored Skirt",
                            "Rok cokelat memberikan tampilan yang rapi dan profesional.",
                        ),
                        (
                            "Leather Belt",
                            "Sabuk kulit memberikan aksen yang alami dan elegan.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Olive Green Blazer",
                            "Blazer hijau zaitun memberikan kesan hangat dan profesional, cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Dark Red Dress Shirt",
                            "Baju merah tua memberikan kesan percaya diri dan elegan.",
                        ),
                        (
                            "Brown Wool Trousers",
                            "Celana wol cokelat memberikan tampilan yang terstruktur dan profesional.",
                        ),
                        (
                            "Plaid Scarf",
                            "Syal bermotif kotak-kotak memberikan aksen dinamis pada tampilan musim gugur Anda.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Burgundy Blazer",
                            "Blazer merah marun ini memberikan kesan kaya dan elegan, cocok untuk kulit hitam.",
                        ),
                        (
                            "Dark Brown Silk Blouse",
                            "Blus sutra cokelat tua memberikan tampilan yang anggun dan berkelas.",
                        ),
                        (
                            "Black Dress Trousers",
                            "Celana hitam memberikan tampilan yang solid dan profesional.",
                        ),
                        (
                            "Gold Watch",
                            "Jam tangan emas memberikan aksen berkelas dan elegan.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Blue Blazer",
                            "Blazer biru muda memberikan kesan profesional dan bersih, cocok untuk kulit putih.",
                        ),
                        (
                            "White Wool Sweater",
                            "Sweter wol putih memberikan kesan hangat dan elegan.",
                        ),
                        (
                            "Gray Tailored Trousers",
                            "Celana abu-abu memberikan tampilan yang solid dan rapi.",
                        ),
                        (
                            "Silver Watch",
                            "Jam tangan perak memberikan aksen berkelas dan modern.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Blazer",
                            "Blazer biru navy memberikan kesan formal dan berkelas, sangat cocok dengan kulit medium.",
                        ),
                        (
                            "Light Gray Dress Shirt",
                            "Baju abu-abu muda memberikan kesan segar dan menenangkan.",
                        ),
                        (
                            "Black Wool Trousers",
                            "Celana wol hitam memberikan kesan terstruktur dan profesional.",
                        ),
                        (
                            "Gold Stud Earrings",
                            "Anting stud emas memberikan aksen sederhana namun elegan.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Purple Blazer",
                            "Blazer ungu tua memberikan kesan berkelas dan elegan, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Wool Sweater",
                            "Sweter wol hitam memberikan tampilan yang anggun dan nyaman.",
                        ),
                        (
                            "Charcoal Gray Tailored Trousers",
                            "Celana abu-abu gelap memberikan kesan solid dan terstruktur.",
                        ),
                        (
                            "Black Leather Boots",
                            "Sepatu bot kulit hitam memberikan aksen kuat pada penampilan Anda.",
                        ),
                    ],
                },
            },
            "wedding-men": {
                "Summer": {
                    "Light": [
                        (
                            "Light Gray Suit",
                            "Setelan abu-abu terang ini memberikan kesan elegan dan sejuk, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Sky Blue Dress Shirt",
                            "Baju biru langit memberikan tampilan yang segar dan cerah.",
                        ),
                        (
                            "White Floral Tie",
                            "Dasi bermotif bunga putih memberikan aksen yang romantis dan segar.",
                        ),
                        (
                            "Tan Leather Shoes",
                            "Sepatu kulit tan memberikan kesan hangat dan menambah elegan pada penampilan Anda.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Suit",
                            "Setelan biru navy memberikan kesan profesional dan berkelas, sangat cocok dengan kulit coklat atau sawo matang.",
                        ),
                        (
                            "Lavender Dress Shirt",
                            "Baju lavender memberikan sentuhan warna yang menenangkan dan elegan.",
                        ),
                        (
                            "Silver Silk Tie",
                            "Dasi sutra perak memberikan aksen yang menambah kesan mewah pada penampilan Anda.",
                        ),
                        (
                            "Black Leather Shoes",
                            "Sepatu kulit hitam memberikan tampilan yang rapi dan klasik.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Ivory Suit",
                            "Setelan ivory memberikan kesan elegan dan kontras yang indah, cocok untuk kulit hitam.",
                        ),
                        (
                            "Mint Green Dress Shirt",
                            "Baju hijau mint memberikan kesan segar dan menonjol.",
                        ),
                        (
                            "Dark Green Tie",
                            "Dasi hijau tua memberikan sentuhan warna yang elegan dan berkelas.",
                        ),
                        (
                            "Brown Leather Shoes",
                            "Sepatu kulit coklat memberikan tampilan yang klasik dan elegan.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Beige Suit",
                            "Setelan beige memberikan kesan hangat dan cerah, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Light Pink Dress Shirt",
                            "Baju pink muda memberikan tampilan yang lembut dan romantis.",
                        ),
                        (
                            "Light Blue Silk Tie",
                            "Dasi sutra biru muda memberikan aksen yang segar dan elegan.",
                        ),
                        (
                            "Brown Leather Belt",
                            "Sabuk kulit coklat memberikan kesan alami dan profesional.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Light Gray Suit",
                            "Setelan abu-abu terang memberikan kesan cerah dan elegan, cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "White Dress Shirt",
                            "Baju putih memberikan tampilan yang bersih dan profesional.",
                        ),
                        (
                            "Navy Blue Tie",
                            "Dasi biru navy memberikan aksen yang berkelas.",
                        ),
                        (
                            "Black Leather Shoes",
                            "Sepatu kulit hitam memberikan tampilan yang klasik dan rapi.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Light Blue Suit",
                            "Setelan biru muda memberikan kesan cerah dan elegan, cocok untuk kulit hitam.",
                        ),
                        (
                            "Cream Dress Shirt",
                            "Baju krem memberikan kontras yang lembut dan anggun.",
                        ),
                        (
                            "Maroon Tie",
                            "Dasi marun memberikan sentuhan warna yang kuat dan berkelas.",
                        ),
                        (
                            "Tan Leather Shoes",
                            "Sepatu kulit tan memberikan kesan hangat dan elegan.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Olive Green Suit",
                            "Setelan hijau zaitun memberikan kesan hangat dan alami, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Cream Dress Shirt",
                            "Baju krem memberikan tampilan yang lembut dan elegan.",
                        ),
                        (
                            "Brown Silk Tie",
                            "Dasi sutra coklat memberikan aksen yang alami dan berkelas.",
                        ),
                        (
                            "Brown Leather Shoes",
                            "Sepatu kulit coklat memberikan tampilan yang klasik dan hangat.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Brown Suit",
                            "Setelan coklat memberikan kesan hangat dan elegan, cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Light Blue Dress Shirt",
                            "Baju biru muda memberikan kontras yang segar dan menonjol.",
                        ),
                        (
                            "Burgundy Tie",
                            "Dasi burgundy memberikan aksen warna yang kaya dan berkelas.",
                        ),
                        (
                            "Black Leather Shoes",
                            "Sepatu kulit hitam memberikan tampilan yang klasik dan profesional.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Green Suit",
                            "Setelan hijau tua memberikan kesan kuat dan elegan, cocok untuk kulit hitam.",
                        ),
                        (
                            "White Dress Shirt",
                            "Baju putih memberikan kontras yang tajam dan elegan.",
                        ),
                        (
                            "Gold Silk Tie",
                            "Dasi sutra emas memberikan aksen yang mewah.",
                        ),
                        (
                            "Brown Leather Belt",
                            "Sabuk kulit coklat memberikan tampilan yang alami dan berkelas.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Charcoal Gray Suit",
                            "Setelan abu-abu arang memberikan kesan profesional dan tajam, cocok untuk warna kulit putih.",
                        ),
                        (
                            "White Dress Shirt",
                            "Baju putih memberikan tampilan yang bersih dan klasik.",
                        ),
                        (
                            "Black Silk Tie",
                            "Dasi sutra hitam memberikan aksen yang elegan dan profesional.",
                        ),
                        (
                            "Black Leather Shoes",
                            "Sepatu kulit hitam memberikan tampilan yang klasik dan berkelas.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Black Suit",
                            "Setelan hitam memberikan kesan formal dan berkelas, sangat cocok dengan kulit coklat atau sawo matang.",
                        ),
                        (
                            "Gray Dress Shirt",
                            "Baju abu-abu memberikan kontras yang elegan.",
                        ),
                        (
                            "Silver Tie",
                            "Dasi perak memberikan aksen yang berkelas dan mewah.",
                        ),
                        (
                            "Black Leather Belt",
                            "Sabuk kulit hitam memberikan tampilan yang klasik dan rapi.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Blue Suit",
                            "Setelan biru tua memberikan kesan formal dan tajam, cocok untuk kulit hitam.",
                        ),
                        (
                            "White Dress Shirt",
                            "Baju putih memberikan kontras yang anggun dan elegan.",
                        ),
                        (
                            "Red Silk Tie",
                            "Dasi sutra merah memberikan aksen warna yang kuat dan berkelas.",
                        ),
                        (
                            "Black Leather Shoes",
                            "Sepatu kulit hitam memberikan tampilan yang klasik dan berkelas.",
                        ),
                    ],
                },
            },
            "wedding-women": {
                "Summer": {
                    "Light": [
                        (
                            "Pastel Pink Dress",
                            "Gaun pink pastel ini memberikan kesan lembut dan romantis, cocok untuk warna kulit putih.",
                        ),
                        (
                            "White Lace Shawl",
                            "Selendang renda putih memberikan sentuhan elegan pada tampilan musim panas.",
                        ),
                        (
                            "Beige Heels",
                            "Sepatu hak tinggi beige memberikan tampilan yang ringan dan elegan.",
                        ),
                        (
                            "Silver Clutch Bag",
                            "Tas clutch perak memberikan aksen modern dan berkelas.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Coral Dress",
                            "Gaun coral ini memberikan kesan ceria dan elegan, cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Light Blue Silk Shawl",
                            "Selendang sutra biru muda memberikan aksen yang menyegarkan.",
                        ),
                        (
                            "White Heels",
                            "Sepatu hak tinggi putih memberikan tampilan yang bersih dan elegan.",
                        ),
                        (
                            "Gold Bracelet",
                            "Gelang emas memberikan aksen yang berkelas dan menarik.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Bright Yellow Dress",
                            "Gaun kuning cerah ini memberikan kesan energik dan modern, cocok untuk kulit hitam.",
                        ),
                        (
                            "Cream Silk Shawl",
                            "Selendang sutra krem memberikan kontras yang anggun dan elegan.",
                        ),
                        (
                            "Navy Blue Heels",
                            "Sepatu hak tinggi biru navy memberikan tampilan yang profesional dan solid.",
                        ),
                        (
                            "Pearl Necklace",
                            "Kalung mutiara memberikan aksen klasik yang berkelas.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Soft Lavender Dress",
                            "Gaun lavender lembut ini memberikan kesan feminin dan segar, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Light Green Scarf",
                            "Syal hijau muda memberikan sentuhan warna yang cerah.",
                        ),
                        (
                            "Light Brown Sandals",
                            "Sandal cokelat muda memberikan tampilan yang santai namun tetap elegan.",
                        ),
                        (
                            "Floral Hair Accessory",
                            "Aksesori rambut bermotif bunga memberikan sentuhan musim semi yang segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Sky Blue Dress",
                            "Gaun biru langit memberikan tampilan yang cerah dan profesional, cocok untuk kulit medium.",
                        ),
                        (
                            "White Cotton Scarf",
                            "Syal katun putih memberikan tampilan yang ringan dan nyaman.",
                        ),
                        (
                            "Khaki Sandals",
                            "Sandal khaki memberikan nuansa elegan namun tetap santai.",
                        ),
                        (
                            "Silver Stud Earrings",
                            "Anting stud perak memberikan aksen sederhana yang berkelas.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Emerald Green Dress",
                            "Gaun hijau zamrud memberikan tampilan yang kuat dan elegan, cocok dengan kulit hitam.",
                        ),
                        (
                            "Black Silk Scarf",
                            "Syal sutra hitam memberikan kesan anggun dan profesional.",
                        ),
                        (
                            "Charcoal Gray Heels",
                            "Sepatu hak tinggi abu-abu gelap memberikan tampilan yang solid dan terstruktur.",
                        ),
                        (
                            "Gold Necklace",
                            "Kalung emas memberikan aksen elegan dan berkelas.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Dress",
                            "Gaun oranye terbakar memberikan kesan hangat dan menenangkan, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Cream Wool Shawl",
                            "Selendang wol krem memberikan kesan hangat dan nyaman.",
                        ),
                        (
                            "Brown Heels",
                            "Sepatu hak tinggi cokelat memberikan tampilan yang klasik dan elegan.",
                        ),
                        (
                            "Leather Belt",
                            "Sabuk kulit memberikan aksen yang alami dan elegan.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Olive Green Dress",
                            "Gaun hijau zaitun memberikan kesan hangat dan profesional, cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Dark Red Scarf",
                            "Syal merah tua memberikan kesan percaya diri dan berkelas.",
                        ),
                        (
                            "Brown Wool Trousers",
                            "Celana wol cokelat memberikan tampilan yang terstruktur dan profesional.",
                        ),
                        (
                            "Plaid Scarf",
                            "Syal bermotif kotak-kotak memberikan aksen dinamis pada tampilan musim gugur Anda.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Burgundy Dress",
                            "Gaun merah marun memberikan kesan kaya dan elegan, cocok untuk kulit hitam.",
                        ),
                        (
                            "Dark Brown Silk Scarf",
                            "Syal sutra cokelat tua memberikan tampilan yang anggun dan berkelas.",
                        ),
                        (
                            "Black Heels",
                            "Sepatu hak tinggi hitam memberikan tampilan yang solid dan profesional.",
                        ),
                        (
                            "Gold Watch",
                            "Jam tangan emas memberikan aksen berkelas dan elegan.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Blue Dress",
                            "Gaun biru muda memberikan kesan profesional dan bersih, cocok untuk kulit putih.",
                        ),
                        (
                            "White Wool Scarf",
                            "Syal wol putih memberikan kesan hangat dan elegan.",
                        ),
                        (
                            "Gray Heels",
                            "Sepatu hak tinggi abu-abu memberikan tampilan yang solid dan rapi.",
                        ),
                        (
                            "Silver Watch",
                            "Jam tangan perak memberikan aksen berkelas dan modern.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Dress",
                            "Gaun biru navy memberikan kesan formal dan berkelas, sangat cocok dengan kulit medium.",
                        ),
                        (
                            "Light Gray Scarf",
                            "Syal abu-abu muda memberikan kesan segar dan menenangkan.",
                        ),
                        (
                            "Black Heels",
                            "Sepatu hak tinggi hitam memberikan kesan terstruktur dan profesional.",
                        ),
                        (
                            "Gold Stud Earrings",
                            "Anting stud emas memberikan aksen sederhana namun elegan.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Purple Dress",
                            "Gaun ungu tua memberikan kesan berkelas dan elegan, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Wool Scarf",
                            "Syal wol hitam memberikan tampilan yang anggun dan nyaman.",
                        ),
                        (
                            "Charcoal Gray Heels",
                            "Sepatu hak tinggi abu-abu gelap memberikan kesan solid dan terstruktur.",
                        ),
                        (
                            "Black Leather Boots",
                            "Sepatu bot kulit hitam memberikan aksen kuat pada penampilan Anda.",
                        ),
                    ],
                },
            },
            "streetwear-men": {
                "Summer": {
                    "Light": [
                        (
                            "White Graphic Tee",
                            "Kaos putih dengan desain grafis yang segar, cocok untuk warna kulit putih, memberikan tampilan yang cerah dan modern.",
                        ),
                        (
                            "Light Blue Denim Shorts",
                            "Celana pendek denim biru muda memberikan kesan kasual dan nyaman.",
                        ),
                        (
                            "White Sneakers",
                            "Sepatu sneakers putih memberikan tampilan yang bersih dan trendi.",
                        ),
                        (
                            "Silver Chain Necklace",
                            "Kalung rantai perak memberikan aksen yang stylish pada penampilan Anda.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Black Graphic Tee",
                            "Kaos hitam dengan desain grafis yang keren, cocok untuk kulit coklat atau sawo matang, memberikan kesan edgy dan modern.",
                        ),
                        (
                            "Gray Jogger Pants",
                            "Celana jogger abu-abu memberikan kenyamanan dan gaya yang santai.",
                        ),
                        (
                            "Black High-top Sneakers",
                            "Sepatu sneakers hitam memberikan tampilan yang tajam dan trendi.",
                        ),
                        (
                            "Gold Bracelet",
                            "Gelang emas memberikan aksen yang berkelas dan menarik.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Red Hoodie men",
                            "Hoodie merah memberikan kesan energik dan menonjol, cocok untuk kulit hitam.",
                        ),
                        (
                            "Dark Blue Denim Jeans",
                            "Jeans denim biru gelap memberikan tampilan yang kasual dan solid.",
                        ),
                        (
                            "White High-top Sneakers",
                            "Sepatu sneakers putih memberikan kontras yang cerah dan stylish.",
                        ),
                        (
                            "Leather Wristband",
                            "Gelang kulit memberikan aksen yang kuat dan maskulin.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Pastel Pink Hoodie",
                            "Hoodie pink pastel memberikan tampilan yang lembut dan ceria, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Light Gray Sweatpants",
                            "Sweatpants abu-abu muda memberikan kenyamanan dan gaya kasual.",
                        ),
                        (
                            "White Low-top Sneakers",
                            "Sepatu sneakers putih memberikan tampilan yang bersih dan trendi.",
                        ),
                        (
                            "Floral Baseball Cap",
                            "Topi baseball bermotif bunga memberikan aksen musim semi yang segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Olive Green Cargo Pants",
                            "Celana cargo hijau zaitun memberikan tampilan yang kasual dan fungsional, cocok untuk kulit medium.",
                        ),
                        (
                            "White Crewneck Sweatshirt",
                            "Sweatshirt putih memberikan tampilan yang bersih dan nyaman.",
                        ),
                        (
                            "Black Skate Shoes",
                            "Sepatu skate hitam memberikan tampilan yang edgy dan cool.",
                        ),
                        (
                            "Leather Strap Watch",
                            "Jam tangan dengan tali kulit memberikan aksen elegan.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Bright Orange Windbreaker",
                            "Windbreaker oranye cerah memberikan kesan energik dan modern, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Jogger Pants",
                            "Celana jogger hitam memberikan tampilan yang santai dan keren.",
                        ),
                        (
                            "Gray Sneakers",
                            "Sepatu sneakers abu-abu memberikan kesan yang trendi dan nyaman.",
                        ),
                        (
                            "Sporty Sunglasses",
                            "Kacamata hitam sporty memberikan aksen yang stylish dan fungsional.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Flannel Shirt",
                            "Kemeja flanel oranye terbakar memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Dark Blue Ripped Jeans",
                            "Jeans robek biru gelap memberikan tampilan yang kasual dan edgy.",
                        ),
                        (
                            "Brown Leather Boots",
                            "Sepatu bot kulit coklat memberikan tampilan yang klasik dan maskulin.",
                        ),
                        (
                            "Beanie Hat",
                            "Topi beanie memberikan aksen kasual dan hangat.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Maroon Bomber Jacket",
                            "Jaket bomber marun memberikan kesan hangat dan stylish, cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Black Slim Fit Jeans",
                            "Jeans slim fit hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "White Leather Sneakers",
                            "Sepatu sneakers kulit putih memberikan kontras yang bersih dan trendi.",
                        ),
                        (
                            "Plaid Scarf",
                            "Syal bermotif kotak-kotak memberikan aksen musim gugur yang segar.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Charcoal Gray Hoodie",
                            "Hoodie abu-abu arang memberikan kesan kuat dan elegan, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Cargo Pants",
                            "Celana cargo hitam memberikan tampilan yang kasual dan fungsional.",
                        ),
                        (
                            "Black Combat Boots",
                            "Sepatu bot hitam memberikan tampilan yang solid dan maskulin.",
                        ),
                        (
                            "Leather Gloves",
                            "Sarung tangan kulit memberikan aksen berkelas dan fungsional.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Gray Puffer Jacket",
                            "Jaket puffer abu-abu terang memberikan kesan hangat dan stylish, cocok untuk warna kulit putih.",
                        ),
                        (
                            "White Thermal Shirt",
                            "Kaos thermal putih memberikan lapisan yang nyaman dan hangat.",
                        ),
                        (
                            "Black Skinny Jeans",
                            "Jeans skinny hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "Snow Boots",
                            "Sepatu bot salju memberikan aksen fungsional dan trendi.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Peacoat",
                            "Jaket peacoat biru navy memberikan kesan formal dan berkelas, sangat cocok dengan kulit medium.",
                        ),
                        (
                            "Gray Turtleneck Sweater",
                            "Sweater turtleneck abu-abu memberikan tampilan yang hangat dan elegan.",
                        ),
                        (
                            "Black Chino Pants",
                            "Celana chino hitam memberikan kesan terstruktur dan profesional.",
                        ),
                        (
                            "Brown Leather Gloves",
                            "Sarung tangan kulit coklat memberikan aksen berkelas dan hangat.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Green Parka",
                            "Jaket parka hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Thermal Shirt",
                            "Kaos thermal hitam memberikan lapisan yang anggun dan hangat.",
                        ),
                        (
                            "Charcoal Gray Cargo Pants",
                            "Celana cargo abu-abu gelap memberikan tampilan yang kasual dan fungsional.",
                        ),
                        (
                            "Black Hiking Boots",
                            "Sepatu bot hiking hitam memberikan aksen kuat pada penampilan Anda.",
                        ),
                    ],
                },
            },
            "streetwear-women": {
                "Summer": {
                    "Light": [
                        (
                            "White Crop Top",
                            "Atasan crop putih ini memberikan tampilan yang segar dan modern, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Light Blue High-Waisted Shorts",
                            "Celana pendek high-waisted biru muda memberikan kesan kasual dan stylish.",
                        ),
                        (
                            "White Sneakers",
                            "Sepatu sneakers putih memberikan tampilan yang bersih dan trendi.",
                        ),
                        (
                            "Silver Hoop Earrings",
                            "Anting lingkaran perak memberikan aksen yang modern dan berkelas.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Black Crop Top",
                            "Atasan crop hitam ini memberikan tampilan yang edgy dan stylish, cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Olive Green Cargo Shorts",
                            "Celana cargo hijau zaitun memberikan tampilan yang kasual dan fungsional.",
                        ),
                        (
                            "Black High-top Sneakers",
                            "Sepatu sneakers hitam memberikan tampilan yang tajam dan trendi.",
                        ),
                        (
                            "Gold Chain Necklace",
                            "Kalung rantai emas memberikan aksen yang berkelas dan menarik.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Red Tank Top",
                            "Tank top merah ini memberikan kesan energik dan modern, cocok untuk kulit hitam.",
                        ),
                        (
                            "Dark Blue Denim Shorts",
                            "Celana pendek denim biru gelap memberikan tampilan yang kasual dan solid.",
                        ),
                        (
                            "White High-top Sneakers",
                            "Sepatu sneakers putih memberikan kontras yang cerah dan stylish.",
                        ),
                        (
                            "Leather Wristband",
                            "Gelang kulit memberikan aksen yang kuat dan maskulin.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Pastel Pink Hoodie",
                            "Hoodie pink pastel ini memberikan tampilan yang lembut dan ceria, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Light Gray Sweatpants",
                            "Sweatpants abu-abu muda memberikan kenyamanan dan gaya kasual.",
                        ),
                        (
                            "White Low-top Sneakers",
                            "Sepatu sneakers putih memberikan tampilan yang bersih dan trendi.",
                        ),
                        (
                            "Floral Baseball Cap",
                            "Topi baseball bermotif bunga memberikan aksen musim semi yang segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Olive Green Cargo Pants",
                            "Celana cargo hijau zaitun memberikan tampilan yang kasual dan fungsional, cocok untuk kulit medium.",
                        ),
                        (
                            "White Crop Sweatshirt",
                            "Sweatshirt crop putih memberikan tampilan yang bersih dan nyaman.",
                        ),
                        (
                            "Black Skate Shoes",
                            "Sepatu skate hitam memberikan tampilan yang edgy dan cool.",
                        ),
                        (
                            "Leather Strap Watch",
                            "Jam tangan dengan tali kulit memberikan aksen elegan.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Bright Orange Windbreaker",
                            "Windbreaker oranye cerah memberikan kesan energik dan modern, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Jogger Pants",
                            "Celana jogger hitam memberikan tampilan yang santai dan keren.",
                        ),
                        (
                            "Gray Sneakers",
                            "Sepatu sneakers abu-abu memberikan kesan yang trendi dan nyaman.",
                        ),
                        (
                            "Sporty Sunglasses",
                            "Kacamata hitam sporty memberikan aksen yang stylish dan fungsional.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Flannel Shirt",
                            "Kemeja flanel oranye terbakar memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Dark Blue Ripped Jeans",
                            "Jeans robek biru gelap memberikan tampilan yang kasual dan edgy.",
                        ),
                        (
                            "Brown Leather Boots",
                            "Sepatu bot kulit coklat memberikan tampilan yang klasik dan maskulin.",
                        ),
                        (
                            "Beanie Hat",
                            "Topi beanie memberikan aksen kasual dan hangat.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Maroon Bomber Jacket",
                            "Jaket bomber marun memberikan kesan hangat dan stylish, cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Black Skinny Jeans",
                            "Jeans skinny hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "White Leather Sneakers",
                            "Sepatu sneakers kulit putih memberikan kontras yang bersih dan trendi.",
                        ),
                        (
                            "Plaid Scarf",
                            "Syal bermotif kotak-kotak memberikan aksen musim gugur yang segar.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Charcoal Gray Hoodie",
                            "Hoodie abu-abu arang memberikan kesan kuat dan elegan, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Cargo Pants",
                            "Celana cargo hitam memberikan tampilan yang kasual dan fungsional.",
                        ),
                        (
                            "Black Combat Boots",
                            "Sepatu bot hitam memberikan tampilan yang solid dan maskulin.",
                        ),
                        (
                            "Leather Gloves",
                            "Sarung tangan kulit memberikan aksen berkelas dan fungsional.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Gray Puffer Jacket",
                            "Jaket puffer abu-abu terang memberikan kesan hangat dan stylish, cocok untuk warna kulit putih.",
                        ),
                        (
                            "White Thermal Shirt",
                            "Kaos thermal putih memberikan lapisan yang nyaman dan hangat.",
                        ),
                        (
                            "Black Skinny Jeans",
                            "Jeans skinny hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "Snow Boots",
                            "Sepatu bot salju memberikan aksen fungsional dan trendi.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Peacoat",
                            "Jaket peacoat biru navy memberikan kesan formal dan berkelas, sangat cocok dengan kulit medium.",
                        ),
                        (
                            "Gray Turtleneck Sweater",
                            "Sweater turtleneck abu-abu memberikan tampilan yang hangat dan elegan.",
                        ),
                        (
                            "Black Chino Pants",
                            "Celana chino hitam memberikan kesan terstruktur dan profesional.",
                        ),
                        (
                            "Brown Leather Gloves",
                            "Sarung tangan kulit coklat memberikan aksen berkelas dan hangat.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Green Parka",
                            "Jaket parka hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Thermal Shirt",
                            "Kaos thermal hitam memberikan lapisan yang anggun dan hangat.",
                        ),
                        (
                            "Charcoal Gray Cargo Pants",
                            "Celana cargo abu-abu gelap memberikan tampilan yang kasual dan fungsional.",
                        ),
                        (
                            "Black Hiking Boots",
                            "Sepatu bot hiking hitam memberikan aksen kuat pada penampilan Anda.",
                        ),
                    ],
                },
            },
            "pajamas-men": {
                "Summer": {
                    "Light": [
                        (
                            "Light Blue Short-Sleeve Pajama Set",
                            "Set piyama biru muda dengan lengan pendek ini sangat nyaman dan sejuk, cocok untuk warna kulit putih.",
                        ),
                        (
                            "White Cotton Sleep Shorts",
                            "Celana tidur katun putih memberikan kesan yang bersih dan segar.",
                        ),
                        (
                            "Lightweight Slippers",
                            "Sandal ringan memberikan kenyamanan dan kemudahan saat berjalan di rumah.",
                        ),
                        (
                            "Striped Sleep Tank Top",
                            "Tank top tidur bergaris memberikan kesan santai dan segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Gray Tank Top and Shorts Pajama Set",
                            "Set piyama abu-abu dengan tank top dan celana pendek ini sangat nyaman dan cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Navy Blue Sleep Shorts",
                            "Celana tidur biru navy memberikan kontras yang menarik.",
                        ),
                        (
                            "Soft Cotton Slippers",
                            "Sandal katun lembut memberikan kenyamanan ekstra.",
                        ),
                        (
                            "Black Sleep T-Shirt",
                            "Kaos tidur hitam memberikan tampilan yang modern dan nyaman.",
                        ),
                    ],
                    "Dark": [
                        (
                            "White Linen Pajama Set",
                            "Set piyama linen putih memberikan tampilan yang sejuk dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Dark Green Sleep Shorts",
                            "Celana tidur hijau gelap memberikan tampilan yang elegan.",
                        ),
                        (
                            "Comfortable House Slippers",
                            "Sandal rumah yang nyaman memberikan kemudahan dan kenyamanan.",
                        ),
                        (
                            "Navy Blue Sleep Tank Top",
                            "Tank top tidur biru navy memberikan kesan elegan dan sejuk.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Pastel Green Pajama Set",
                            "Set piyama hijau pastel ini memberikan kesan segar dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "Light Gray Sleep Pants",
                            "Celana tidur abu-abu muda memberikan tampilan yang ringan dan nyaman.",
                        ),
                        (
                            "Soft Slip-On Slippers",
                            "Sandal slip-on lembut memberikan kenyamanan saat berjalan di rumah.",
                        ),
                        (
                            "White Cotton Robe",
                            "Jubah katun putih memberikan kenyamanan tambahan dan tampilan yang anggun.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Blue Striped Pajama Set",
                            "Set piyama dengan garis-garis biru memberikan tampilan yang cerah dan cocok untuk kulit medium.",
                        ),
                        (
                            "White Sleep Pants",
                            "Celana tidur putih memberikan kesan yang bersih dan segar.",
                        ),
                        (
                            "Foam Slippers",
                            "Sandal busa memberikan kenyamanan ekstra saat berjalan di rumah.",
                        ),
                        (
                            "Gray Sleep T-Shirt",
                            "Kaos tidur abu-abu memberikan tampilan yang nyaman dan kasual.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Cream Pajama Set",
                            "Set piyama krem memberikan tampilan yang anggun dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Navy Blue Sleep Pants",
                            "Celana tidur biru navy memberikan kontras yang menarik.",
                        ),
                        (
                            "Fleece Slippers",
                            "Sandal fleece memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                        (
                            "Black Silk Sleep Shirt",
                            "Baju tidur sutra hitam memberikan kesan mewah dan nyaman.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Pajama Set",
                            "Set piyama oranye terbakar ini memberikan kesan hangat dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "Dark Brown Sleep Pants",
                            "Celana tidur cokelat gelap memberikan tampilan yang hangat.",
                        ),
                        (
                            "Wool Slippers",
                            "Sandal wol memberikan kenyamanan dan kehangatan saat musim gugur.",
                        ),
                        (
                            "Cream Knit Sleep Shirt",
                            "Baju tidur rajut krem memberikan tampilan yang lembut dan nyaman.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Olive Green Pajama Set",
                            "Set piyama hijau zaitun memberikan tampilan yang hangat dan cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Maroon Sleep Pants",
                            "Celana tidur merah marun memberikan kontras yang elegan.",
                        ),
                        (
                            "Leather House Slippers",
                            "Sandal rumah kulit memberikan tampilan yang berkelas dan nyaman.",
                        ),
                        (
                            "Charcoal Gray Sleep Shirt",
                            "Baju tidur abu-abu arang memberikan tampilan yang solid dan nyaman.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Brown Pajama Set",
                            "Set piyama cokelat gelap memberikan tampilan yang elegan dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Charcoal Gray Sleep Pants",
                            "Celana tidur abu-abu arang memberikan tampilan yang solid.",
                        ),
                        (
                            "Knitted Slippers",
                            "Sandal rajut memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                        (
                            "Black Velvet Sleep Shirt",
                            "Baju tidur beludru hitam memberikan kesan mewah dan nyaman.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Gray Flannel Pajama Set",
                            "Set piyama flanel abu-abu terang ini memberikan kesan hangat dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "White Thermal Pants",
                            "Celana thermal putih memberikan kehangatan ekstra.",
                        ),
                        (
                            "Fur-Lined Slippers",
                            "Sandal berlapis bulu memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                        (
                            "Navy Blue Sleep Shirt",
                            "Baju tidur biru navy memberikan tampilan elegan dan hangat.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Flannel Pajama Set",
                            "Set piyama flanel biru navy ini memberikan kesan hangat dan cocok untuk kulit medium.",
                        ),
                        (
                            "Gray Thermal Pants",
                            "Celana thermal abu-abu memberikan kehangatan ekstra.",
                        ),
                        (
                            "Cozy Wool Slippers",
                            "Sandal wol yang nyaman memberikan kehangatan dan kenyamanan.",
                        ),
                        (
                            "Red Plaid Sleep Shirt",
                            "Baju tidur kotak-kotak merah memberikan kesan hangat dan kasual.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Green Flannel Pajama Set",
                            "Set piyama flanel hijau tua ini memberikan kesan hangat dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Thermal Pants",
                            "Celana thermal hitam memberikan kehangatan ekstra.",
                        ),
                        (
                            "Heated Slippers",
                            "Sandal pemanas memberikan kenyamanan dan kehangatan yang luar biasa.",
                        ),
                        (
                            "Dark Red Sleep Shirt",
                            "Baju tidur merah gelap memberikan tampilan yang hangat dan menenangkan.",
                        ),
                    ],
                },
            },
            "pajamas-woman": {
                "Summer": {
                    "Light": [
                        (
                            "White Cotton Pajama Set",
                            "Set piyama katun putih ini memberikan kenyamanan dan kesegaran, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Pink Sleep Shorts",
                            "Celana tidur pink memberikan tampilan yang ceria dan ringan.",
                        ),
                        (
                            "Lightweight Slippers",
                            "Sandal ringan memberikan kenyamanan saat berjalan di rumah.",
                        ),
                        (
                            "Striped Sleep Tank Top",
                            "Tank top tidur bergaris memberikan kesan santai dan segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Light Blue Tank Top and Shorts Set",
                            "Set tank top dan celana pendek biru muda ini memberikan tampilan yang segar dan cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Gray Sleep Shorts",
                            "Celana tidur abu-abu memberikan kenyamanan dan gaya kasual.",
                        ),
                        (
                            "Soft Cotton Slippers",
                            "Sandal katun lembut memberikan kenyamanan ekstra.",
                        ),
                        (
                            "Navy Blue Sleep Shirt",
                            "Baju tidur biru navy memberikan tampilan yang elegan.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Yellow Linen Pajama Set",
                            "Set piyama linen kuning ini memberikan tampilan yang cerah dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Dark Green Sleep Shorts",
                            "Celana tidur hijau gelap memberikan tampilan yang elegan.",
                        ),
                        (
                            "Comfortable House Slippers",
                            "Sandal rumah yang nyaman memberikan kemudahan dan kenyamanan.",
                        ),
                        (
                            "Black Silk Sleep Shirt",
                            "Baju tidur sutra hitam memberikan kesan mewah dan nyaman.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Pastel Pink Pajama Set",
                            "Set piyama pink pastel ini memberikan kesan feminin dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "Light Gray Sleep Pants",
                            "Celana tidur abu-abu muda memberikan kenyamanan dan gaya kasual.",
                        ),
                        (
                            "Soft Slip-On Slippers",
                            "Sandal slip-on lembut memberikan kenyamanan saat berjalan di rumah.",
                        ),
                        (
                            "White Cotton Robe",
                            "Jubah katun putih memberikan kenyamanan tambahan dan tampilan yang anggun.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Green Striped Pajama Set",
                            "Set piyama bergaris hijau memberikan tampilan yang segar dan cocok untuk kulit medium.",
                        ),
                        (
                            "White Sleep Pants",
                            "Celana tidur putih memberikan kesan yang bersih dan segar.",
                        ),
                        (
                            "Foam Slippers",
                            "Sandal busa memberikan kenyamanan ekstra saat berjalan di rumah.",
                        ),
                        (
                            "Floral Print Sleep Shirt",
                            "Baju tidur dengan motif bunga memberikan nuansa menyenangkan.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Cream Silk Pajama Set",
                            "Set piyama sutra krem memberikan tampilan yang anggun dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Navy Blue Sleep Pants",
                            "Celana tidur biru navy memberikan kontras yang menarik.",
                        ),
                        (
                            "Fleece Slippers",
                            "Sandal fleece memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                        (
                            "Black Satin Sleep Shirt",
                            "Baju tidur satin hitam memberikan kesan mewah dan anggun.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Pajama Set",
                            "Set piyama oranye terbakar ini memberikan kesan hangat dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "Dark Brown Sleep Pants",
                            "Celana tidur cokelat gelap memberikan tampilan yang hangat.",
                        ),
                        (
                            "Wool Slippers",
                            "Sandal wol memberikan kenyamanan dan kehangatan saat musim gugur.",
                        ),
                        (
                            "Cream Knit Sleep Shirt",
                            "Baju tidur rajut krem memberikan tampilan yang lembut dan nyaman.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Olive Green Pajama Set",
                            "Set piyama hijau zaitun memberikan tampilan yang hangat dan cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Maroon Sleep Pants",
                            "Celana tidur merah marun memberikan kontras yang elegan.",
                        ),
                        (
                            "Leather House Slippers",
                            "Sandal rumah kulit memberikan tampilan yang berkelas dan nyaman.",
                        ),
                        (
                            "Charcoal Gray Sleep Shirt",
                            "Baju tidur abu-abu arang memberikan tampilan yang solid dan nyaman.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Brown Pajama Set",
                            "Set piyama cokelat gelap memberikan tampilan yang elegan dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Charcoal Gray Sleep Pants",
                            "Celana tidur abu-abu arang memberikan tampilan yang solid.",
                        ),
                        (
                            "Knitted Slippers",
                            "Sandal rajut memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                        (
                            "Black Velvet Sleep Shirt",
                            "Baju tidur beludru hitam memberikan kesan mewah dan nyaman.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Gray Flannel Pajama Set",
                            "Set piyama flanel abu-abu terang ini memberikan kesan hangat dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "White Thermal Pants",
                            "Celana thermal putih memberikan kehangatan ekstra.",
                        ),
                        (
                            "Fur-Lined Slippers",
                            "Sandal berlapis bulu memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                        (
                            "Navy Blue Sleep Shirt",
                            "Baju tidur biru navy memberikan tampilan elegan dan hangat.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Flannel Pajama Set",
                            "Set piyama flanel biru navy ini memberikan kesan hangat dan cocok untuk kulit medium.",
                        ),
                        (
                            "Gray Thermal Pants",
                            "Celana thermal abu-abu memberikan kehangatan ekstra.",
                        ),
                        (
                            "Cozy Wool Slippers",
                            "Sandal wol yang nyaman memberikan kehangatan dan kenyamanan.",
                        ),
                        (
                            "Red Plaid Sleep Shirt",
                            "Baju tidur kotak-kotak merah memberikan kesan hangat dan kasual.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Green Flannel Pajama Set",
                            "Set piyama flanel hijau tua ini memberikan kesan hangat dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Thermal Pants",
                            "Celana thermal hitam memberikan kehangatan ekstra.",
                        ),
                        (
                            "Heated Slippers",
                            "Sandal pemanas memberikan kenyamanan dan kehangatan yang luar biasa.",
                        ),
                        (
                            "Dark Red Sleep Shirt",
                            "Baju tidur merah gelap memberikan tampilan yang hangat dan menenangkan.",
                        ),
                    ],
                },
            },
            "casual-men": {
                "Summer": {
                    "Light": [
                        (
                            "White Polo Shirt",
                            "Kaus polo putih memberikan tampilan yang segar dan bersih, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Khaki Shorts",
                            "Celana pendek khaki memberikan kenyamanan dan kesan santai.",
                        ),
                        (
                            "White Canvas Sneakers",
                            "Sepatu kanvas putih memberikan tampilan yang bersih dan stylish.",
                        ),
                        (
                            "Blue Baseball Cap",
                            "Topi baseball biru memberikan aksen yang kasual dan segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue T-Shirt",
                            "Kaos biru navy memberikan tampilan yang klasik dan cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Gray Chino Shorts",
                            "Celana pendek chino abu-abu memberikan kenyamanan dan gaya kasual.",
                        ),
                        (
                            "Black Slip-On Sneakers",
                            "Sepatu slip-on hitam memberikan tampilan yang modern dan nyaman.",
                        ),
                        (
                            "Leather Strap Watch",
                            "Jam tangan dengan tali kulit memberikan aksen elegan.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Light Gray Henley Shirt",
                            "Kaus henley abu-abu terang memberikan tampilan yang elegan dan sejuk, cocok untuk kulit hitam.",
                        ),
                        (
                            "Navy Blue Cargo Shorts",
                            "Celana pendek cargo biru navy memberikan tampilan yang kasual dan fungsional.",
                        ),
                        (
                            "White High-Top Sneakers",
                            "Sepatu sneakers putih memberikan kontras yang cerah dan stylish.",
                        ),
                        (
                            "Beaded Bracelet",
                            "Gelang berbutir memberikan aksen yang kasual dan menarik.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Pastel Green T-Shirt",
                            "Kaos hijau pastel memberikan tampilan yang segar dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "Light Blue Jeans",
                            "Jeans biru muda memberikan kenyamanan dan gaya kasual.",
                        ),
                        (
                            "White Sneakers",
                            "Sepatu sneakers putih memberikan tampilan yang bersih dan trendi.",
                        ),
                        (
                            "Floral Print Cap",
                            "Topi bermotif bunga memberikan aksen musim semi yang segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Olive Green Button-Down Shirt",
                            "Kemeja hijau zaitun memberikan tampilan yang kasual dan elegan, cocok untuk kulit medium.",
                        ),
                        (
                            "Khaki Pants",
                            "Celana khaki memberikan tampilan yang bersih dan nyaman.",
                        ),
                        (
                            "Brown Leather Loafers",
                            "Sepatu loafer kulit coklat memberikan tampilan yang berkelas.",
                        ),
                        (
                            "Aviator Sunglasses",
                            "Kacamata aviator memberikan aksen yang stylish dan fungsional.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Bright Orange Hoodie",
                            "Hoodie oranye cerah memberikan kesan energik dan modern, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Jogger Pants",
                            "Celana jogger hitam memberikan tampilan yang santai dan keren.",
                        ),
                        (
                            "Gray Sneakers",
                            "Sepatu sneakers abu-abu memberikan kesan yang trendi dan nyaman.",
                        ),
                        (
                            "Sporty Sunglasses",
                            "Kacamata hitam sporty memberikan aksen yang stylish dan fungsional.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Flannel Shirt",
                            "Kemeja flanel oranye terbakar memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Dark Blue Ripped Jeans",
                            "Jeans robek biru gelap memberikan tampilan yang kasual dan edgy.",
                        ),
                        (
                            "Brown Leather Boots",
                            "Sepatu bot kulit coklat memberikan tampilan yang klasik dan maskulin.",
                        ),
                        (
                            "Beanie Hat",
                            "Topi beanie memberikan aksen kasual dan hangat.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Maroon Bomber Jacket",
                            "Jaket bomber marun memberikan kesan hangat dan stylish, cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Black Skinny Jeans",
                            "Jeans skinny hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "White Leather Sneakers",
                            "Sepatu sneakers kulit putih memberikan kontras yang bersih dan trendi.",
                        ),
                        (
                            "Plaid Scarf",
                            "Syal bermotif kotak-kotak memberikan aksen musim gugur yang segar.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Charcoal Gray Hoodie",
                            "Hoodie abu-abu arang memberikan kesan kuat dan elegan, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Cargo Pants",
                            "Celana cargo hitam memberikan tampilan yang kasual dan fungsional.",
                        ),
                        (
                            "Black Combat Boots",
                            "Sepatu bot hitam memberikan tampilan yang solid dan maskulin.",
                        ),
                        (
                            "Leather Gloves",
                            "Sarung tangan kulit memberikan aksen berkelas dan fungsional.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Gray Puffer Jacket",
                            "Jaket puffer abu-abu terang memberikan kesan hangat dan stylish, cocok untuk warna kulit putih.",
                        ),
                        (
                            "White Thermal Shirt",
                            "Kaos thermal putih memberikan lapisan yang nyaman dan hangat.",
                        ),
                        (
                            "Black Skinny Jeans",
                            "Jeans skinny hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "Snow Boots",
                            "Sepatu bot salju memberikan aksen fungsional dan trendi.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Peacoat",
                            "Jaket peacoat biru navy memberikan kesan formal dan berkelas, sangat cocok dengan kulit medium.",
                        ),
                        (
                            "Gray Turtleneck Sweater",
                            "Sweater turtleneck abu-abu memberikan tampilan yang hangat dan elegan.",
                        ),
                        (
                            "Black Chino Pants",
                            "Celana chino hitam memberikan kesan terstruktur dan profesional.",
                        ),
                        (
                            "Brown Leather Gloves",
                            "Sarung tangan kulit coklat memberikan aksen berkelas dan hangat.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Green Parka",
                            "Jaket parka hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Thermal Shirt",
                            "Kaos thermal hitam memberikan lapisan yang anggun dan hangat.",
                        ),
                        (
                            "Charcoal Gray Cargo Pants",
                            "Celana cargo abu-abu gelap memberikan tampilan yang kasual dan fungsional.",
                        ),
                        (
                            "Black Hiking Boots",
                            "Sepatu bot hiking hitam memberikan aksen kuat pada penampilan Anda.",
                        ),
                    ],
                },
            },
            "casual-women": {
                "Summer": {
                    "Light": [
                        (
                            "White Sleeveless Top",
                            "Atasan tanpa lengan putih ini memberikan tampilan yang segar dan nyaman, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Denim Shorts",
                            "Celana pendek denim memberikan tampilan kasual dan stylish.",
                        ),
                        (
                            "White Espadrilles",
                            "Sepatu espadrilles putih memberikan kenyamanan dan tampilan yang elegan.",
                        ),
                        (
                            "Straw Hat",
                            "Topi jerami memberikan aksen musim panas yang menyegarkan.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Coral T-Shirt",
                            "Kaos coral memberikan kesan cerah dan cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Khaki Shorts",
                            "Celana pendek khaki memberikan kenyamanan dan kesan santai.",
                        ),
                        (
                            "Beige Sandals",
                            "Sandal beige memberikan tampilan yang ringan dan nyaman.",
                        ),
                        (
                            "Gold Hoop Earrings",
                            "Anting lingkaran emas memberikan aksen yang berkelas dan menarik.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Yellow Tank Top",
                            "Tank top kuning memberikan kesan cerah dan energik, cocok untuk kulit hitam.",
                        ),
                        (
                            "White Linen Shorts",
                            "Celana pendek linen putih memberikan tampilan yang sejuk dan nyaman.",
                        ),
                        (
                            "Navy Blue Sneakers",
                            "Sepatu sneakers biru navy memberikan kontras yang stylish.",
                        ),
                        (
                            "Leather Wristband",
                            "Gelang kulit memberikan aksen yang kasual dan menarik.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Pastel Pink Blouse",
                            "Blus pink pastel ini memberikan kesan feminin dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "Light Blue Jeans",
                            "Jeans biru muda memberikan kenyamanan dan gaya kasual.",
                        ),
                        (
                            "White Ballet Flats",
                            "Sepatu ballet flats putih memberikan tampilan yang elegan dan nyaman.",
                        ),
                        (
                            "Floral Scarf",
                            "Syal bermotif bunga memberikan aksen musim semi yang segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Mint Green Button-Down Shirt",
                            "Kemeja hijau mint memberikan tampilan yang segar dan cocok untuk kulit medium.",
                        ),
                        (
                            "Beige Capris",
                            "Celana capri beige memberikan tampilan yang elegan dan kasual.",
                        ),
                        (
                            "Brown Leather Loafers",
                            "Sepatu loafer kulit coklat memberikan tampilan yang berkelas.",
                        ),
                        (
                            "Pearl Necklace",
                            "Kalung mutiara memberikan aksen klasik yang elegan.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Bright Orange Tank Top",
                            "Tank top oranye cerah memberikan kesan energik dan modern, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Leggings",
                            "Legging hitam memberikan tampilan yang santai dan nyaman.",
                        ),
                        (
                            "Gray Slip-On Sneakers",
                            "Sepatu slip-on abu-abu memberikan kesan yang trendi dan nyaman.",
                        ),
                        (
                            "Sporty Sunglasses",
                            "Kacamata hitam sporty memberikan aksen yang stylish dan fungsional.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Cardigan",
                            "Cardigan oranye terbakar memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Dark Blue Skinny Jeans",
                            "Jeans skinny biru gelap memberikan tampilan yang kasual dan elegan.",
                        ),
                        (
                            "Brown Ankle Boots",
                            "Sepatu bot coklat memberikan tampilan yang klasik dan hangat.",
                        ),
                        (
                            "Plaid Scarf",
                            "Syal kotak-kotak memberikan aksen musim gugur yang stylish.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Maroon Sweater",
                            "Sweater marun memberikan kesan hangat dan cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Black Wide-Leg Pants",
                            "Celana panjang hitam dengan potongan lebar memberikan tampilan yang elegan dan modern.",
                        ),
                        (
                            "White Sneakers",
                            "Sepatu sneakers putih memberikan kontras yang bersih dan trendi.",
                        ),
                        (
                            "Beanie Hat",
                            "Topi beanie memberikan aksen kasual dan hangat.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Olive Green Jacket",
                            "Jaket hijau zaitun memberikan tampilan yang kuat dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Charcoal Gray Skinny Jeans",
                            "Jeans skinny abu-abu arang memberikan tampilan yang solid dan modern.",
                        ),
                        (
                            "Black Combat Boots",
                            "Sepatu bot hitam memberikan tampilan yang kuat dan stylish.",
                        ),
                        (
                            "Leather Gloves",
                            "Sarung tangan kulit memberikan aksen berkelas dan fungsional.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Gray Wool Coat",
                            "Mantel wol abu-abu terang memberikan kesan hangat dan elegan, cocok untuk warna kulit putih.",
                        ),
                        (
                            "White Knit Sweater",
                            "Sweater rajut putih memberikan kenyamanan dan tampilan yang bersih.",
                        ),
                        (
                            "Black Jeans",
                            "Jeans hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "Winter Boots",
                            "Sepatu bot musim dingin memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Overcoat",
                            "Mantel biru navy memberikan tampilan yang berkelas dan cocok untuk kulit medium.",
                        ),
                        (
                            "Gray Wool Turtleneck",
                            "Turtleneck wol abu-abu memberikan kehangatan dan kesan elegan.",
                        ),
                        (
                            "Black Straight-Leg Pants",
                            "Celana panjang hitam dengan potongan lurus memberikan tampilan yang terstruktur dan profesional.",
                        ),
                        (
                            "Brown Leather Gloves",
                            "Sarung tangan kulit coklat memberikan aksen berkelas dan hangat.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Green Parka",
                            "Parka hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Thermal Sweater",
                            "Sweater thermal hitam memberikan kehangatan ekstra.",
                        ),
                        (
                            "Charcoal Gray Cargo Pants",
                            "Celana cargo abu-abu gelap memberikan tampilan yang kasual dan fungsional.",
                        ),
                        (
                            "Black Winter Boots",
                            "Sepatu bot musim dingin hitam memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                    ],
                },
            },
            "sportswear-men": {
                "Summer": {
                    "Light": [
                        (
                            "White Performance T-Shirt",
                            "Kaos performa putih ini memberikan kenyamanan dan kesegaran, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Blue Running Shorts",
                            "Celana pendek lari biru memberikan kenyamanan dan sirkulasi udara yang baik.",
                        ),
                        (
                            "White Running Shoes",
                            "Sepatu lari putih memberikan tampilan yang bersih dan nyaman.",
                        ),
                        (
                            "Sweatband",
                            "Ikatan kepala yang menyerap keringat memberikan kenyamanan tambahan saat berolahraga.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Gray Moisture-Wicking T-Shirt",
                            "Kaos abu-abu dengan bahan yang menyerap keringat, cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Black Training Shorts",
                            "Celana pendek training hitam memberikan tampilan yang modern dan nyaman.",
                        ),
                        (
                            "Red Running Shoes",
                            "Sepatu lari merah memberikan tampilan yang stylish dan fungsional.",
                        ),
                        (
                            "Wristband",
                            "Gelang tangan yang menyerap keringat memberikan kenyamanan saat berolahraga.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Yellow Tank Top",
                            "Tank top kuning memberikan kesan cerah dan energik, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Athletic Shorts",
                            "Celana pendek atletik hitam memberikan tampilan yang kasual dan solid.",
                        ),
                        (
                            "White High-Top Sneakers",
                            "Sepatu sneakers putih memberikan kontras yang cerah dan stylish.",
                        ),
                        (
                            "Compression Socks",
                            "Kaus kaki kompresi memberikan kenyamanan dan mendukung sirkulasi darah.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Pastel Green Tank Top",
                            "Tank top hijau pastel ini memberikan kesan segar dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "Navy Blue Jogging Pants",
                            "Celana jogging biru navy memberikan kenyamanan dan gaya kasual.",
                        ),
                        (
                            "White Running Shoes",
                            "Sepatu lari putih memberikan tampilan yang bersih dan trendi.",
                        ),
                        (
                            "Sweat-Wicking Cap",
                            "Topi yang menyerap keringat memberikan kenyamanan saat berolahraga.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Blue Compression Shirt",
                            "Kaos kompresi biru memberikan dukungan dan kenyamanan ekstra, cocok untuk kulit medium.",
                        ),
                        (
                            "Gray Athletic Pants",
                            "Celana atletik abu-abu memberikan kenyamanan dan gaya kasual.",
                        ),
                        (
                            "Black Running Shoes",
                            "Sepatu lari hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "Sporty Sunglasses",
                            "Kacamata hitam sporty memberikan aksen yang stylish dan fungsional.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Bright Orange Athletic Shirt",
                            "Kaos atletik oranye cerah memberikan kesan energik dan modern, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Jogger Pants",
                            "Celana jogger hitam memberikan tampilan yang santai dan keren.",
                        ),
                        (
                            "Gray Sneakers",
                            "Sepatu sneakers abu-abu memberikan kesan yang trendi dan nyaman.",
                        ),
                        (
                            "Fitness Tracker",
                            "Pelacak kebugaran memberikan informasi tentang aktivitas olahraga Anda.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Hoodie",
                            "Hoodie oranye terbakar memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Black Running Pants",
                            "Celana lari hitam memberikan kenyamanan dan perlindungan.",
                        ),
                        (
                            "Brown Training Shoes",
                            "Sepatu training coklat memberikan tampilan yang klasik dan solid.",
                        ),
                        (
                            "Running Gloves",
                            "Sarung tangan lari memberikan kenyamanan dan kehangatan.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Maroon Long-Sleeve Shirt",
                            "Kaos lengan panjang marun memberikan kesan hangat dan cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Black Training Pants",
                            "Celana training hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "White Running Shoes",
                            "Sepatu lari putih memberikan kontras yang bersih dan trendi.",
                        ),
                        (
                            "Thermal Hat",
                            "Topi thermal memberikan kenyamanan dan kehangatan saat musim dingin.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Olive Green Windbreaker",
                            "Windbreaker hijau zaitun memberikan tampilan yang kuat dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Gray Jogging Pants",
                            "Celana jogging abu-abu memberikan tampilan yang santai dan nyaman.",
                        ),
                        (
                            "Black Running Shoes",
                            "Sepatu lari hitam memberikan tampilan yang solid dan stylish.",
                        ),
                        (
                            "Sweat-Wicking Headband",
                            "Ikatan kepala yang menyerap keringat memberikan kenyamanan tambahan saat berolahraga.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Gray Fleece Jacket",
                            "Jaket fleece abu-abu terang memberikan kesan hangat dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "Black Thermal Pants",
                            "Celana thermal hitam memberikan kehangatan ekstra.",
                        ),
                        (
                            "Fur-Lined Sneakers",
                            "Sepatu sneakers berlapis bulu memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                        (
                            "Winter Running Gloves",
                            "Sarung tangan lari musim dingin memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Puffer Vest",
                            "Rompi puffer biru navy memberikan kesan hangat dan cocok untuk kulit medium.",
                        ),
                        (
                            "Gray Sweatpants",
                            "Celana sweatpants abu-abu memberikan kenyamanan dan kehangatan.",
                        ),
                        (
                            "Black Running Shoes",
                            "Sepatu lari hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "Insulated Headband",
                            "Ikatan kepala berinsulasi memberikan kenyamanan dan kehangatan saat musim dingin.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Green Thermal Jacket",
                            "Jaket thermal hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Fleece Pants",
                            "Celana fleece hitam memberikan kehangatan ekstra.",
                        ),
                        (
                            "Heated Sneakers",
                            "Sepatu sneakers dengan fitur pemanas memberikan kenyamanan dan kehangatan yang luar biasa.",
                        ),
                        (
                            "Thermal Socks",
                            "Kaos kaki thermal memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                    ],
                },
            },
            "sportswear-women": {
                "Summer": {
                    "Light": [
                        (
                            "White Sports Bra",
                            "Bra olahraga putih ini memberikan dukungan dan kenyamanan, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Light Blue Running Shorts",
                            "Celana pendek lari biru muda memberikan kenyamanan dan sirkulasi udara yang baik.",
                        ),
                        (
                            "White Running Shoes",
                            "Sepatu lari putih memberikan tampilan yang bersih dan nyaman.",
                        ),
                        (
                            "Sweat-Wicking Headband",
                            "Ikatan kepala yang menyerap keringat memberikan kenyamanan tambahan saat berolahraga.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Gray Sports Tank",
                            "Tank olahraga abu-abu ini memberikan kenyamanan dan tampilan yang modern, cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Black Bike Shorts",
                            "Celana pendek sepeda hitam memberikan tampilan yang fungsional dan stylish.",
                        ),
                        (
                            "Red Running Shoes",
                            "Sepatu lari merah memberikan tampilan yang stylish dan fungsional.",
                        ),
                        (
                            "Wristband",
                            "Gelang tangan yang menyerap keringat memberikan kenyamanan saat berolahraga.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Bright Yellow Sports Bra",
                            "Bra olahraga kuning cerah ini memberikan kesan energik dan modern, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Athletic Shorts",
                            "Celana pendek atletik hitam memberikan tampilan yang kasual dan solid.",
                        ),
                        (
                            "White High-Top Sneakers",
                            "Sepatu sneakers putih memberikan kontras yang cerah dan stylish.",
                        ),
                        (
                            "Compression Socks",
                            "Kaus kaki kompresi memberikan kenyamanan dan mendukung sirkulasi darah.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Pastel Green Sports Tank",
                            "Tank olahraga hijau pastel ini memberikan kesan segar dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "Navy Blue Leggings",
                            "Legging biru navy memberikan kenyamanan dan tampilan yang kasual.",
                        ),
                        (
                            "White Running Shoes",
                            "Sepatu lari putih memberikan tampilan yang bersih dan trendi.",
                        ),
                        (
                            "Sweat-Wicking Cap",
                            "Topi yang menyerap keringat memberikan kenyamanan saat berolahraga.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Blue Compression Shirt",
                            "Kaos kompresi biru memberikan dukungan dan kenyamanan ekstra, cocok untuk kulit medium.",
                        ),
                        (
                            "Gray Athletic Pants",
                            "Celana atletik abu-abu memberikan kenyamanan dan gaya kasual.",
                        ),
                        (
                            "Black Running Shoes",
                            "Sepatu lari hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "Sporty Sunglasses",
                            "Kacamata hitam sporty memberikan aksen yang stylish dan fungsional.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Bright Orange Sports Tank",
                            "Tank olahraga oranye cerah ini memberikan kesan energik dan modern, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Jogger Pants",
                            "Celana jogger hitam memberikan tampilan yang santai dan keren.",
                        ),
                        (
                            "Gray Sneakers",
                            "Sepatu sneakers abu-abu memberikan kesan yang trendi dan nyaman.",
                        ),
                        (
                            "Fitness Tracker",
                            "Pelacak kebugaran memberikan informasi tentang aktivitas olahraga Anda.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Hoodie",
                            "Hoodie oranye terbakar ini memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Black Running Pants",
                            "Celana lari hitam memberikan kenyamanan dan perlindungan.",
                        ),
                        (
                            "Brown Training Shoes",
                            "Sepatu training coklat memberikan tampilan yang klasik dan solid.",
                        ),
                        (
                            "Running Gloves",
                            "Sarung tangan lari memberikan kenyamanan dan kehangatan.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Maroon Long-Sleeve Shirt",
                            "Kaos lengan panjang marun ini memberikan kesan hangat dan cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Black Training Pants",
                            "Celana training hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "White Running Shoes",
                            "Sepatu lari putih memberikan kontras yang bersih dan trendi.",
                        ),
                        (
                            "Thermal Hat",
                            "Topi thermal memberikan kenyamanan dan kehangatan saat musim dingin.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Olive Green Windbreaker",
                            "Windbreaker hijau zaitun ini memberikan tampilan yang kuat dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Gray Jogging Pants",
                            "Celana jogging abu-abu memberikan tampilan yang santai dan nyaman.",
                        ),
                        (
                            "Black Running Shoes",
                            "Sepatu lari hitam memberikan tampilan yang solid dan stylish.",
                        ),
                        (
                            "Sweat-Wicking Headband",
                            "Ikatan kepala yang menyerap keringat memberikan kenyamanan tambahan saat berolahraga.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Gray Fleece Jacket",
                            "Jaket fleece abu-abu terang ini memberikan kesan hangat dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "Black Thermal Pants",
                            "Celana thermal hitam memberikan kehangatan ekstra.",
                        ),
                        (
                            "Fur-Lined Sneakers",
                            "Sepatu sneakers berlapis bulu memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                        (
                            "Winter Running Gloves",
                            "Sarung tangan lari musim dingin memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Puffer Vest",
                            "Rompi puffer biru navy ini memberikan kesan hangat dan cocok untuk kulit medium.",
                        ),
                        (
                            "Gray Sweatpants",
                            "Celana sweatpants abu-abu memberikan kenyamanan dan kehangatan.",
                        ),
                        (
                            "Black Running Shoes",
                            "Sepatu lari hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "Insulated Headband",
                            "Ikatan kepala berinsulasi memberikan kenyamanan dan kehangatan saat musim dingin.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Green Thermal Jacket",
                            "Jaket thermal hijau tua ini memberikan kesan hangat dan kuat, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Fleece Pants",
                            "Celana fleece hitam memberikan kehangatan ekstra.",
                        ),
                        (
                            "Heated Sneakers",
                            "Sepatu sneakers dengan fitur pemanas memberikan kenyamanan dan kehangatan yang luar biasa.",
                        ),
                        (
                            "Thermal Socks",
                            "Kaos kaki thermal memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                    ],
                },
            },
            "vintage-men": {
                "Summer": {
                    "Light": [
                        (
                            "White Linen Shirt",
                            "Kemeja linen putih ini memberikan tampilan yang klasik dan sejuk, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Khaki High-Waisted Shorts",
                            "Celana pendek high-waisted khaki memberikan tampilan yang klasik dan santai.",
                        ),
                        (
                            "Brown Leather Loafers",
                            "Sepatu loafer kulit coklat memberikan tampilan yang elegan dan berkelas.",
                        ),
                        (
                            "Straw Fedora Hat",
                            "Topi fedora jerami memberikan aksen vintage yang segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Light Blue Chambray Shirt",
                            "Kemeja chambray biru muda ini memberikan tampilan yang kasual dan cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Beige Pleated Trousers",
                            "Celana panjang berlipat beige memberikan tampilan yang klasik dan nyaman.",
                        ),
                        (
                            "White Canvas Sneakers",
                            "Sepatu kanvas putih memberikan kontras yang bersih dan stylish.",
                        ),
                        (
                            "Leather Strap Watch",
                            "Jam tangan dengan tali kulit memberikan aksen elegan dan klasik.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Navy Blue Henley Shirt",
                            "Kaus henley biru navy memberikan tampilan yang klasik dan sejuk, cocok untuk kulit hitam.",
                        ),
                        (
                            "Olive Green Chino Shorts",
                            "Celana pendek chino hijau zaitun memberikan tampilan yang kasual dan fungsional.",
                        ),
                        (
                            "Black Leather Oxfords",
                            "Sepatu oxford kulit hitam memberikan tampilan yang elegan dan berkelas.",
                        ),
                        (
                            "Flat Cap",
                            "Topi datar memberikan aksen vintage yang klasik.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Pastel Yellow Polo Shirt",
                            "Kaus polo kuning pastel ini memberikan tampilan yang segar dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "Light Gray Tailored Trousers",
                            "Celana panjang tailored abu-abu muda memberikan kenyamanan dan gaya kasual.",
                        ),
                        (
                            "White Brogues",
                            "Sepatu brogue putih memberikan tampilan yang elegan dan klasik.",
                        ),
                        (
                            "Floral Pocket Square",
                            "Pocket square bermotif bunga memberikan aksen vintage yang segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Mint Green Button-Down Shirt",
                            "Kemeja hijau mint ini memberikan tampilan yang segar dan cocok untuk kulit medium.",
                        ),
                        (
                            "Brown Corduroy Pants",
                            "Celana corduroy coklat memberikan tampilan yang klasik dan nyaman.",
                        ),
                        (
                            "Beige Desert Boots",
                            "Sepatu desert beige memberikan tampilan yang kasual dan elegan.",
                        ),
                        (
                            "Vintage Leather Belt",
                            "Sabuk kulit vintage memberikan aksen yang klasik dan berkelas.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Bright Orange Short-Sleeve Shirt",
                            "Kemeja lengan pendek oranye cerah ini memberikan kesan energik dan modern, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Wide-Leg Trousers",
                            "Celana panjang hitam dengan potongan lebar memberikan tampilan yang elegan dan modern.",
                        ),
                        (
                            "Brown Leather Moccasins",
                            "Sepatu mokasin kulit coklat memberikan tampilan yang klasik dan nyaman.",
                        ),
                        (
                            "Vintage Sunglasses",
                            "Kacamata hitam vintage memberikan aksen yang stylish dan fungsional.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Cardigan",
                            "Cardigan oranye terbakar memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Dark Blue Straight-Leg Jeans",
                            "Jeans dengan potongan lurus biru gelap memberikan tampilan yang kasual dan elegan.",
                        ),
                        (
                            "Brown Brogue Shoes",
                            "Sepatu brogue coklat memberikan tampilan yang klasik dan berkelas.",
                        ),
                        (
                            "Wool Scarf",
                            "Syal wol memberikan kehangatan dan aksen vintage.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Maroon Crewneck Sweater",
                            "Sweater crewneck marun ini memberikan kesan hangat dan cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Black Dress Trousers",
                            "Celana panjang hitam memberikan tampilan yang elegan dan profesional.",
                        ),
                        (
                            "White Leather Sneakers",
                            "Sepatu sneakers kulit putih memberikan kontras yang bersih dan trendi.",
                        ),
                        (
                            "Newsboy Cap",
                            "Topi newsboy memberikan aksen vintage yang klasik.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Olive Green Blazer",
                            "Blazer hijau zaitun memberikan tampilan yang kuat dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Charcoal Gray Wool Pants",
                            "Celana wol abu-abu arang memberikan tampilan yang solid dan modern.",
                        ),
                        (
                            "Black Chelsea Boots",
                            "Sepatu bot chelsea hitam memberikan tampilan yang kuat dan stylish.",
                        ),
                        (
                            "Leather Gloves",
                            "Sarung tangan kulit memberikan aksen berkelas dan fungsional.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Gray Wool Overcoat",
                            "Mantel wol abu-abu terang memberikan kesan hangat dan elegan, cocok untuk warna kulit putih.",
                        ),
                        (
                            "White Turtleneck Sweater",
                            "Sweater turtleneck putih memberikan kenyamanan dan tampilan yang bersih.",
                        ),
                        (
                            "Black Dress Pants",
                            "Celana panjang hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "Leather Winter Boots",
                            "Sepatu bot musim dingin kulit memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Peacoat",
                            "Jaket peacoat biru navy memberikan tampilan yang berkelas dan cocok untuk kulit medium.",
                        ),
                        (
                            "Gray Wool Turtleneck",
                            "Turtleneck wol abu-abu memberikan kehangatan dan kesan elegan.",
                        ),
                        (
                            "Black Straight-Leg Pants",
                            "Celana panjang hitam dengan potongan lurus memberikan tampilan yang terstruktur dan profesional.",
                        ),
                        (
                            "Brown Leather Gloves",
                            "Sarung tangan kulit coklat memberikan aksen berkelas dan hangat.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Green Parka",
                            "Parka hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Thermal Sweater",
                            "Sweater thermal hitam memberikan kehangatan ekstra.",
                        ),
                        (
                            "Charcoal Gray Cargo Pants",
                            "Celana cargo abu-abu gelap memberikan tampilan yang kasual dan fungsional.",
                        ),
                        (
                            "Black Winter Boots",
                            "Sepatu bot musim dingin hitam memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                    ],
                },
            },
            "vintage-women": {
                "Summer": {
                    "Light": [
                        (
                            "White Lace Blouse",
                            "Blus renda putih ini memberikan tampilan yang klasik dan feminin, cocok untuk warna kulit putih.",
                        ),
                        (
                            "High-Waisted Denim Shorts",
                            "Celana pendek denim high-waisted memberikan tampilan kasual yang vintage.",
                        ),
                        (
                            "Brown Leather Sandals",
                            "Sandal kulit coklat memberikan kenyamanan dan tampilan yang elegan.",
                        ),
                        (
                            "Straw Hat",
                            "Topi jerami memberikan aksen vintage yang segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Light Blue Chambray Dress",
                            "Gaun chambray biru muda ini memberikan tampilan kasual yang cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Beige Espadrilles",
                            "Espadrilles beige memberikan kenyamanan dan tampilan yang stylish.",
                        ),
                        (
                            "Leather Belt",
                            "Sabuk kulit memberikan aksen vintage yang berkelas.",
                        ),
                        (
                            "Vintage Sunglasses",
                            "Kacamata hitam vintage memberikan aksen yang stylish dan fungsional.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Red Polka Dot Blouse",
                            "Blus polka dot merah ini memberikan tampilan yang ceria dan cocok untuk kulit hitam.",
                        ),
                        (
                            "White Linen Pants",
                            "Celana linen putih memberikan tampilan yang sejuk dan nyaman.",
                        ),
                        (
                            "Navy Blue Flats",
                            "Sepatu flats biru navy memberikan kenyamanan dan tampilan yang elegan.",
                        ),
                        (
                            "Silk Scarf",
                            "Syal sutra memberikan aksen vintage yang klasik.",
                        ),
                    ],
                },
                "Spring": {
                    "Light": [
                        (
                            "Pastel Pink Cardigan",
                            "Cardigan pink pastel ini memberikan tampilan yang segar dan cocok untuk warna kulit putih.",
                        ),
                        (
                            "Light Gray A-Line Skirt",
                            "Rok A-line abu-abu muda memberikan tampilan yang feminin dan elegan.",
                        ),
                        (
                            "White Mary Janes",
                            "Sepatu Mary Janes putih memberikan tampilan yang klasik dan nyaman.",
                        ),
                        (
                            "Floral Brooch",
                            "Brooch bermotif bunga memberikan aksen vintage yang segar.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Mint Green Wrap Dress",
                            "Gaun wrap hijau mint ini memberikan tampilan yang segar dan cocok untuk kulit medium.",
                        ),
                        (
                            "Beige Kitten Heels",
                            "Sepatu kitten heels beige memberikan kenyamanan dan tampilan yang elegan.",
                        ),
                        (
                            "Leather Satchel Bag",
                            "Tas satchel kulit memberikan tampilan yang klasik dan berkelas.",
                        ),
                        (
                            "Pearl Necklace",
                            "Kalung mutiara memberikan aksen vintage yang klasik.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Bright Orange Sundress",
                            "Gaun sundress oranye cerah ini memberikan kesan energik dan modern, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Wide-Brim Hat",
                            "Topi bertepi lebar hitam memberikan tampilan yang elegan dan melindungi dari sinar matahari.",
                        ),
                        (
                            "Brown Leather Loafers",
                            "Sepatu loafer kulit coklat memberikan tampilan yang nyaman dan berkelas.",
                        ),
                        (
                            "Vintage Earrings",
                            "Anting vintage memberikan aksen yang klasik dan stylish.",
                        ),
                    ],
                },
                "Autumn": {
                    "Light": [
                        (
                            "Burnt Orange Knit Sweater",
                            "Sweater rajut oranye terbakar ini memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih.",
                        ),
                        (
                            "Dark Blue Straight-Leg Jeans",
                            "Jeans dengan potongan lurus biru gelap memberikan tampilan yang kasual dan elegan.",
                        ),
                        (
                            "Brown Ankle Boots",
                            "Sepatu bot coklat memberikan tampilan yang klasik dan hangat.",
                        ),
                        (
                            "Wool Scarf",
                            "Syal wol memberikan kehangatan dan aksen vintage.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Maroon Corduroy Skirt",
                            "Rok corduroy marun ini memberikan kesan hangat dan cocok untuk kulit coklat atau sawo matang.",
                        ),
                        (
                            "Black Turtleneck Sweater",
                            "Sweater turtleneck hitam memberikan tampilan yang elegan dan hangat.",
                        ),
                        (
                            "White Ankle Boots",
                            "Sepatu bot putih memberikan kontras yang bersih dan trendi.",
                        ),
                        (
                            "Vintage Brooch",
                            "Brooch vintage memberikan aksen yang klasik dan berkelas.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Olive Green Trench Coat",
                            "Mantel trench hijau zaitun memberikan tampilan yang kuat dan cocok untuk kulit hitam.",
                        ),
                        (
                            "Charcoal Gray Wool Pants",
                            "Celana wol abu-abu arang memberikan tampilan yang solid dan modern.",
                        ),
                        (
                            "Black Chelsea Boots",
                            "Sepatu bot chelsea hitam memberikan tampilan yang kuat dan stylish.",
                        ),
                        (
                            "Leather Gloves",
                            "Sarung tangan kulit memberikan aksen berkelas dan fungsional.",
                        ),
                    ],
                },
                "Winter": {
                    "Light": [
                        (
                            "Light Gray Wool Coat",
                            "Mantel wol abu-abu terang memberikan kesan hangat dan elegan, cocok untuk warna kulit putih.",
                        ),
                        (
                            "White Knit Sweater",
                            "Sweater rajut putih memberikan kenyamanan dan tampilan yang bersih.",
                        ),
                        (
                            "Black Jeans",
                            "Jeans hitam memberikan tampilan yang tajam dan modern.",
                        ),
                        (
                            "Winter Boots",
                            "Sepatu bot musim dingin memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                    ],
                    "Medium": [
                        (
                            "Navy Blue Peacoat",
                            "Jaket peacoat biru navy memberikan tampilan yang berkelas dan cocok untuk kulit medium.",
                        ),
                        (
                            "Gray Wool Turtleneck",
                            "Turtleneck wol abu-abu memberikan kehangatan dan kesan elegan.",
                        ),
                        (
                            "Black Straight-Leg Pants",
                            "Celana panjang hitam dengan potongan lurus memberikan tampilan yang terstruktur dan profesional.",
                        ),
                        (
                            "Brown Leather Gloves",
                            "Sarung tangan kulit coklat memberikan aksen berkelas dan hangat.",
                        ),
                    ],
                    "Dark": [
                        (
                            "Dark Green Parka",
                            "Parka hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam.",
                        ),
                        (
                            "Black Thermal Sweater",
                            "Sweater thermal hitam memberikan kehangatan ekstra.",
                        ),
                        (
                            "Charcoal Gray Cargo Pants",
                            "Celana cargo abu-abu gelap memberikan tampilan yang kasual dan fungsional.",
                        ),
                        (
                            "Black Winter Boots",
                            "Sepatu bot musim dingin hitam memberikan kenyamanan dan kehangatan ekstra.",
                        ),
                    ],
                },
            },
        }

        # Return outfit recommendations based on the given clothing type, seasonal color, and skin tone
        return (
            recommendations.get(clothing_type, {})
            .get(seasonal_color, {})
            .get(skin_tone, [])
        )


# Kelas utama aplikasi Flask untuk menjalankan API prediksi
class ColorAnalysisApp:
    def __init__(self):
        """
        Konstruktor untuk aplikasi Flask. Menyiapkan aplikasi dan memuat model yang diperlukan.
        """

        load_dotenv()

        self.app = Flask(__name__)  # Membuat aplikasi Flask
        self.model_analyzer = ModelAnalyzer(
            seasonal_model_path="models/seasonal_color_model_improved.h5",
            skintone_model_path="models/skintone_model.h5",
        )

        self.RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
        self.RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")
        self.RAPIDAPI_URL = os.getenv("RAPIDAPI_URL")

        # Setup error handlers untuk HTTP error codes
        self.setup_error_handlers()

        try:
            # Memuat model saat aplikasi diinisialisasi
            self.model_analyzer.load_models()
        except ModelLoadError as e:
            logger.critical(f"Gagal memuat model: {e}")
            raise

        self.setup_routes()  # Menyiapkan endpoint API

    def setup_error_handlers(self):
        """
        Mengonfigurasi error handler untuk berbagai jenis kesalahan HTTP.
        """

        @self.app.errorhandler(400)
        def bad_request(error):
            return (
                jsonify({"error": "Bad Request", "message": "Permintaan tidak valid"}),
                400,
            )

        @self.app.errorhandler(404)
        def not_found(error):
            return (
                jsonify(
                    {"error": "Not Found", "message": "Sumber daya tidak ditemukan"}
                ),
                404,
            )

        @self.app.errorhandler(500)
        def internal_error(error):
            return (
                jsonify(
                    {
                        "error": "Internal Server Error",
                        "message": "Terjadi kesalahan internal pada server",
                    }
                ),
                500,
            )

    def search_amazon_products(self, query, page_size=3):
        """
        Mencari produk di Amazon menggunakan API dengan query yang diberikan dan mengembalikan sejumlah produk teratas.
        """
        querystring = {
            "query": query,
            "page": "1",  # Ambil halaman pertama, bisa menambah paginasi jika diperlukan
            "country": "US",
            "sort_by": "RELEVANCE",
            "product_condition": "ALL",
            "is_prime": "false",  # Menyesuaikan jika Anda ingin produk Prime atau tidak
        }

        headers = {
            "x-rapidapi-key": self.RAPIDAPI_KEY,
            "x-rapidapi-host": self.RAPIDAPI_HOST,
        }

        try:
            # Mengirim permintaan GET ke API Amazon
            response = requests.get(
                self.RAPIDAPI_URL, headers=headers, params=querystring
            )

            # Memeriksa jika ada rate-limiting (kode status 429)
            if response.status_code == 429:
                logger.warning(
                    f"Rate limit hit for query: {query}. Retrying after 5 seconds."
                )
                time.sleep(5)  # Menunggu 5 detik sebelum mencoba ulang
                response = requests.get(
                    self.RAPIDAPI_URL, headers=headers, params=querystring
                )

            # Memeriksa jika terjadi error 403 (forbidden)
            if response.status_code == 403:
                logger.error(
                    f"Forbidden error for query: {query}. Check your API key or access permissions."
                )
                return []

            # Memastikan respons berhasil (status code 200)
            response.raise_for_status()

            # Menangani respons JSON
            data = response.json()

            # Log the full Amazon API response for debugging
            logger.info(f"Full Amazon API response for query '{query}': {data}")

            # Mengekstrak produk dari hasil yang diterima
            products = []
            items = data.get("data", {}).get("products", [])

            # Jika tidak ada produk ditemukan, beri peringatan
            if not items:
                logger.warning(
                    f"No products found in Amazon response for query: {query}"
                )
            else:
                logger.info(f"Found {len(items)} items for query: {query}")

            # Ambil hanya 3 produk pertama dari daftar hasil
            for item in items[:page_size]:
                product = {
                    "asin": item.get("asin"),
                    "title": item.get("product_title"),
                    "price": item.get(
                        "product_price", "Not Available"
                    ),  # Menambahkan fallback jika harga tidak ada
                    "pic": item.get("product_photo", ""),
                    "detail_url": item.get("product_url", ""),
                    "sales_volume": item.get(
                        "sales_volume", "Not Available"
                    ),  # Menambahkan fallback jika sales_volume tidak ada
                    "is_prime": item.get("is_prime", False),
                    "delivery": item.get("delivery", "Not specified"),
                }

                # Log each product for debugging purposes
                logger.info(f"Product found: {product['title']} - {product['price']}")

                # Menambahkan produk ke dalam daftar produk
                products.append(product)

            # Log jumlah produk yang berhasil ditemukan
            logger.info(f"Returning {len(products)} products for query: {query}")

            # Mengembalikan daftar produk (max 3 produk)
            return products

        except requests.RequestException as e:
            # Menangani error saat permintaan ke API
            logger.error(f"Amazon API error for query '{query}': {e}")
            return []

    def setup_routes(self):
        """
        Menyiapkan rute untuk aplikasi web (endpoint).
        """

        @self.app.route("/predict_color_palette", methods=["POST"])
        def predict_color_palette():
            """
            Rute API untuk menerima gambar dan mengembalikan prediksi warna musiman dan kulit.
            """
            try:
                # Validasi unggahan gambar
                if "image" not in request.files:
                    return (
                        jsonify(
                            {
                                "error": "Tidak ada gambar diunggah",
                                "details": "Pastikan Anda mengunggah file gambar",
                            }
                        ),
                        400,
                    )

                image_file = request.files["image"].read()

                # Prediksi warna berdasarkan gambar yang diunggah
                try:
                    prediction_result = self.model_analyzer.predict(image_file)
                    return jsonify(prediction_result), 200
                except ImageProcessingError as img_error:
                    return (
                        jsonify(
                            {
                                "error": "Kesalahan Pemrosesan Gambar",
                                "details": str(img_error),
                            }
                        ),
                        422,
                    )

            except Exception as e:
                logger.error(f"Kesalahan prediksi: {e}")
                logger.error(traceback.format_exc())
                return jsonify({"error": "Prediksi Gagal", "details": str(e)}), 500

        @self.app.route("/model_details", methods=["GET"])
        def model_details():
            """
            Rute API untuk mengambil detail tentang model yang digunakan.
            """
            try:
                # Mengambil detail model yang digunakan
                return (
                    jsonify(
                        {
                            "seasonal_model": {
                                "path": self.model_analyzer.seasonal_model_path,
                                "input_shape": self.model_analyzer.seasonal_model.input_shape,
                                "output_shape": self.model_analyzer.seasonal_model.output_shape,
                            },
                            "skintone_model": {
                                "path": self.model_analyzer.skintone_model_path,
                                "input_shape": self.model_analyzer.skintone_model.input_shape,
                                "output_shape": self.model_analyzer.skintone_model.output_shape,
                            },
                        }
                    ),
                    200,
                )
            except Exception as e:
                return (
                    jsonify(
                        {"error": "Gagal mengambil detail model", "details": str(e)}
                    ),
                    500,
                )

        @self.app.route("/style_recommendation", methods=["POST"])
        def style_recommendation():
            try:
                if "image" not in request.files:
                    return (
                        jsonify(
                            {
                                "error": "No image uploaded",
                                "details": "Make sure you upload an image file.",
                            }
                        ),
                        400,
                    )

                image_file = request.files["image"].read()

                # Default to 'streetwear' if not provided
                clothing_type = request.form.get("clothing_type", "streetwear").lower()

                # Validate clothing type
                valid_clothing_types = ["formal", "wedding", "streetwear", "pajamas"]
                if clothing_type not in valid_clothing_types:
                    clothing_type = "streetwear"  # Default if invalid type provided

                try:
                    # Predict color and style
                    color_prediction = self.model_analyzer.predict(image_file)

                    # Get outfit recommendations
                    outfit_recommendations = self.model_analyzer.predict_outfit(
                        color_prediction["seasonal_color_label"],
                        color_prediction["skin_tone_label"],
                        clothing_type,
                    )

                    # Initialize amazon_products as an empty list
                    amazon_products = []
                    for item in outfit_recommendations:
                        # Log each item being searched on Amazon
                        logger.info(f"Searching for Amazon products with query: {item}")
                        products = self.search_amazon_products(
                            item, page_size=3
                        )  # Get only 3 products
                        # Log the results
                        logger.info(f"Found {len(products)} products for query: {item}")

                        # If products are found, add them to the amazon_products list
                        if products:
                            amazon_products.extend(products)

                    # If no products found, log it and return an empty list
                    if not amazon_products:
                        logger.warning(
                            "No Amazon products found for any of the recommendations."
                        )

                    # Log the final list of products being returned
                    logger.info(f"Returning {len(amazon_products)} products.")

                    # Ensure only 3 products are returned
                    amazon_products = amazon_products[
                        :3
                    ]  # Limit to the first 3 products

                    return (
                        jsonify(
                            {
                                **color_prediction,
                                "outfit_recommendations": outfit_recommendations,
                                "amazon_products": amazon_products,
                            }
                        ),
                        200,
                    )

                except Exception as predict_error:
                    logger.error(f"Prediction error: {predict_error}")
                    return (
                        jsonify(
                            {
                                "error": "Prediction failed",
                                "details": str(predict_error),
                            }
                        ),
                        500,
                    )

            except Exception as e:
                logger.error(f"Error during style recommendation: {e}")
                return (
                    jsonify(
                        {"error": "Style recommendation failed", "details": str(e)}
                    ),
                    500,
                )

        # get semua data
        @self.app.route("/get_all_data", methods=["GET"])
        def get_all_data():
            try:
                # Ambil semua dokumen dari koleksi 'users'
                data = ref.get()
                return jsonify(data), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # get dokument berdasarkan ID
        # @self.app.route('/get_data/<document_id>', methods=['GET'])
        # def get_data(document_id):
        #         try:

        #             doc = db.collection('users').document(document_id).get()
        #             if doc.exists:
        #                 return jsonify(doc.to_dict()), 200
        #             else:
        #                 return jsonify({"error": "Document not found"}), 404

        #         except Exception as e:
        #             return jsonify({"error": str(e)}), 500

        # add data to Realtime database
        @self.app.route("/add_data", methods=["POST"])
        def add_data():
            try:
                data = request.json
                if not data:
                    return jsonify({"error": "No data provided"}), 400
                # Menambahkan data ke Realtime Database
                ref.push(data)
                return jsonify({"success add data": True}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # add data to Realtime database user
        @self.app.route("/add_data_user", methods=["POST"])
        def add_data_user():
            try:
                data = request.json
                if not data:
                    return jsonify({"error": "No data provided"}), 400
                # Menambahkan data ke Realtime Database
                ref.child("users").push(data)
                return jsonify({"success add data user": True}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # delete data berdasarkan id
        @self.app.route("/delete_data/<data_id>", methods=["DELETE"])
        def delete_data(data_id):
            try:
                # Hapus data berdasarkan ID di kolom users
                ref.child("users").child(data_id).delete()
                return jsonify({"success": True, "message": "Data deleted"}), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500

    def run(self, debug=True, host="0.0.0.0", port=5000):
        """
        Menjalankan aplikasi Flask di server lokal.
        """
        self.app.run(debug=debug, host=host, port=port)


# Menjalankan aplikasi ketika file dijalankan langsung
if __name__ == "__main__":
    try:
        color_analysis_app = ColorAnalysisApp()
        color_analysis_app.run()
    except Exception as startup_error:
        logger.critical(f"Gagal menjalankan aplikasi: {startup_error}")
        print(f"Startup Error: {startup_error}")
