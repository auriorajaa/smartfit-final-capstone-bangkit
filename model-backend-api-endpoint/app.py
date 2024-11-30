from dotenv import load_dotenv
import os
import numpy as np
import tensorflow as tf
import requests  # Add this import
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from flask import Flask, request, jsonify
from PIL import Image, UnidentifiedImageError
import io
import logging
import traceback
import colorsys
import time
from datetime import datetime

# Add Firebase imports
import firebase_admin
from firebase_admin import credentials, db

logger = logging.getLogger(__name__)  # Membuat logger untuk aplikasi, digunakan di seluruh kode

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

        self.color_palettes = {
            "Summer": {
                "light_colors": [
                    "#B0E0E6",  # Powder Blue
                    "#98FB98",  # Pale Green
                    "#FFF0F5",  # Lavender Blush
                    "#E6E6FA",  # Lavender
                    "#87CEFA"   # Light Sky Blue
                ],
                "dark_colors": [
                    "#4682B4",  # Steel Blue
                    "#008B8B",  # Dark Cyan
                    "#483D8B",  # Dark Slate Blue
                    "#2F4F4F",  # Dark Slate Gray
                    "#00CED1"   # Dark Turquoise
                ]
            },
            "Winter": {
                "light_colors": [
                    "#F0F8FF",  # Alice Blue
                    "#E6E6FA",  # Lavender
                    "#F0FFFF",  # Azure
                    "#F5F5F5",  # White Smoke
                    "#FFFFFF"   # White
                ],
                "dark_colors": [
                    "#000080",  # Navy Blue
                    "#191970",  # Midnight Blue
                    "#000000",  # Black
                    "#2C3E50",  # Dark Blue Gray
                    "#1A1A1A"   # Very Dark Gray
                ]
            },
            "Spring": {
                "light_colors": [
                    "#98FB98",  # Pale Green
                    "#F0FFF0",  # Honeydew
                    "#E0FFFF",  # Light Cyan
                    "#FFB6C1",  # Light Pink
                    "#F0E68C"   # Khaki
                ],
                "dark_colors": [
                    "#228B22",  # Forest Green
                    "#006400",  # Dark Green
                    "#8B4513",  # Saddle Brown
                    "#4B0082",  # Indigo
                    "#556B2F"   # Dark Olive Green
                ]
            },
            "Autumn": {
                "light_colors": [
                    "#DEB887",  # Burlywood
                    "#D2B48C",  # Tan
                    "#F4A460",  # Sandy Brown
                    "#FFE4B5",  # Moccasin
                    "#FFDAB9"   # Peach Puff
                ],
                "dark_colors": [
                    "#8B0000",  # Dark Red
                    "#A0522D",  # Sienna
                    "#CD853F",  # Peru
                    "#6B4423",  # Dark Brown
                    "#800000"   # Maroon
                ]
            }
        }

    def load_models(self):
        """
        Memuat model dari file. Jika model gagal dimuat, exception akan dilemparkan.

        Menangani kesalahan yang mungkin terjadi saat memuat model, seperti FileNotFoundError,
        kesalahan I/O, atau masalah dengan TensorFlow.
        """
        try:
            # Memeriksa apakah path model ada dan file dapat diakses
            if not os.path.exists(self.seasonal_model_path):
                raise FileNotFoundError(f"Model warna musiman tidak ditemukan di {self.seasonal_model_path}")
            
            if not os.path.exists(self.skintone_model_path):
                raise FileNotFoundError(f"Model warna kulit tidak ditemukan di {self.skintone_model_path}")

            # Memuat model TensorFlow
            self.seasonal_model = load_model(self.seasonal_model_path)
            logger.info(f"Model warna musiman berhasil dimuat dari {self.seasonal_model_path}")

            self.skintone_model = load_model(self.skintone_model_path)
            logger.info(f"Model warna kulit berhasil dimuat dari {self.skintone_model_path}")

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
            "Light": "#F0D2B6",    # Peach Muda
            "Medium": "#C19A6B",   # Camel
            "Dark": "#6B4423",     # Coklat Gelap
            "Unknown": "#FFFFFF"   # Putih sebagai default
        }
        return skin_tone_hex_map.get(skin_tone_label, "#FFFFFF")  # Mengembalikan default '#FFFFFF' jika tidak ada kecocokan

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
                raise ImageProcessingError(f"Gambar terlalu kecil. Ukuran minimal {min_size}x{min_size} piksel.")
            
            if width > max_size or height > max_size:
                raise ImageProcessingError(f"Gambar terlalu besar. Ukuran maksimal {max_size}x{max_size} piksel.")
            
            # Memastikan gambar berada dalam mode RGB atau RGBA
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            return img
        
        except UnidentifiedImageError:
            # Menangani kesalahan jika gambar tidak dapat dikenali
            raise ImageProcessingError("Format gambar tidak dikenal atau rusak.")
        except IOError:
            # Menangani kesalahan jika gambar gagal dibuka
            raise ImageProcessingError("Gagal membuka gambar. Pastikan file gambar valid.")

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
        resize_strategies = [(224, 224), (128, 128), (256, 256)]  # Daftar ukuran yang dicoba untuk resizing
        
        try:
            # Validasi gambar terlebih dahulu
            img = self.validate_image(image_file)
            
            for size in resize_strategies:
                try:
                    # Resize gambar ke ukuran yang ditentukan
                    img_resized = img.resize(size)
                    
                    # Mengubah gambar ke array NumPy dan menormalkan nilai pixel
                    img_array = img_to_array(img_resized) / 255.0
                    img_array = np.expand_dims(img_array, axis=0)  # Menambah dimensi untuk batch

                    # Menyimpan gambar yang sudah diproses
                    processed_images.append((img_array, size))
                
                except Exception as resize_error:
                    # Log kesalahan jika resizing gagal pada ukuran tertentu
                    logger.warning(f"Preprocessing gagal untuk ukuran {size}: {resize_error}")
            
            # Jika tidak ada gambar yang berhasil diproses, naikkan kesalahan
            if not processed_images:
                raise ImageProcessingError("Tidak dapat memproses gambar dengan strategi yang tersedia.")
            
            return processed_images
        
        except ImageProcessingError as img_error:
            logger.error(f"Kesalahan pemrosesan gambar: {img_error}")
            raise

    def predict(self, image_file, outfit_type='casual'):
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
                    seasonal_color_label = ["Winter", "Spring", "Summer", "Autumn"][seasonal_label]
                    skin_tone_label = ["Light", "Medium", "Dark"][skintone_label]
                    skin_tone_hex = self.get_skin_tone_hex(skin_tone_label)

                    # Menyusun hasil prediksi dalam format JSON
                    return {
                        "seasonal_color_label": seasonal_color_label,
                        "seasonal_probability": seasonal_probability,
                        "skin_tone_label": skin_tone_label,
                        "skin_tone_probability": skintone_probability,
                        "skin_tone_hex": skin_tone_hex
                    }
                
                except Exception as prediction_error:
                    logger.warning(f"Prediksi gagal untuk ukuran {size}: {prediction_error}")
            
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
                        ("Formal Light Blue Blazer", "Blazer biru muda ini menciptakan kesan segar dan cerah, cocok dengan warna kulit terang."),
                        ("White Dress Shirt Men", "Baju putih netral yang sangat cocok dengan warna kulit terang, memberikan kesan bersih dan profesional."),
                        ("Light Gray Tailored Trousers","Celana abu-abu muda melengkapi warna kulit terang Anda dengan kesan yang ringan dan bersih."),
                    ],
                    "Medium": [
                        ("Navy Blue Professional Suit", "Setelan biru navy ini memberi kesan profesional dan percaya diri, cocok untuk kulit medium."),
                        ("Lavender Dress Shirt Men", "Baju lavender memberi sentuhan unik dan segar pada penampilan formal Anda."),
                        ("Charcoal Gray Blazer","Blazer abu-abu gelap memberikan kontras elegan dengan kulit medium."),
                    ],
                    "Dark": [
                        ("Dark Turquoise Blazer", "Blazer biru kehijauan gelap cocok untuk kulit gelap dengan kesan yang lebih tajam dan modern."),
                        ("Pale Green Dress Shirt", "Baju hijau pucat memberikan nuansa segar yang cocok dengan warna kulit gelap."),
                        ("Beige Dress Trousers","Celana krem memberikan tampilan yang tenang namun tetap profesional."),
                    ],
                },
                "Spring": {
                    "Light": [
                        ("Soft Yellow Blazer","Blazer kuning lembut ini memberikan kesan ceria dan hangat, cocok dengan warna kulit terang."),
                        ("Light Pink Dress Shirt","Baju pink muda memberi kesan segar dan lembut."),
                        ("Light Brown Chinos","Celana chinos cokelat muda memberikan tampilan yang lebih ringan namun tetap profesional."),
                    ],
                    "Medium": [
                        ("Pale Blue Blazer","Blazer biru pucat memberi tampilan profesional namun santai, cocok untuk kulit medium."),
                        ("Off-White Dress Shirt","Baju putih krem memberikan tampilan cerah dan bersih."),
                        ("Beige Tailored Trousers","Celana krem memberikan nuansa elegan namun tidak berlebihan."),
                    ],
                    "Dark": [
                        ("Forest Green Blazer","Blazer hijau tua ini memberi kesan kuat dan elegan, cocok dengan kulit gelap."),
                        ("Charcoal Gray Shirt","Baju abu-abu gelap memberikan kontras yang elegan."),
                        ("Olive Green Trousers","Celana hijau zaitun memberi kesan berani namun tetap santai."),
                    ],
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Blazer", "Blazer oranye terbakar ini memberikan kesan hangat dan menenangkan, cocok untuk kulit terang."),
                        ("Light Tan Dress Shirt", "Baju tan lembut memberikan sentuhan elegan dan alami."),
                        ("Khaki Trousers", "Celana khaki memberi tampilan santai namun tetap rapi."),
                    ],
                    "Medium": [
                        ("Olive Green Blazer", "Blazer hijau zaitun memberikan kesan profesional dan hangat, cocok dengan kulit medium."),
                        ("Deep Red Dress Shirt", "Baju merah tua memberi kesan percaya diri dan berkelas."),
                        ("Dark Brown Tailored Trousers", "Celana coklat tua memberikan tampilan yang berkelas dan tegas."),
                    ],
                    "Dark": [
                        ("Maroon Blazer", "Blazer marun ini memberi kesan kaya dan elegan, cocok untuk kulit gelap."),
                        ("Dark Brown Shirt", "Baju coklat tua memberi kesan tegas dan berkelas."),
                        ("Dark Green Trousers", "Celana hijau gelap memberi tampilan solid dan terstruktur."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Gray Blazer", "Blazer abu-abu terang cocok dengan kulit terang, memberikan kesan profesional dan bersih."),
                        ("White Dress Shirt", "Baju putih memberikan kesan netral yang sangat cocok dengan warna kulit terang."),
                        ("Charcoal Gray Chinos", "Celana chinos abu-abu gelap memberi tampilan yang profesional dan elegan."),
                    ],
                    "Medium": [
                        ("Navy Blue Suit", "Setelan biru navy memberi kesan formal dan berkelas, sangat cocok dengan kulit medium."),
                        ("Light Blue Dress Shirt", "Baju biru muda memberi kesan segar dan menenangkan."),
                        ("Gray Wool Trousers", "Celana wol abu-abu memberikan kesan terstruktur dan profesional."),
                    ],
                    "Dark": [
                        ("Midnight Blue Blazer", "Blazer biru gelap memberi kesan formal dan berkelas, sangat cocok untuk kulit gelap."),
                        ("Black Dress Shirt", "Baju hitam memberi kesan tajam dan profesional."),
                        ("Black Tailored Trousers", "Celana hitam memberi kesan solid dan sangat elegan."),
                    ]
                }
            },
            "formal-women": {
                "Summer": {
                    "Light": [
                        ("Pastel Pink Blazer", "Blazer pink pastel ini memberikan kesan segar dan ceria, cocok untuk warna kulit putih."),
                        ("White Silk Blouse", "Blus sutra putih memberi kesan elegan dan ringan, sempurna untuk musim panas."),
                        ("Beige Pencil Skirt", "Rok pensil beige melengkapi warna kulit putih dengan sentuhan yang lembut dan profesional."),
                    ],
                    "Medium": [
                        ("Coral Blazer", "Blazer coral ini memberikan kesan hangat dan ceria, cocok untuk kulit coklat atau sawo matang."),
                        ("Light Blue Dress Shirt", "Baju biru muda memberikan kontras yang menyegarkan dengan kulit medium."),
                        ("White Tailored Trousers", "Celana putih memberikan tampilan yang bersih dan elegan."),
                    ],
                    "Dark": [
                        ("Bright Yellow Blazer", "Blazer kuning cerah ini memberi kesan energik dan modern, cocok untuk kulit hitam."),
                        ("Cream Silk Shirt", "Baju sutra krem memberikan kontras yang anggun dan elegan."),
                        ("Navy Blue Dress Trousers", "Celana biru navy memberikan tampilan yang profesional dan solid."),
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Soft Lavender Blazer", "Blazer lavender lembut ini memberikan kesan segar dan feminin, cocok dengan warna kulit putih."),
                        ("Light Green Dress Shirt", "Baju hijau muda memberikan tampilan yang ceria dan natural."),
                        ("Light Brown Chinos", "Celana chinos cokelat muda memberikan tampilan yang santai namun tetap elegan."),
                    ],
                    "Medium": [
                        ("Sky Blue Blazer", "Blazer biru langit memberikan tampilan yang cerah dan profesional, cocok untuk kulit medium."),
                        ("White Cotton Blouse", "Blus katun putih memberikan tampilan yang ringan dan nyaman."),
                        ("Khaki Tailored Trousers", "Celana khaki memberikan kesan elegan namun tetap santai."),
                    ],
                    "Dark": [
                        ("Emerald Green Blazer", "Blazer hijau zamrud ini memberikan tampilan yang kuat dan elegan, cocok dengan kulit hitam."),
                        ("Black Silk Shirt", "Baju sutra hitam memberikan kesan anggun dan profesional."),
                        ("Charcoal Gray Dress Trousers", "Celana abu-abu gelap memberikan tampilan yang solid dan terstruktur."),
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Blazer", "Blazer oranye terbakar ini memberikan kesan hangat dan menenangkan, cocok untuk warna kulit putih."),
                        ("Cream Wool Sweater", "Sweter wol krem memberikan kesan hangat dan nyaman."),
                        ("Brown Tailored Skirt", "Rok cokelat memberikan tampilan yang rapi dan profesional."),
                    ],
                    "Medium": [
                        ("Olive Green Blazer", "Blazer hijau zaitun memberikan kesan hangat dan profesional, cocok untuk kulit coklat atau sawo matang."),
                        ("Dark Red Dress Shirt", "Baju merah tua memberikan kesan percaya diri dan elegan."),
                        ("Brown Wool Trousers", "Celana wol cokelat memberikan tampilan yang terstruktur dan profesional."),
                    ],
                    "Dark": [
                        ("Burgundy Blazer", "Blazer merah marun ini memberikan kesan kaya dan elegan, cocok untuk kulit hitam."),
                        ("Dark Brown Silk Blouse", "Blus sutra cokelat tua memberikan tampilan yang anggun dan berkelas."),
                        ("Black Dress Trousers", "Celana hitam memberikan tampilan yang solid dan profesional."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Blue Blazer", "Blazer biru muda memberikan kesan profesional dan bersih, cocok untuk kulit putih."),
                        ("White Wool Sweater", "Sweter wol putih memberikan kesan hangat dan elegan."),
                        ("Gray Tailored Trousers", "Celana abu-abu memberikan tampilan yang solid dan rapi."),
                    ],
                    "Medium": [
                        ("Navy Blue Blazer", "Blazer biru navy memberikan kesan formal dan berkelas, sangat cocok dengan kulit medium."),
                        ("Light Gray Dress Shirt", "Baju abu-abu muda memberikan kesan segar dan menenangkan."),
                        ("Black Wool Trousers", "Celana wol hitam memberikan kesan terstruktur dan profesional."),
                    ],
                    "Dark": [
                        ("Dark Purple Blazer", "Blazer ungu tua memberikan kesan berkelas dan elegan, cocok untuk kulit hitam."),
                        ("Black Wool Sweater", "Sweter wol hitam memberikan tampilan yang anggun dan nyaman."),
                        ("Charcoal Gray Tailored Trousers", "Celana abu-abu gelap memberikan kesan solid dan terstruktur."),
                    ]
                }
            },
            "wedding-men": {
                "Summer": {
                    "Light": [
                        ("Light Gray Suit", "Setelan abu-abu terang ini memberikan kesan elegan dan sejuk, cocok untuk warna kulit putih."),
                        ("Sky Blue Dress Shirt", "Baju biru langit memberikan tampilan yang segar dan cerah."),
                        ("Tan Leather Shoes", "Sepatu kulit tan memberikan kesan hangat dan menambah elegan pada penampilan Anda.")
                    ],
                    "Medium": [
                        ("Navy Blue Suit", "Setelan biru navy memberikan kesan profesional dan berkelas, sangat cocok dengan kulit coklat atau sawo matang."),
                        ("Lavender Dress Shirt", "Baju lavender memberikan sentuhan warna yang menenangkan dan elegan."),
                        ("Black Leather Shoes", "Sepatu kulit hitam memberikan tampilan yang rapi dan klasik.")
                    ],
                    "Dark": [
                        ("Ivory Suit", "Setelan ivory memberikan kesan elegan dan kontras yang indah, cocok untuk kulit hitam."),
                        ("Mint Green Dress Shirt", "Baju hijau mint memberikan kesan segar dan menonjol."),
                        ("Brown Leather Shoes", "Sepatu kulit coklat memberikan tampilan yang klasik dan elegan.")
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Beige Suit", "Setelan beige memberikan kesan hangat dan cerah, cocok untuk warna kulit putih."),
                        ("Light Pink Dress Shirt", "Baju pink muda memberikan tampilan yang lembut dan romantis."),
                        ("Light Blue Silk Tie", "Dasi sutra biru muda memberikan aksen yang segar dan elegan."),
                    ],
                    "Medium": [
                        ("Light Gray Suit", "Setelan abu-abu terang memberikan kesan cerah dan elegan, cocok untuk kulit coklat atau sawo matang."),
                        ("White Dress Shirt", "Baju putih memberikan tampilan yang bersih dan profesional."),
                        ("Black Leather Shoes", "Sepatu kulit hitam memberikan tampilan yang klasik dan rapi.")
                    ],
                    "Dark": [
                        ("Light Blue Suit", "Setelan biru muda memberikan kesan cerah dan elegan, cocok untuk kulit hitam."),
                        ("Cream Dress Shirt", "Baju krem memberikan kontras yang lembut dan anggun."),
                        ("Tan Leather Shoes", "Sepatu kulit tan memberikan kesan hangat dan elegan.")
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Olive Green Suit", "Setelan hijau zaitun memberikan kesan hangat dan alami, cocok untuk warna kulit putih."),
                        ("Cream Dress Shirt", "Baju krem memberikan tampilan yang lembut dan elegan."),
                        ("Brown Leather Shoes", "Sepatu kulit coklat memberikan tampilan yang klasik dan hangat.")
                    ],
                    "Medium": [
                        ("Brown Suit", "Setelan coklat memberikan kesan hangat dan elegan, cocok untuk kulit coklat atau sawo matang."),
                        ("Light Blue Dress Shirt", "Baju biru muda memberikan kontras yang segar dan menonjol."),
                        ("Black Leather Shoes", "Sepatu kulit hitam memberikan tampilan yang klasik dan profesional.")
                    ],
                    "Dark": [
                        ("Dark Green Suit", "Setelan hijau tua memberikan kesan kuat dan elegan, cocok untuk kulit hitam."),
                        ("White Dress Shirt", "Baju putih memberikan kontras yang tajam dan elegan."),
                        ("Brown Leather Belt", "Sabuk kulit coklat memberikan tampilan yang alami dan berkelas.")
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Charcoal Gray Suit", "Setelan abu-abu arang memberikan kesan profesional dan tajam, cocok untuk warna kulit putih."),
                        ("White Dress Shirt", "Baju putih memberikan tampilan yang bersih dan klasik."),
                        ("Black Leather Shoes", "Sepatu kulit hitam memberikan tampilan yang klasik dan berkelas.")
                    ],
                    "Medium": [
                        ("Black Suit", "Setelan hitam memberikan kesan formal dan berkelas, sangat cocok dengan kulit coklat atau sawo matang."),
                        ("Gray Dress Shirt", "Baju abu-abu memberikan kontras yang elegan."),
                        ("Silver Tie", "Dasi perak memberikan aksen yang berkelas dan mewah."),
                    ],
                    "Dark": [
                        ("Dark Blue Suit", "Setelan biru tua memberikan kesan formal dan tajam, cocok untuk kulit hitam."),
                        ("White Dress Shirt", "Baju putih memberikan kontras yang anggun dan elegan."),
                        ("Black Leather Shoes", "Sepatu kulit hitam memberikan tampilan yang klasik dan berkelas.")
                    ]
                }
            },
            "wedding-women": {
                "Summer": {
                    "Light": [
                        ("Pastel Pink Dress", "Gaun pink pastel ini memberikan kesan lembut dan romantis, cocok untuk warna kulit putih."),
                        ("White Lace Shawl", "Selendang renda putih memberikan sentuhan elegan pada tampilan musim panas."),
                        ("Beige Heels", "Sepatu hak tinggi beige memberikan tampilan yang ringan dan elegan."),
                    ],
                    "Medium": [
                        ("Coral Dress", "Gaun coral ini memberikan kesan ceria dan elegan, cocok untuk kulit coklat atau sawo matang."),
                        ("Light Blue Silk Shawl", "Selendang sutra biru muda memberikan aksen yang menyegarkan."),
                        ("White Heels", "Sepatu hak tinggi putih memberikan tampilan yang bersih dan elegan."),
                    ],
                    "Dark": [
                        ("Bright Yellow Dress", "Gaun kuning cerah ini memberikan kesan energik dan modern, cocok untuk kulit hitam."),
                        ("Cream Silk Shawl", "Selendang sutra krem memberikan kontras yang anggun dan elegan."),
                        ("Navy Blue Heels", "Sepatu hak tinggi biru navy memberikan tampilan yang profesional dan solid."),
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Soft Lavender Dress", "Gaun lavender lembut ini memberikan kesan feminin dan segar, cocok untuk warna kulit putih."),
                        ("Light Green Scarf", "Syal hijau muda memberikan sentuhan warna yang cerah."),
                        ("Light Brown Sandals", "Sandal cokelat muda memberikan tampilan yang santai namun tetap elegan."),
                    ],
                    "Medium": [
                        ("Sky Blue Dress", "Gaun biru langit memberikan tampilan yang cerah dan profesional, cocok untuk kulit medium."),
                        ("White Cotton Scarf", "Syal katun putih memberikan tampilan yang ringan dan nyaman."),
                        ("Khaki Sandals", "Sandal khaki memberikan nuansa elegan namun tetap santai."),
                    ],
                    "Dark": [
                        ("Emerald Green Dress", "Gaun hijau zamrud memberikan tampilan yang kuat dan elegan, cocok dengan kulit hitam."),
                        ("Black Silk Scarf", "Syal sutra hitam memberikan kesan anggun dan profesional."),
                        ("Charcoal Gray Heels", "Sepatu hak tinggi abu-abu gelap memberikan tampilan yang solid dan terstruktur."),
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Dress", "Gaun oranye terbakar memberikan kesan hangat dan menenangkan, cocok untuk warna kulit putih."),
                        ("Cream Wool Shawl", "Selendang wol krem memberikan kesan hangat dan nyaman."),
                        ("Brown Heels", "Sepatu hak tinggi cokelat memberikan tampilan yang klasik dan elegan."),
                    ],
                    "Medium": [
                        ("Olive Green Dress", "Gaun hijau zaitun memberikan kesan hangat dan profesional, cocok untuk kulit coklat atau sawo matang."),
                        ("Dark Red Scarf", "Syal merah tua memberikan kesan percaya diri dan berkelas."),
                        ("Brown Wool Trousers", "Celana wol cokelat memberikan tampilan yang terstruktur dan profesional."),
                    ],
                    "Dark": [
                        ("Burgundy Dress", "Gaun merah marun memberikan kesan kaya dan elegan, cocok untuk kulit hitam."),
                        ("Dark Brown Silk Scarf", "Syal sutra cokelat tua memberikan tampilan yang anggun dan berkelas."),
                        ("Black Heels", "Sepatu hak tinggi hitam memberikan tampilan yang solid dan profesional."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Blue Dress", "Gaun biru muda memberikan kesan profesional dan bersih, cocok untuk kulit putih."),
                        ("White Wool Scarf", "Syal wol putih memberikan kesan hangat dan elegan."),
                        ("Gray Heels", "Sepatu hak tinggi abu-abu memberikan tampilan yang solid dan rapi."),
                    ],
                    "Medium": [
                        ("Navy Blue Dress", "Gaun biru navy memberikan kesan formal dan berkelas, sangat cocok dengan kulit medium."),
                        ("Light Gray Scarf", "Syal abu-abu muda memberikan kesan segar dan menenangkan."),
                        ("Black Heels", "Sepatu hak tinggi hitam memberikan kesan terstruktur dan profesional."),
                    ],
                    "Dark": [
                        ("Dark Purple Dress", "Gaun ungu tua memberikan kesan berkelas dan elegan, cocok untuk kulit hitam."),
                        ("Black Wool Scarf", "Syal wol hitam memberikan tampilan yang anggun dan nyaman."),
                        ("Charcoal Gray Heels", "Sepatu hak tinggi abu-abu gelap memberikan kesan solid dan terstruktur."),
                    ]
                }
            },
            "streetwear-men": {
                "Summer": {
                    "Light": [
                        ("White Graphic Tee", "Kaos putih dengan desain grafis yang segar, cocok untuk warna kulit putih, memberikan tampilan yang cerah dan modern."),
                        ("Light Blue Denim Shorts", "Celana pendek denim biru muda memberikan kesan kasual dan nyaman."),
                        ("White Sneakers", "Sepatu sneakers putih memberikan tampilan yang bersih dan trendi."),
                    ],
                    "Medium": [
                        ("Black Graphic Tee", "Kaos hitam dengan desain grafis yang keren, cocok untuk kulit coklat atau sawo matang, memberikan kesan edgy dan modern."),
                        ("Gray Jogger Pants", "Celana jogger abu-abu memberikan kenyamanan dan gaya yang santai."),
                        ("Black High-top Sneakers", "Sepatu sneakers hitam memberikan tampilan yang tajam dan trendi."),
                    ],
                    "Dark": [
                        ("Red Hoodie men", "Hoodie merah memberikan kesan energik dan menonjol, cocok untuk kulit hitam."),
                        ("Dark Blue Denim Jeans", "Jeans denim biru gelap memberikan tampilan yang kasual dan solid."),
                        ("White High-top Sneakers", "Sepatu sneakers putih memberikan kontras yang cerah dan stylish."),
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Pastel Pink Hoodie", "Hoodie pink pastel memberikan tampilan yang lembut dan ceria, cocok untuk warna kulit putih."),
                        ("Light Gray Sweatpants", "Sweatpants abu-abu muda memberikan kenyamanan dan gaya kasual."),
                        ("White Low-top Sneakers", "Sepatu sneakers putih memberikan tampilan yang bersih dan trendi."),
                    ],
                    "Medium": [
                        ("Olive Green Cargo Pants", "Celana cargo hijau zaitun memberikan tampilan yang kasual dan fungsional, cocok untuk kulit medium."),
                        ("White Crewneck Sweatshirt", "Sweatshirt putih memberikan tampilan yang bersih dan nyaman."),
                        ("Black Skate Shoes", "Sepatu skate hitam memberikan tampilan yang edgy dan cool."),
                    ],
                    "Dark": [
                        ("Bright Orange Windbreaker", "Windbreaker oranye cerah memberikan kesan energik dan modern, cocok untuk kulit hitam."),
                        ("Black Jogger Pants", "Celana jogger hitam memberikan tampilan yang santai dan keren."),
                        ("Gray Sneakers", "Sepatu sneakers abu-abu memberikan kesan yang trendi dan nyaman."),
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Flannel Shirt", "Kemeja flanel oranye terbakar memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih."),
                        ("Dark Blue Ripped Jeans", "Jeans robek biru gelap memberikan tampilan yang kasual dan edgy."),
                        ("Brown Leather Boots", "Sepatu bot kulit coklat memberikan tampilan yang klasik dan maskulin."),
                    ],
                    "Medium": [
                        ("Maroon Bomber Jacket", "Jaket bomber marun memberikan kesan hangat dan stylish, cocok untuk kulit coklat atau sawo matang."),
                        ("Black Slim Fit Jeans", "Jeans slim fit hitam memberikan tampilan yang tajam dan modern."),
                        ("White Leather Sneakers", "Sepatu sneakers kulit putih memberikan kontras yang bersih dan trendi."),
                    ],
                    "Dark": [
                        ("Charcoal Gray Hoodie", "Hoodie abu-abu arang memberikan kesan kuat dan elegan, cocok untuk kulit hitam."),
                        ("Black Cargo Pants", "Celana cargo hitam memberikan tampilan yang kasual dan fungsional."),
                        ("Black Combat Boots", "Sepatu bot hitam memberikan tampilan yang solid dan maskulin."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Gray Puffer Jacket", "Jaket puffer abu-abu terang memberikan kesan hangat dan stylish, cocok untuk warna kulit putih."),
                        ("White Thermal Shirt", "Kaos thermal putih memberikan lapisan yang nyaman dan hangat."),
                        ("Black Skinny Jeans", "Jeans skinny hitam memberikan tampilan yang tajam dan modern."),
                    ],
                    "Medium": [
                        ("Navy Blue Peacoat", "Jaket peacoat biru navy memberikan kesan formal dan berkelas, sangat cocok dengan kulit medium."),
                        ("Gray Turtleneck Sweater", "Sweater turtleneck abu-abu memberikan tampilan yang hangat dan elegan."),
                        ("Black Chino Pants", "Celana chino hitam memberikan kesan terstruktur dan profesional."),
                    ],
                    "Dark": [
                        ("Dark Green Parka", "Jaket parka hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam."),
                        ("Black Thermal Shirt", "Kaos thermal hitam memberikan lapisan yang anggun dan hangat."),
                        ("Charcoal Gray Cargo Pants", "Celana cargo abu-abu gelap memberikan tampilan yang kasual dan fungsional."),
                    ]
                }
            },
            "streetwear-women": {
                "Summer": {
                    "Light": [
                        ("White Crop Top", "Atasan crop putih ini memberikan tampilan yang segar dan modern, cocok untuk warna kulit putih."),
                        ("Light Blue High-Waisted Shorts", "Celana pendek high-waisted biru muda memberikan kesan kasual dan stylish."),
                        ("White Sneakers", "Sepatu sneakers putih memberikan tampilan yang bersih dan trendi."),
                    ],
                    "Medium": [
                        ("Black Crop Top", "Atasan crop hitam ini memberikan tampilan yang edgy dan stylish, cocok untuk kulit coklat atau sawo matang."),
                        ("Olive Green Cargo Shorts", "Celana cargo hijau zaitun memberikan tampilan yang kasual dan fungsional."),
                        ("Black High-top Sneakers", "Sepatu sneakers hitam memberikan tampilan yang tajam dan trendi."),
                    ],
                    "Dark": [
                        ("Red Tank Top", "Tank top merah ini memberikan kesan energik dan modern, cocok untuk kulit hitam."),
                        ("Dark Blue Denim Shorts", "Celana pendek denim biru gelap memberikan tampilan yang kasual dan solid."),
                        ("White High-top Sneakers", "Sepatu sneakers putih memberikan kontras yang cerah dan stylish."),
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Pastel Pink Hoodie", "Hoodie pink pastel ini memberikan tampilan yang lembut dan ceria, cocok untuk warna kulit putih."),
                        ("Light Gray Sweatpants", "Sweatpants abu-abu muda memberikan kenyamanan dan gaya kasual."),
                        ("White Low-top Sneakers", "Sepatu sneakers putih memberikan tampilan yang bersih dan trendi."),
                    ],
                    "Medium": [
                        ("Olive Green Cargo Pants", "Celana cargo hijau zaitun memberikan tampilan yang kasual dan fungsional, cocok untuk kulit medium."),
                        ("White Crop Sweatshirt", "Sweatshirt crop putih memberikan tampilan yang bersih dan nyaman."),
                        ("Black Skate Shoes", "Sepatu skate hitam memberikan tampilan yang edgy dan cool."),
                    ],
                    "Dark": [
                        ("Bright Orange Windbreaker", "Windbreaker oranye cerah memberikan kesan energik dan modern, cocok untuk kulit hitam."),
                        ("Black Jogger Pants", "Celana jogger hitam memberikan tampilan yang santai dan keren."),
                        ("Gray Sneakers", "Sepatu sneakers abu-abu memberikan kesan yang trendi dan nyaman."),
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Flannel Shirt", "Kemeja flanel oranye terbakar memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih."),
                        ("Dark Blue Ripped Jeans", "Jeans robek biru gelap memberikan tampilan yang kasual dan edgy."),
                        ("Brown Leather Boots", "Sepatu bot kulit coklat memberikan tampilan yang klasik dan maskulin."),
                    ],
                    "Medium": [
                        ("Maroon Bomber Jacket", "Jaket bomber marun memberikan kesan hangat dan stylish, cocok untuk kulit coklat atau sawo matang."),
                        ("Black Skinny Jeans", "Jeans skinny hitam memberikan tampilan yang tajam dan modern."),
                        ("White Leather Sneakers", "Sepatu sneakers kulit putih memberikan kontras yang bersih dan trendi."),
                    ],
                    "Dark": [
                        ("Charcoal Gray Hoodie", "Hoodie abu-abu arang memberikan kesan kuat dan elegan, cocok untuk kulit hitam."),
                        ("Black Cargo Pants", "Celana cargo hitam memberikan tampilan yang kasual dan fungsional."),
                        ("Black Combat Boots", "Sepatu bot hitam memberikan tampilan yang solid dan maskulin."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Gray Puffer Jacket", "Jaket puffer abu-abu terang memberikan kesan hangat dan stylish, cocok untuk warna kulit putih."),
                        ("White Thermal Shirt", "Kaos thermal putih memberikan lapisan yang nyaman dan hangat."),
                        ("Black Skinny Jeans", "Jeans skinny hitam memberikan tampilan yang tajam dan modern."),
                    ],
                    "Medium": [
                        ("Navy Blue Peacoat", "Jaket peacoat biru navy memberikan kesan formal dan berkelas, sangat cocok dengan kulit medium."),
                        ("Gray Turtleneck Sweater", "Sweater turtleneck abu-abu memberikan tampilan yang hangat dan elegan."),
                        ("Black Chino Pants", "Celana chino hitam memberikan kesan terstruktur dan profesional."),
                    ],
                    "Dark": [
                        ("Dark Green Parka", "Jaket parka hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam."),
                        ("Black Thermal Shirt", "Kaos thermal hitam memberikan lapisan yang anggun dan hangat."),
                        ("Charcoal Gray Cargo Pants", "Celana cargo abu-abu gelap memberikan tampilan yang kasual dan fungsional."),
                    ]
                }
            },
            "pajamas-men": {
                "Summer": {
                    "Light": [
                        ("Light Blue Short-Sleeve Pajama Set Men", "Set piyama biru muda dengan lengan pendek ini sangat nyaman dan sejuk, cocok untuk warna kulit putih."),
                        ("White Cotton Sleep Shorts Men", "Celana tidur katun putih memberikan kesan yang bersih dan segar."),
                        ("Lightweight Slippers Men", "Sandal ringan memberikan kenyamanan dan kemudahan saat berjalan di rumah."),
                    ],
                    "Medium": [
                        ("Gray Tank Top and Shorts Pajama Set Men", "Set piyama abu-abu dengan tank top dan celana pendek ini sangat nyaman dan cocok untuk kulit coklat atau sawo matang."),
                        ("Navy Blue Sleep Shorts Men", "Celana tidur biru navy memberikan kontras yang menarik."),
                        ("Soft Cotton Slippers Men", "Sandal katun lembut memberikan kenyamanan ekstra."),
                    ],
                    "Dark": [
                        ("White Linen Pajama Set Men", "Set piyama linen putih memberikan tampilan yang sejuk dan cocok untuk kulit hitam."),
                        ("Dark Green Sleep Shorts Men", "Celana tidur hijau gelap memberikan tampilan yang elegan."),
                        ("Comfortable House Slippers Men", "Sandal rumah yang nyaman memberikan kemudahan dan kenyamanan."),
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Pastel Green Pajama Set Men", "Set piyama hijau pastel ini memberikan kesan segar dan cocok untuk warna kulit putih."),
                        ("Light Gray Sleep Pants Men", "Celana tidur abu-abu muda memberikan tampilan yang ringan dan nyaman."),
                        ("Soft Slip-On Slippers Men", "Sandal slip-on lembut memberikan kenyamanan saat berjalan di rumah."),
                    ],
                    "Medium": [
                        ("Blue Striped Pajama Set", "Set piyama dengan garis-garis biru memberikan tampilan yang cerah dan cocok untuk kulit medium."),
                        ("White Sleep Pants", "Celana tidur putih memberikan kesan yang bersih dan segar."),
                        ("Foam Slippers", "Sandal busa memberikan kenyamanan ekstra saat berjalan di rumah."),
                    ],
                    "Dark": [
                        ("Cream Pajama Set", "Set piyama krem memberikan tampilan yang anggun dan cocok untuk kulit hitam."),
                        ("Navy Blue Sleep Pants", "Celana tidur biru navy memberikan kontras yang menarik."),
                        ("Fleece Slippers", "Sandal fleece memberikan kenyamanan dan kehangatan ekstra."),
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Pajama Set", "Set piyama oranye terbakar ini memberikan kesan hangat dan cocok untuk warna kulit putih."),
                        ("Dark Brown Sleep Pants", "Celana tidur cokelat gelap memberikan tampilan yang hangat."),
                        ("Wool Slippers", "Sandal wol memberikan kenyamanan dan kehangatan saat musim gugur."),
                    ],
                    "Medium": [
                        ("Olive Green Pajama Set", "Set piyama hijau zaitun memberikan tampilan yang hangat dan cocok untuk kulit coklat atau sawo matang."),
                        ("Maroon Sleep Pants", "Celana tidur merah marun memberikan kontras yang elegan."),
                        ("Leather House Slippers", "Sandal rumah kulit memberikan tampilan yang berkelas dan nyaman."),
                    ],
                    "Dark": [
                        ("Dark Brown Pajama Set", "Set piyama cokelat gelap memberikan tampilan yang elegan dan cocok untuk kulit hitam."),
                        ("Charcoal Gray Sleep Pants", "Celana tidur abu-abu arang memberikan tampilan yang solid."),
                        ("Knitted Slippers", "Sandal rajut memberikan kenyamanan dan kehangatan ekstra."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Gray Flannel Pajama Set", "Set piyama flanel abu-abu terang ini memberikan kesan hangat dan cocok untuk warna kulit putih."),
                        ("White Thermal Pants", "Celana thermal putih memberikan kehangatan ekstra."),
                        ("Fur-Lined Slippers", "Sandal berlapis bulu memberikan kenyamanan dan kehangatan ekstra."),
                    ],
                    "Medium": [
                        ("Navy Blue Flannel Pajama Set", "Set piyama flanel biru navy ini memberikan kesan hangat dan cocok untuk kulit medium."),
                        ("Gray Thermal Pants", "Celana thermal abu-abu memberikan kehangatan ekstra."),
                        ("Cozy Wool Slippers", "Sandal wol yang nyaman memberikan kehangatan dan kenyamanan."),
                    ],
                    "Dark": [
                        ("Dark Green Flannel Pajama Set", "Set piyama flanel hijau tua ini memberikan kesan hangat dan cocok untuk kulit hitam."),
                        ("Black Thermal Pants", "Celana thermal hitam memberikan kehangatan ekstra."),
                        ("Heated Slippers", "Sandal pemanas memberikan kenyamanan dan kehangatan yang luar biasa."),
                    ]
                }
            },
            "pajamas-women": {
                "Summer": {
                    "Light": [
                        ("White Cotton Pajama Set", "Set piyama katun putih ini memberikan kenyamanan dan kesegaran, cocok untuk warna kulit putih."),
                        ("Pink Sleep Shorts", "Celana tidur pink memberikan tampilan yang ceria dan ringan."),
                        ("Lightweight Slippers", "Sandal ringan memberikan kenyamanan saat berjalan di rumah."),
                    ],
                    "Medium": [
                        ("Light Blue Tank Top and Shorts Set", "Set tank top dan celana pendek biru muda ini memberikan tampilan yang segar dan cocok untuk kulit coklat atau sawo matang."),
                        ("Gray Sleep Shorts", "Celana tidur abu-abu memberikan kenyamanan dan gaya kasual."),
                        ("Soft Cotton Slippers", "Sandal katun lembut memberikan kenyamanan ekstra."),
                    ],
                    "Dark": [
                        ("Yellow Linen Pajama Set", "Set piyama linen kuning ini memberikan tampilan yang cerah dan cocok untuk kulit hitam."),
                        ("Dark Green Sleep Shorts", "Celana tidur hijau gelap memberikan tampilan yang elegan."),
                        ("Comfortable House Slippers", "Sandal rumah yang nyaman memberikan kemudahan dan kenyamanan."),
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Pastel Pink Pajama Set", "Set piyama pink pastel ini memberikan kesan feminin dan cocok untuk warna kulit putih."),
                        ("Light Gray Sleep Pants", "Celana tidur abu-abu muda memberikan kenyamanan dan gaya kasual."),
                        ("Soft Slip-On Slippers", "Sandal slip-on lembut memberikan kenyamanan saat berjalan di rumah."),
                    ],
                    "Medium": [
                        ("Green Striped Pajama Set", "Set piyama bergaris hijau memberikan tampilan yang segar dan cocok untuk kulit medium."),
                        ("White Sleep Pants", "Celana tidur putih memberikan kesan yang bersih dan segar."),
                        ("Foam Slippers", "Sandal busa memberikan kenyamanan ekstra saat berjalan di rumah."),
                    ],
                    "Dark": [
                        ("Cream Silk Pajama Set", "Set piyama sutra krem memberikan tampilan yang anggun dan cocok untuk kulit hitam."),
                        ("Navy Blue Sleep Pants", "Celana tidur biru navy memberikan kontras yang menarik."),
                        ("Fleece Slippers", "Sandal fleece memberikan kenyamanan dan kehangatan ekstra."),
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Pajama Set", "Set piyama oranye terbakar ini memberikan kesan hangat dan cocok untuk warna kulit putih."),
                        ("Dark Brown Sleep Pants", "Celana tidur cokelat gelap memberikan tampilan yang hangat."),
                        ("Wool Slippers", "Sandal wol memberikan kenyamanan dan kehangatan saat musim gugur."),
                    ],
                    "Medium": [
                        ("Olive Green Pajama Set", "Set piyama hijau zaitun memberikan tampilan yang hangat dan cocok untuk kulit coklat atau sawo matang."),
                        ("Maroon Sleep Pants", "Celana tidur merah marun memberikan kontras yang elegan."),
                        ("Leather House Slippers", "Sandal rumah kulit memberikan tampilan yang berkelas dan nyaman."),
                    ],
                    "Dark": [
                        ("Dark Brown Pajama Set", "Set piyama cokelat gelap memberikan tampilan yang elegan dan cocok untuk kulit hitam."),
                        ("Charcoal Gray Sleep Pants", "Celana tidur abu-abu arang memberikan tampilan yang solid."),
                        ("Knitted Slippers", "Sandal rajut memberikan kenyamanan dan kehangatan ekstra."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Gray Flannel Pajama Set", "Set piyama flanel abu-abu terang ini memberikan kesan hangat dan cocok untuk warna kulit putih."),
                        ("White Thermal Pants", "Celana thermal putih memberikan kehangatan ekstra."),
                        ("Fur-Lined Slippers", "Sandal berlapis bulu memberikan kenyamanan dan kehangatan ekstra."),
                    ],
                    "Medium": [
                        ("Navy Blue Flannel Pajama Set", "Set piyama flanel biru navy ini memberikan kesan hangat dan cocok untuk kulit medium."),
                        ("Gray Thermal Pants", "Celana thermal abu-abu memberikan kehangatan ekstra."),
                        ("Cozy Wool Slippers", "Sandal wol yang nyaman memberikan kehangatan dan kenyamanan."),
                    ],
                    "Dark": [
                        ("Dark Green Flannel Pajama Set", "Set piyama flanel hijau tua ini memberikan kesan hangat dan cocok untuk kulit hitam."),
                        ("Black Thermal Pants", "Celana thermal hitam memberikan kehangatan ekstra."),
                        ("Heated Slippers", "Sandal pemanas memberikan kenyamanan dan kehangatan yang luar biasa."),
                    ]
                }
            },
            "casual-men": {
                "Summer": {
                    "Light": [
                        ("White Polo Shirt", "Kaus polo putih memberikan tampilan yang segar dan bersih, cocok untuk warna kulit putih."),
                        ("Khaki Shorts", "Celana pendek khaki memberikan kenyamanan dan kesan santai."),
                        ("White Canvas Sneakers", "Sepatu kanvas putih memberikan tampilan yang bersih dan stylish."),
                    ],
                    "Medium": [
                        ("Navy Blue T-Shirt", "Kaos biru navy memberikan tampilan yang klasik dan cocok untuk kulit coklat atau sawo matang."),
                        ("Gray Chino Shorts", "Celana pendek chino abu-abu memberikan kenyamanan dan gaya kasual."),
                        ("Black Slip-On Sneakers", "Sepatu slip-on hitam memberikan tampilan yang modern dan nyaman."),
                    ],
                    "Dark": [
                        ("Light Gray Henley Shirt", "Kaus henley abu-abu terang memberikan tampilan yang elegan dan sejuk, cocok untuk kulit hitam."),
                        ("Navy Blue Cargo Shorts", "Celana pendek cargo biru navy memberikan tampilan yang kasual dan fungsional."),
                        ("White High-Top Sneakers", "Sepatu sneakers putih memberikan kontras yang cerah dan stylish."),
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Pastel Green T-Shirt", "Kaos hijau pastel memberikan tampilan yang segar dan cocok untuk warna kulit putih."),
                        ("Light Blue Jeans", "Jeans biru muda memberikan kenyamanan dan gaya kasual."),
                        ("White Sneakers", "Sepatu sneakers putih memberikan tampilan yang bersih dan trendi."),
                    ],
                    "Medium": [
                        ("Olive Green Button-Down Shirt", "Kemeja hijau zaitun memberikan tampilan yang kasual dan elegan, cocok untuk kulit medium."),
                        ("Khaki Pants", "Celana khaki memberikan tampilan yang bersih dan nyaman."),
                        ("Brown Leather Loafers", "Sepatu loafer kulit coklat memberikan tampilan yang berkelas."),
                    ],
                    "Dark": [
                        ("Bright Orange Hoodie", "Hoodie oranye cerah memberikan kesan energik dan modern, cocok untuk kulit hitam."),
                        ("Black Jogger Pants", "Celana jogger hitam memberikan tampilan yang santai dan keren."),
                        ("Gray Sneakers", "Sepatu sneakers abu-abu memberikan kesan yang trendi dan nyaman."),
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Flannel Shirt", "Kemeja flanel oranye terbakar memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih."),
                        ("Dark Blue Ripped Jeans", "Jeans robek biru gelap memberikan tampilan yang kasual dan edgy."),
                        ("Brown Leather Boots", "Sepatu bot kulit coklat memberikan tampilan yang klasik dan maskulin."),
                    ],
                    "Medium": [
                        ("Maroon Bomber Jacket", "Jaket bomber marun memberikan kesan hangat dan stylish, cocok untuk kulit coklat atau sawo matang."),
                        ("Black Skinny Jeans", "Jeans skinny hitam memberikan tampilan yang tajam dan modern."),
                        ("White Leather Sneakers", "Sepatu sneakers kulit putih memberikan kontras yang bersih dan trendi."),
                    ],
                    "Dark": [
                        ("Charcoal Gray Hoodie", "Hoodie abu-abu arang memberikan kesan kuat dan elegan, cocok untuk kulit hitam."),
                        ("Black Cargo Pants", "Celana cargo hitam memberikan tampilan yang kasual dan fungsional."),
                        ("Black Combat Boots", "Sepatu bot hitam memberikan tampilan yang solid dan maskulin."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Gray Puffer Jacket", "Jaket puffer abu-abu terang memberikan kesan hangat dan stylish, cocok untuk warna kulit putih."),
                        ("White Thermal Shirt", "Kaos thermal putih memberikan lapisan yang nyaman dan hangat."),
                        ("Black Skinny Jeans", "Jeans skinny hitam memberikan tampilan yang tajam dan modern."),
                    ],
                    "Medium": [
                        ("Navy Blue Peacoat", "Jaket peacoat biru navy memberikan kesan formal dan berkelas, sangat cocok dengan kulit medium."),
                        ("Gray Turtleneck Sweater", "Sweater turtleneck abu-abu memberikan tampilan yang hangat dan elegan."),
                        ("Black Chino Pants", "Celana chino hitam memberikan kesan terstruktur dan profesional."),
                    ],
                    "Dark": [
                        ("Dark Green Parka", "Jaket parka hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam."),
                        ("Black Thermal Shirt", "Kaos thermal hitam memberikan lapisan yang anggun dan hangat."),
                        ("Charcoal Gray Cargo Pants", "Celana cargo abu-abu gelap memberikan tampilan yang kasual dan fungsional."),
                    ]
                }
            },
            "casual-women": {
                "Summer": {
                    "Light": [
                        ("White Sleeveless Top", "Atasan tanpa lengan putih ini memberikan tampilan yang segar dan nyaman, cocok untuk warna kulit putih."),
                        ("Denim Shorts", "Celana pendek denim memberikan tampilan kasual dan stylish."),
                        ("White Espadrilles", "Sepatu espadrilles putih memberikan kenyamanan dan tampilan yang elegan."),
                    ],
                    "Medium": [
                        ("Coral T-Shirt", "Kaos coral memberikan kesan cerah dan cocok untuk kulit coklat atau sawo matang."),
                        ("Khaki Shorts", "Celana pendek khaki memberikan kenyamanan dan kesan santai."),
                        ("Beige Sandals", "Sandal beige memberikan tampilan yang ringan dan nyaman."),
                    ],
                    "Dark": [
                        ("Yellow Tank Top", "Tank top kuning memberikan kesan cerah dan energik, cocok untuk kulit hitam."),
                        ("White Linen Shorts", "Celana pendek linen putih memberikan tampilan yang sejuk dan nyaman."),
                        ("Navy Blue Sneakers", "Sepatu sneakers biru navy memberikan kontras yang stylish."),
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Pastel Pink Blouse", "Blus pink pastel ini memberikan kesan feminin dan cocok untuk warna kulit putih."),
                        ("Light Blue Jeans", "Jeans biru muda memberikan kenyamanan dan gaya kasual."),
                        ("White Ballet Flats", "Sepatu ballet flats putih memberikan tampilan yang elegan dan nyaman."),
                    ],
                    "Medium": [
                        ("Mint Green Button-Down Shirt", "Kemeja hijau mint memberikan tampilan yang segar dan cocok untuk kulit medium."),
                        ("Beige Capris", "Celana capri beige memberikan tampilan yang elegan dan kasual."),
                        ("Brown Leather Loafers", "Sepatu loafer kulit coklat memberikan tampilan yang berkelas."),
                    ],
                    "Dark": [
                        ("Bright Orange Tank Top", "Tank top oranye cerah memberikan kesan energik dan modern, cocok untuk kulit hitam."),
                        ("Black Leggings", "Legging hitam memberikan tampilan yang santai dan nyaman."),
                        ("Gray Slip-On Sneakers", "Sepatu slip-on abu-abu memberikan kesan yang trendi dan nyaman."),
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Cardigan", "Cardigan oranye terbakar memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih."),
                        ("Dark Blue Skinny Jeans", "Jeans skinny biru gelap memberikan tampilan yang kasual dan elegan."),
                        ("Brown Ankle Boots", "Sepatu bot coklat memberikan tampilan yang klasik dan hangat."),
                    ],
                    "Medium": [
                        ("Maroon Sweater", "Sweater marun memberikan kesan hangat dan cocok untuk kulit coklat atau sawo matang."),
                        ("Black Wide-Leg Pants", "Celana panjang hitam dengan potongan lebar memberikan tampilan yang elegan dan modern."),
                        ("White Sneakers", "Sepatu sneakers putih memberikan kontras yang bersih dan trendi."),
                    ],
                    "Dark": [
                        ("Olive Green Jacket", "Jaket hijau zaitun memberikan tampilan yang kuat dan cocok untuk kulit hitam."),
                        ("Charcoal Gray Skinny Jeans", "Jeans skinny abu-abu arang memberikan tampilan yang solid dan modern."),
                        ("Black Combat Boots", "Sepatu bot hitam memberikan tampilan yang kuat dan stylish."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Gray Wool Coat", "Mantel wol abu-abu terang memberikan kesan hangat dan elegan, cocok untuk warna kulit putih."),
                        ("White Knit Sweater", "Sweater rajut putih memberikan kenyamanan dan tampilan yang bersih."),
                        ("Black Jeans", "Jeans hitam memberikan tampilan yang tajam dan modern."),
                    ],
                    "Medium": [
                        ("Navy Blue Overcoat", "Mantel biru navy memberikan tampilan yang berkelas dan cocok untuk kulit medium."),
                        ("Gray Wool Turtleneck", "Turtleneck wol abu-abu memberikan kehangatan dan kesan elegan."),
                        ("Black Straight-Leg Pants", "Celana panjang hitam dengan potongan lurus memberikan tampilan yang terstruktur dan profesional."),
                    ],
                    "Dark": [
                        ("Dark Green Parka", "Parka hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam."),
                        ("Black Thermal Sweater", "Sweater thermal hitam memberikan kehangatan ekstra."),
                        ("Charcoal Gray Cargo Pants", "Celana cargo abu-abu gelap memberikan tampilan yang kasual dan fungsional."),
                    ]
                }
            },
            "sportswear-men": {
                "Summer": {
                    "Light": [
                        ("White Performance T-Shirt", "Kaos performa putih ini memberikan kenyamanan dan kesegaran, cocok untuk warna kulit putih."),
                        ("Blue Running Shorts", "Celana pendek lari biru memberikan kenyamanan dan sirkulasi udara yang baik."),
                        ("White Running Shoes", "Sepatu lari putih memberikan tampilan yang bersih dan nyaman."),
                    ],
                    "Medium": [
                        ("Gray Moisture-Wicking T-Shirt", "Kaos abu-abu dengan bahan yang menyerap keringat, cocok untuk kulit coklat atau sawo matang."),
                        ("Black Training Shorts", "Celana pendek training hitam memberikan tampilan yang modern dan nyaman."),
                        ("Red Running Shoes", "Sepatu lari merah memberikan tampilan yang stylish dan fungsional."),
                    ],
                    "Dark": [
                        ("Yellow Tank Top", "Tank top kuning memberikan kesan cerah dan energik, cocok untuk kulit hitam."),
                        ("Black Athletic Shorts", "Celana pendek atletik hitam memberikan tampilan yang kasual dan solid."),
                        ("White High-Top Sneakers", "Sepatu sneakers putih memberikan kontras yang cerah dan stylish."),
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Pastel Green Tank Top", "Tank top hijau pastel ini memberikan kesan segar dan cocok untuk warna kulit putih."),
                        ("Navy Blue Jogging Pants", "Celana jogging biru navy memberikan kenyamanan dan gaya kasual."),
                        ("White Running Shoes", "Sepatu lari putih memberikan tampilan yang bersih dan trendi."),
                    ],
                    "Medium": [
                        ("Blue Compression Shirt", "Kaos kompresi biru memberikan dukungan dan kenyamanan ekstra, cocok untuk kulit medium."),
                        ("Gray Athletic Pants", "Celana atletik abu-abu memberikan kenyamanan dan gaya kasual."),
                        ("Black Running Shoes", "Sepatu lari hitam memberikan tampilan yang tajam dan modern."),
                    ],
                    "Dark": [
                        ("Bright Orange Athletic Shirt", "Kaos atletik oranye cerah memberikan kesan energik dan modern, cocok untuk kulit hitam."),
                        ("Black Jogger Pants", "Celana jogger hitam memberikan tampilan yang santai dan keren."),
                        ("Gray Sneakers", "Sepatu sneakers abu-abu memberikan kesan yang trendi dan nyaman."),
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Hoodie", "Hoodie oranye terbakar memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih."),
                        ("Black Running Pants", "Celana lari hitam memberikan kenyamanan dan perlindungan."),
                        ("Brown Training Shoes", "Sepatu training coklat memberikan tampilan yang klasik dan solid."),
                    ],
                    "Medium": [
                        ("Maroon Long-Sleeve Shirt", "Kaos lengan panjang marun memberikan kesan hangat dan cocok untuk kulit coklat atau sawo matang."),
                        ("Black Training Pants", "Celana training hitam memberikan tampilan yang tajam dan modern."),
                        ("White Running Shoes", "Sepatu lari putih memberikan kontras yang bersih dan trendi."),
                    ],
                    "Dark": [
                        ("Olive Green Windbreaker", "Windbreaker hijau zaitun memberikan tampilan yang kuat dan cocok untuk kulit hitam."),
                        ("Gray Jogging Pants", "Celana jogging abu-abu memberikan tampilan yang santai dan nyaman."),
                        ("Black Running Shoes", "Sepatu lari hitam memberikan tampilan yang solid dan stylish."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Gray Fleece Jacket", "Jaket fleece abu-abu terang memberikan kesan hangat dan cocok untuk warna kulit putih."),
                        ("Black Thermal Pants", "Celana thermal hitam memberikan kehangatan ekstra."),
                        ("Fur-Lined Sneakers", "Sepatu sneakers berlapis bulu memberikan kenyamanan dan kehangatan ekstra."),
                    ],
                    "Medium": [
                        ("Navy Blue Puffer Vest", "Rompi puffer biru navy memberikan kesan hangat dan cocok untuk kulit medium."),
                        ("Gray Sweatpants", "Celana sweatpants abu-abu memberikan kenyamanan dan kehangatan."),
                        ("Black Running Shoes", "Sepatu lari hitam memberikan tampilan yang tajam dan modern."),
                    ],
                    "Dark": [
                        ("Dark Green Thermal Jacket", "Jaket thermal hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam."),
                        ("Black Fleece Pants", "Celana fleece hitam memberikan kehangatan ekstra."),
                        ("Heated Sneakers", "Sepatu sneakers dengan fitur pemanas memberikan kenyamanan dan kehangatan yang luar biasa."),
                    ]
                }
            },
            "sportswear-women": {
                "Summer": {
                    "Light": [
                        ("White Sports Bra", "Bra olahraga putih ini memberikan dukungan dan kenyamanan, cocok untuk warna kulit putih."),
                        ("Light Blue Running Shorts", "Celana pendek lari biru muda memberikan kenyamanan dan sirkulasi udara yang baik."),
                        ("White Running Shoes", "Sepatu lari putih memberikan tampilan yang bersih dan nyaman."),
                    ],
                    "Medium": [
                        ("Gray Sports Tank", "Tank olahraga abu-abu ini memberikan kenyamanan dan tampilan yang modern, cocok untuk kulit coklat atau sawo matang."),
                        ("Black Bike Shorts", "Celana pendek sepeda hitam memberikan tampilan yang fungsional dan stylish."),
                        ("Red Running Shoes", "Sepatu lari merah memberikan tampilan yang stylish dan fungsional."),
                    ],
                    "Dark": [
                        ("Bright Yellow Sports Bra", "Bra olahraga kuning cerah ini memberikan kesan energik dan modern, cocok untuk kulit hitam."),
                        ("Black Athletic Shorts", "Celana pendek atletik hitam memberikan tampilan yang kasual dan solid."),
                        ("White High-Top Sneakers", "Sepatu sneakers putih memberikan kontras yang cerah dan stylish."),
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Pastel Green Sports Tank", "Tank olahraga hijau pastel ini memberikan kesan segar dan cocok untuk warna kulit putih."),
                        ("Navy Blue Leggings", "Legging biru navy memberikan kenyamanan dan tampilan yang kasual."),
                        ("White Running Shoes", "Sepatu lari putih memberikan tampilan yang bersih dan trendi."),
                    ],
                    "Medium": [
                        ("Blue Compression Shirt", "Kaos kompresi biru memberikan dukungan dan kenyamanan ekstra, cocok untuk kulit medium."),
                        ("Gray Athletic Pants", "Celana atletik abu-abu memberikan kenyamanan dan gaya kasual."),
                        ("Black Running Shoes", "Sepatu lari hitam memberikan tampilan yang tajam dan modern."),
                    ],
                    "Dark": [
                        ("Bright Orange Sports Tank", "Tank olahraga oranye cerah ini memberikan kesan energik dan modern, cocok untuk kulit hitam."),
                        ("Black Jogger Pants", "Celana jogger hitam memberikan tampilan yang santai dan keren."),
                        ("Gray Sneakers", "Sepatu sneakers abu-abu memberikan kesan yang trendi dan nyaman."),
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Hoodie", "Hoodie oranye terbakar ini memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih."),
                        ("Black Running Pants", "Celana lari hitam memberikan kenyamanan dan perlindungan."),
                        ("Brown Training Shoes", "Sepatu training coklat memberikan tampilan yang klasik dan solid."),
                    ],
                    "Medium": [
                        ("Maroon Long-Sleeve Shirt", "Kaos lengan panjang marun ini memberikan kesan hangat dan cocok untuk kulit coklat atau sawo matang."),
                        ("Black Training Pants", "Celana training hitam memberikan tampilan yang tajam dan modern."),
                        ("White Running Shoes", "Sepatu lari putih memberikan kontras yang bersih dan trendi."),
                    ],
                    "Dark": [
                        ("Olive Green Windbreaker", "Windbreaker hijau zaitun ini memberikan tampilan yang kuat dan cocok untuk kulit hitam."),
                        ("Gray Jogging Pants", "Celana jogging abu-abu memberikan tampilan yang santai dan nyaman."),
                        ("Black Running Shoes", "Sepatu lari hitam memberikan tampilan yang solid dan stylish."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Gray Fleece Jacket", "Jaket fleece abu-abu terang ini memberikan kesan hangat dan cocok untuk warna kulit putih."),
                        ("Black Thermal Pants", "Celana thermal hitam memberikan kehangatan ekstra."),
                        ("Fur-Lined Sneakers", "Sepatu sneakers berlapis bulu memberikan kenyamanan dan kehangatan ekstra."),
                    ],
                    "Medium": [
                        ("Navy Blue Puffer Vest", "Rompi puffer biru navy ini memberikan kesan hangat dan cocok untuk kulit medium."),
                        ("Gray Sweatpants", "Celana sweatpants abu-abu memberikan kenyamanan dan kehangatan."),
                        ("Black Running Shoes", "Sepatu lari hitam memberikan tampilan yang tajam dan modern."),
                    ],
                    "Dark": [
                        ("Dark Green Thermal Jacket", "Jaket thermal hijau tua ini memberikan kesan hangat dan kuat, cocok untuk kulit hitam."),
                        ("Black Fleece Pants", "Celana fleece hitam memberikan kehangatan ekstra."),
                        ("Heated Sneakers", "Sepatu sneakers dengan fitur pemanas memberikan kenyamanan dan kehangatan yang luar biasa."),
                    ]
                }
            },
            "vintage-men": {
                "Summer": {
                    "Light": [
                        ("White Linen Shirt", "Kemeja linen putih ini memberikan tampilan yang klasik dan sejuk, cocok untuk warna kulit putih."),
                        ("Khaki High-Waisted Shorts", "Celana pendek high-waisted khaki memberikan tampilan yang klasik dan santai."),
                        ("Brown Leather Loafers", "Sepatu loafer kulit coklat memberikan tampilan yang elegan dan berkelas."),
                    ],
                    "Medium": [
                        ("Light Blue Chambray Shirt", "Kemeja chambray biru muda ini memberikan tampilan yang kasual dan cocok untuk kulit coklat atau sawo matang."),
                        ("Beige Pleated Trousers", "Celana panjang berlipat beige memberikan tampilan yang klasik dan nyaman."),
                        ("White Canvas Sneakers", "Sepatu kanvas putih memberikan kontras yang bersih dan stylish."),
                    ],
                    "Dark": [
                        ("Navy Blue Henley Shirt", "Kaus henley biru navy memberikan tampilan yang klasik dan sejuk, cocok untuk kulit hitam."),
                        ("Olive Green Chino Shorts", "Celana pendek chino hijau zaitun memberikan tampilan yang kasual dan fungsional."),
                        ("Black Leather Oxfords", "Sepatu oxford kulit hitam memberikan tampilan yang elegan dan berkelas."),
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Pastel Yellow Polo Shirt", "Kaus polo kuning pastel ini memberikan tampilan yang segar dan cocok untuk warna kulit putih."),
                        ("Light Gray Tailored Trousers", "Celana panjang tailored abu-abu muda memberikan kenyamanan dan gaya kasual."),
                        ("White Brogues", "Sepatu brogue putih memberikan tampilan yang elegan dan klasik."),
                    ],
                    "Medium": [
                        ("Mint Green Button-Down Shirt", "Kemeja hijau mint ini memberikan tampilan yang segar dan cocok untuk kulit medium."),
                        ("Brown Corduroy Pants", "Celana corduroy coklat memberikan tampilan yang klasik dan nyaman."),
                        ("Beige Desert Boots", "Sepatu desert beige memberikan tampilan yang kasual dan elegan."),
                    ],
                    "Dark": [
                        ("Bright Orange Short-Sleeve Shirt", "Kemeja lengan pendek oranye cerah ini memberikan kesan energik dan modern, cocok untuk kulit hitam."),
                        ("Black Wide-Leg Trousers", "Celana panjang hitam dengan potongan lebar memberikan tampilan yang elegan dan modern."),
                        ("Brown Leather Moccasins", "Sepatu mokasin kulit coklat memberikan tampilan yang klasik dan nyaman."),
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Cardigan", "Cardigan oranye terbakar memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih."),
                        ("Dark Blue Straight-Leg Jeans", "Jeans dengan potongan lurus biru gelap memberikan tampilan yang kasual dan elegan."),
                        ("Brown Brogue Shoes", "Sepatu brogue coklat memberikan tampilan yang klasik dan berkelas."),
                    ],
                    "Medium": [
                        ("Maroon Crewneck Sweater", "Sweater crewneck marun ini memberikan kesan hangat dan cocok untuk kulit coklat atau sawo matang."),
                        ("Black Dress Trousers", "Celana panjang hitam memberikan tampilan yang elegan dan profesional."),
                        ("White Leather Sneakers", "Sepatu sneakers kulit putih memberikan kontras yang bersih dan trendi."),
                    ],
                    "Dark": [
                        ("Olive Green Blazer", "Blazer hijau zaitun memberikan tampilan yang kuat dan cocok untuk kulit hitam."),
                        ("Charcoal Gray Wool Pants", "Celana wol abu-abu arang memberikan tampilan yang solid dan modern."),
                        ("Black Chelsea Boots", "Sepatu bot chelsea hitam memberikan tampilan yang kuat dan stylish."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Gray Wool Overcoat", "Mantel wol abu-abu terang memberikan kesan hangat dan elegan, cocok untuk warna kulit putih."),
                        ("White Turtleneck Sweater", "Sweater turtleneck putih memberikan kenyamanan dan tampilan yang bersih."),
                        ("Black Dress Pants", "Celana panjang hitam memberikan tampilan yang tajam dan modern."),
                    ],
                    "Medium": [
                        ("Navy Blue Peacoat", "Jaket peacoat biru navy memberikan tampilan yang berkelas dan cocok untuk kulit medium."),
                        ("Gray Wool Turtleneck", "Turtleneck wol abu-abu memberikan kehangatan dan kesan elegan."),
                        ("Black Straight-Leg Pants", "Celana panjang hitam dengan potongan lurus memberikan tampilan yang terstruktur dan profesional."),
                    ],
                    "Dark": [
                        ("Dark Green Parka", "Parka hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam."),
                        ("Black Thermal Sweater", "Sweater thermal hitam memberikan kehangatan ekstra."),
                        ("Charcoal Gray Cargo Pants", "Celana cargo abu-abu gelap memberikan tampilan yang kasual dan fungsional."),
                    ]
                }
            },
            "vintage-women": {
                "Summer": {
                    "Light": [
                        ("White Lace Blouse", "Blus renda putih ini memberikan tampilan yang klasik dan feminin, cocok untuk warna kulit putih."),
                        ("High-Waisted Denim Shorts", "Celana pendek denim high-waisted memberikan tampilan kasual yang vintage."),
                        ("Brown Leather Sandals", "Sandal kulit coklat memberikan kenyamanan dan tampilan yang elegan."),
                    ],
                    "Medium": [
                        ("Light Blue Chambray Dress", "Gaun chambray biru muda ini memberikan tampilan kasual yang cocok untuk kulit coklat atau sawo matang."),
                        ("Beige Espadrilles", "Espadrilles beige memberikan kenyamanan dan tampilan yang stylish."),
                        ("Leather Belt", "Sabuk kulit memberikan aksen vintage yang berkelas."),
                    ],
                    "Dark": [
                        ("Red Polka Dot Blouse", "Blus polka dot merah ini memberikan tampilan yang ceria dan cocok untuk kulit hitam."),
                        ("White Linen Pants", "Celana linen putih memberikan tampilan yang sejuk dan nyaman."),
                        ("Navy Blue Flats", "Sepatu flats biru navy memberikan kenyamanan dan tampilan yang elegan."),
                    ]
                },
                "Spring": {
                    "Light": [
                        ("Pastel Pink Cardigan", "Cardigan pink pastel ini memberikan tampilan yang segar dan cocok untuk warna kulit putih."),
                        ("Light Gray A-Line Skirt", "Rok A-line abu-abu muda memberikan tampilan yang feminin dan elegan."),
                        ("White Mary Janes", "Sepatu Mary Janes putih memberikan tampilan yang klasik dan nyaman."),
                    ],
                    "Medium": [
                        ("Mint Green Wrap Dress", "Gaun wrap hijau mint ini memberikan tampilan yang segar dan cocok untuk kulit medium."),
                        ("Beige Kitten Heels", "Sepatu kitten heels beige memberikan kenyamanan dan tampilan yang elegan."),
                        ("Leather Satchel Bag", "Tas satchel kulit memberikan tampilan yang klasik dan berkelas."),
                    ],
                    "Dark": [
                        ("Bright Orange Sundress", "Gaun sundress oranye cerah ini memberikan kesan energik dan modern, cocok untuk kulit hitam."),
                        ("Black Wide-Brim Hat", "Topi bertepi lebar hitam memberikan tampilan yang elegan dan melindungi dari sinar matahari."),
                        ("Brown Leather Loafers", "Sepatu loafer kulit coklat memberikan tampilan yang nyaman dan berkelas."),
                    ]
                },
                "Autumn": {
                    "Light": [
                        ("Burnt Orange Knit Sweater", "Sweater rajut oranye terbakar ini memberikan kesan hangat dan nyaman, cocok untuk warna kulit putih."),
                        ("Dark Blue Straight-Leg Jeans", "Jeans dengan potongan lurus biru gelap memberikan tampilan yang kasual dan elegan."),
                        ("Brown Ankle Boots", "Sepatu bot coklat memberikan tampilan yang klasik dan hangat."),
                    ],
                    "Medium": [
                        ("Maroon Corduroy Skirt", "Rok corduroy marun ini memberikan kesan hangat dan cocok untuk kulit coklat atau sawo matang."),
                        ("Black Turtleneck Sweater", "Sweater turtleneck hitam memberikan tampilan yang elegan dan hangat."),
                        ("White Ankle Boots", "Sepatu bot putih memberikan kontras yang bersih dan trendi."),
                    ],
                    "Dark": [
                        ("Olive Green Trench Coat", "Mantel trench hijau zaitun memberikan tampilan yang kuat dan cocok untuk kulit hitam."),
                        ("Charcoal Gray Wool Pants", "Celana wol abu-abu arang memberikan tampilan yang solid dan modern."),
                        ("Black Chelsea Boots", "Sepatu bot chelsea hitam memberikan tampilan yang kuat dan stylish."),
                    ]
                },
                "Winter": {
                    "Light": [
                        ("Light Gray Wool Coat", "Mantel wol abu-abu terang memberikan kesan hangat dan elegan, cocok untuk warna kulit putih."),
                        ("White Knit Sweater", "Sweater rajut putih memberikan kenyamanan dan tampilan yang bersih."),
                        ("Black Jeans", "Jeans hitam memberikan tampilan yang tajam dan modern."),
                    ],
                    "Medium": [
                        ("Navy Blue Peacoat", "Jaket peacoat biru navy memberikan tampilan yang berkelas dan cocok untuk kulit medium."),
                        ("Gray Wool Turtleneck", "Turtleneck wol abu-abu memberikan kehangatan dan kesan elegan."),
                        ("Black Straight-Leg Pants", "Celana panjang hitam dengan potongan lurus memberikan tampilan yang terstruktur dan profesional."),
                    ],
                    "Dark": [
                        ("Dark Green Parka", "Parka hijau tua memberikan kesan hangat dan kuat, cocok untuk kulit hitam."),
                        ("Black Thermal Sweater", "Sweater thermal hitam memberikan kehangatan ekstra."),
                        ("Charcoal Gray Cargo Pants", "Celana cargo abu-abu gelap memberikan tampilan yang kasual dan fungsional."),
                    ]
                }
            },
        }

      # Return outfit recommendations based on the given clothing type, seasonal color, and skin tone
      return recommendations.get(clothing_type, {}).get(seasonal_color, {}).get(skin_tone, [])    

# Kelas utama aplikasi Flask untuk menjalankan API prediksi
class ColorAnalysisApp:
    def __init__(self):
        """
        Konstruktor untuk aplikasi Flask. Menyiapkan aplikasi dan memuat model yang diperlukan.
        """

        load_dotenv()

        # Inisialisasi Firebase
        try:
            # Membuat path ke file kredensial Firebase
            cred_path = os.path.join(os.path.dirname(__file__), 'smartfit-capstone-firebase-adminsdk.json')
            
            # Memeriksa apakah file kredensial ada
            if not os.path.exists(cred_path):
                raise FileNotFoundError(f"File kredensial Firebase tidak ditemukan di {cred_path}")
            
            # Inisialisasi kredensial Firebase
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://smartfit-capstone-default-rtdb.asia-southeast1.firebasedatabase.app/'
            })
            
            logger.info("Firebase berhasil diinisialisasi")
        except Exception as e:
            logger.error(f"Gagal menginisialisasi Firebase: {e}")
            raise

        self.app = Flask(__name__)  # Membuat aplikasi Flask
        self.model_analyzer = ModelAnalyzer(
            seasonal_model_path='models/seasonal_color_model_improved.h5',
            skintone_model_path='models/skintone_model.h5'
        )

        self.RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY") or os.environ.get('RAPIDAPI_KEY')
        self.RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST") or os.environ.get('RAPIDAPI_HOST')
        self.RAPIDAPI_URL = os.getenv("RAPIDAPI_URL") or os.environ.get()

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
            return jsonify({
                "error": "Bad Request",
                "message": "Permintaan tidak valid"
            }), 400

        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                "error": "Not Found",
                "message": "Sumber daya tidak ditemukan"
            }), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({
                "error": "Internal Server Error",
                "message": "Terjadi kesalahan internal pada server"
            }), 500

    def search_amazon_products(self, query, page_size=1):
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
          "x-rapidapi-host": self.RAPIDAPI_HOST
      }

      try:
          # Mengirim permintaan GET ke API Amazon
          response = requests.get(self.RAPIDAPI_URL, headers=headers, params=querystring)

          # Memeriksa jika ada rate-limiting (kode status 429)
          if response.status_code == 429:
              logger.warning(f"Rate limit hit for query: {query}. Retrying after 10 seconds.")
              time.sleep(10)  # Menunggu 10 detik sebelum mencoba ulang
              response = requests.get(self.RAPIDAPI_URL, headers=headers, params=querystring)

          # Memeriksa jika terjadi error 403 (forbidden)
          if response.status_code == 403:
              logger.error(f"Forbidden error for query: {query}. Check your API key or access permissions.")
              return []

          # Memastikan respons berhasil (status code 200)
          response.raise_for_status()

          # Menangani respons JSON
          data = response.json()

          # Log the full Amazon API response for debugging
          logger.info(f"Full Amazon API response for query '{query}': {data}")

          # Mengekstrak produk dari hasil yang diterima
          products = []
          items = data.get('data', {}).get('products', [])

          # Jika tidak ada produk ditemukan, beri peringatan
          if not items:
              logger.warning(f"No products found in Amazon response for query: {query}")
          else:
              logger.info(f"Found {len(items)} items for query: {query}")

          # Ambil hanya 3 produk pertama dari daftar hasil
          for item in items[:page_size]:
              product = {
                  "asin": item.get('asin'),
                  "title": item.get('product_title'),
                  "price": item.get('product_price', 'Not Available'),  # Menambahkan fallback jika harga tidak ada
                  "pic": item.get('product_photo', ''),
                  "detail_url": item.get('product_url', ''),
                  "sales_volume": item.get('sales_volume', 'Not Available'),  # Menambahkan fallback jika sales_volume tidak ada
                  "is_prime": item.get('is_prime', False),
                  "delivery": item.get('delivery', 'Not specified'),
              }

              # Log each product for debugging purposes
              logger.info(f"Product found: {product['title']} - {product['price']}")

              # Menambahkan produk ke dalam daftar produk
              products.append(product)

          # Menampilkan sisa permintaan yang tersisa pada header respons
          remaining_requests = response.headers.get('X-RateLimit-Remaining')
          total_requests = response.headers.get('X-RateLimit-Limit')

          logger.info(f"Remaining API requests: {remaining_requests}/{total_requests}")

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
        @self.app.route('/predict_color_palette', methods=['POST'])
        def predict_color_palette():
            """
            Rute API untuk menerima gambar dan mengembalikan prediksi warna musiman dan kulit.
            """
            try:
                # Validasi unggahan gambar
                if 'image' not in request.files:
                    return jsonify({
                        "error": "Tidak ada gambar diunggah",
                        "details": "Pastikan Anda mengunggah file gambar"
                    }), 400
                
                image_file = request.files['image'].read()
                
                # Prediksi warna berdasarkan gambar yang diunggah
                try:
                    prediction_result = self.model_analyzer.predict(image_file)
                    return jsonify(prediction_result), 200
                except ImageProcessingError as img_error:
                    return jsonify({
                        "error": "Kesalahan Pemrosesan Gambar",
                        "details": str(img_error)
                    }), 422
                
            except Exception as e:
                logger.error(f"Kesalahan prediksi: {e}")
                logger.error(traceback.format_exc())
                return jsonify({
                    "error": "Prediksi Gagal",
                    "details": str(e)
                }), 500

        @self.app.route('/model_details', methods=['GET'])
        def model_details():
            """
            Rute API untuk mengambil detail tentang model yang digunakan.
            """
            try:
                # Mengambil detail model yang digunakan
                return jsonify({
                    "seasonal_model": {
                        "path": self.model_analyzer.seasonal_model_path,
                        "input_shape": self.model_analyzer.seasonal_model.input_shape,
                        "output_shape": self.model_analyzer.seasonal_model.output_shape
                    },
                    "skintone_model": {
                        "path": self.model_analyzer.skintone_model_path,
                        "input_shape": self.model_analyzer.skintone_model.input_shape,
                        "output_shape": self.model_analyzer.skintone_model.output_shape
                    }
                }), 200
            except Exception as e:
                return jsonify({
                    "error": "Gagal mengambil detail model",
                    "details": str(e)
                }), 500

        @self.app.route('/style_recommendation', methods=['POST'])
        def style_recommendation():
            try:
                if 'image' not in request.files:
                    return jsonify({
                        "error": "No image uploaded",
                        "details": "Make sure you upload an image file."
                    }), 400
                
                # Ambil UID dari form data
                uid = request.form.get('uid')
                if not uid:
                    return jsonify({
                        "error": "No User ID provided",
                        "details": "Please provide a Firebase User ID"
                    }), 400

                image_file = request.files['image'].read()

                # Default to 'streetwear' if not provided
                clothing_type = request.form.get('clothing_type', 'streetwear').lower()

                # Validate clothing type
                valid_clothing_types = ['formal-men', 'formal-women', 'wedding-men', 'wedding-women', 'streetwear-men', 'streetwear-women', 'pajamas-men', 'pajamas-women', 'vintage-men', 'vintage-women', 'casual-men', 'casual-women', 'sportswear-men', 'sportswear-women']
                if clothing_type not in valid_clothing_types:
                    clothing_type = 'streetwear'  # Default if invalid type provided

                try:
                    # Predict color and style
                    color_prediction = self.model_analyzer.predict(image_file)
                    seasonal_color = color_prediction['seasonal_color_label']

                    # Get color palette for the season
                    color_palette = self.model_analyzer.color_palettes.get(seasonal_color, {})

                    # Get outfit recommendations
                    outfit_recommendations = self.model_analyzer.predict_outfit(
                        color_prediction['seasonal_color_label'],
                        color_prediction['skin_tone_label'],
                        clothing_type
                    )

                    # Initialize amazon_products as an empty list
                    amazon_products = []
                    unique_queries = set()

                    for item, description in outfit_recommendations:
                        if item not in unique_queries:
                            unique_queries.add(item)
                            products = self.search_amazon_products(item, page_size=1)
                            
                            # Add description to each product
                            for product in products:
                                product['description'] = description

                            if products:
                                amazon_products.append(products[0])

                    # Ensure only 4 unique products are returned
                    amazon_products = amazon_products[:4]

                    # Persiapkan data untuk disimpan di Firebase
                    prediction_data = {
                        **color_prediction,
                        "color_palette": color_palette,
                        "seasonal_description": self._get_seasonal_description(seasonal_color),
                        "outfit_recommendations": [
                            {"item": item, "description": desc} 
                            for item, desc in outfit_recommendations
                        ],
                        "amazon_products": amazon_products,
                        "clothing_type": clothing_type,
                        "user_uid": uid
                    }

                    # Simpan prediksi ke Firebase
                    firebase_key = self.save_prediction_to_firebase(uid, prediction_data)

                    # Tambahkan firebase_key ke response jika berhasil disimpan
                    if firebase_key:
                        prediction_data['firebase_key'] = firebase_key

                    return jsonify(prediction_data), 200

                except Exception as predict_error:
                    logger.error(f"Prediction error: {predict_error}")
                    return jsonify({
                        "error": "Prediction failed",
                        "details": str(predict_error)
                    }), 500
            
            except Exception as e:
                logger.error(f"Error during style recommendation: {e}")
                return jsonify({
                    "error": "Style recommendation failed",
                    "details": str(e)
                }), 500

        @self.app.route('/delete_prediction_history', methods=['POST'])
        def delete_prediction_history():
            try:                
                # Validasi input
                uid = request.form.get('uid')
                prediction_key = request.form.get('prediction_key')
                
                if not uid or not prediction_key:
                    return jsonify({
                        "error": "Missing required parameters",
                        "details": "Both 'uid' and 'prediction_key' are required"
                    }), 400

                # Referensi ke node spesifik di Firebase
                ref = db.reference(f'prediction_history/{uid}/{prediction_key}')
                
                # Hapus prediction history
                ref.delete()
                
                logger.info(f"Prediction history {prediction_key} for user {uid} deleted successfully")
                
                return jsonify({
                    "message": "Prediction history deleted successfully",
                    "prediction_key": prediction_key
                }), 200

            except Exception as e:
                logger.error(f"Error deleting prediction history: {e}")
                return jsonify({
                    "error": "Failed to delete prediction history",
                    "details": str(e)
                }), 500

        @self.app.route('/get_prediction_history_list', methods=['GET'])
        def get_prediction_history_list():
            try:
                # Ambil data dari query parameter uid
                uid = request.args.get('uid')

                # Validasi input
                if not uid:
                    return jsonify({
                        "error": "Missing required parameter",
                        "details": "'uid' is required"
                    }), 400

                # Referensi ke node prediction_history di Firebase
                ref = db.reference(f'prediction_history/{uid}')
                
                # Ambil semua prediction history untuk uid
                prediction_data = ref.get()

                # Cek jika data tidak ditemukan
                if prediction_data is None:
                    return jsonify({
                        "error": "Data not found",
                        "details": f"No prediction history found for user {uid}"
                    }), 404
                
                # Jika data ditemukan, kirimkan data dalam format list
                return jsonify({
                    "message": "Prediction history list retrieved successfully",
                    "prediction_data": prediction_data
                }), 200

            except Exception as e:
                logger.error(f"Error retrieving prediction history list: {e}")
                return jsonify({
                    "error": "Failed to retrieve prediction history list",
                    "details": str(e)
                }), 500

        @self.app.route('/get_prediction_history_detail', methods=['GET'])
        def get_prediction_history_detail():
            try:
                # Ambil data dari query parameters
                uid = request.args.get('uid')
                prediction_key = request.args.get('prediction_key')

                # Validasi input
                if not uid or not prediction_key:
                    return jsonify({
                        "error": "Missing required parameters",
                        "details": "Both 'uid' and 'prediction_key' are required"
                    }), 400

                # Referensi ke node prediction_history tertentu di Firebase
                ref = db.reference(f'prediction_history/{uid}/{prediction_key}')
                
                # Ambil detail prediction history
                prediction_data = ref.get()
                
                # Cek jika data tidak ditemukan
                if prediction_data is None:
                    return jsonify({
                        "error": "Data not found",
                        "details": f"No prediction history found for user {uid} and key {prediction_key}"
                    }), 404
                
                # Jika data ditemukan, kirimkan data detail
                return jsonify({
                    "message": "Prediction history detail retrieved successfully",
                    "prediction_data": prediction_data
                }), 200

            except Exception as e:
                logger.error(f"Error retrieving prediction history detail: {e}")
                return jsonify({
                    "error": "Failed to retrieve prediction history detail",
                    "details": str(e)
                }), 500

    def _get_seasonal_description(self, season):
        """
        Memberikan deskripsi mendalam tentang karakteristik setiap musim.
        """
        seasonal_descriptions = {
            "Summer": "Musim panas adalah periode yang penuh cahaya dan kehangatan. Warna-warna lembut dan cerah mendominasi, mencerminkan energi dan keceriaan. Pakaian ringan dan bernapas menjadi pilihan utama untuk mengatasi suhu yang tinggi. Nuansa warna seperti biru pastel, hijau muda, dan merah muda lembut menggambarkan kesegaran dan ketenangan musim ini.",
            "Winter": "Musim dingin identik dengan keanggunan dan kedalaman warna. Warna-warna gelap dan kaya seperti navy, hitam, dan abu-abu mendominasi, mencerminkan ketenangan dan kecanggihan. Pakaian tebal dan berlapis menjadi kebutuhan untuk melindungi dari udara dingin. Nuansa warna yang dalam menggambarkan kekokohan dan keberanian.",
            "Spring": "Musim semi adalah simbol kebangkitan dan pertumbuhan. Warna-warna cerah dan segar seperti hijau muda, pink lembut, dan kuning mendominasi, melambangkan harapan dan pembaruan. Pakaian ringan dengan lapisan yang dapat disesuaikan menjadi pilihan, mencerminkan transisi dari musim dingin ke musim panas.",
            "Autumn": "Musim gugur penuh dengan warna-warna hangat dan kaya. Cokelat, merah bata, emas, dan hijau zaitun mencerminkan perubahan alam. Pakaian berlapis dengan tekstur yang lebih berat menjadi pilihan, menangkap kedalaman dan kedewasaan musim ini. Warna-warna musim gugur melambangkan transformasi, kematangan, dan keanggunan."
        }
        return seasonal_descriptions.get(season, "Deskripsi musim tidak tersedia.")            

    def save_prediction_to_firebase(self, uid, prediction_data):
        """
        Menyimpan hasil prediksi ke Firebase Realtime Database.
        
        Args:
            uid (str): User ID dari Firebase Authentication
            prediction_data (dict): Data hasil prediksi untuk disimpan
        
        Returns:
            str: Kunci (key) dari data yang disimpan di database
        """
        try:
            # Referensi ke node 'prediction_history' di database
            ref = db.reference('prediction_history')
            
            # Tambahkan timestamp untuk setiap prediksi
            prediction_data['timestamp'] = datetime.utcnow().isoformat()
            
            # Simpan data dengan UID sebagai child node
            new_prediction_ref = ref.child(uid).push(prediction_data)
            
            logger.info(f"Prediksi berhasil disimpan untuk user {uid}")
            
            # Kembalikan kunci dari prediksi yang baru disimpan
            return new_prediction_ref.key
        except Exception as e:
            logger.error(f"Gagal menyimpan prediksi ke Firebase: {e}")
            return None

    def run(self, debug=True, host='0.0.0.0', port=5000):
        """
        Menjalankan aplikasi Flask di server lokal.
        """
        self.app.run(debug=debug, host=host, port=port)

# Buat instance aplikasi
color_app = ColorAnalysisApp()

# Buat variabel app untuk digunakan oleh server WSGI
app = color_app.app

# Jika script dijalankan secara langsung
if __name__ == '__main__':
    color_app.run()
