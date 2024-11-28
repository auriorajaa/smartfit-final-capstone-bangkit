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

# Konfigurasi Logging yang Lebih Komprehensif
logging.basicConfig(
    level=logging.INFO,  # Level log ditetapkan pada INFO untuk menangkap semua log penting
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Format log
    handlers=[
        logging.FileHandler('color_analysis_comprehensive.log', encoding='utf-8'),  # Menyimpan log ke file
        logging.StreamHandler()  # Menampilkan log di terminal
    ]
)
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
          "formal": {
              "Summer": {
                  "Light": ["Soft blue blazer", "Light gray suit", "Pastel pink dress shirt"],
                  "Medium": ["Formal Navy suit", "Formal gray blazer", "Formal purple shirt"],
                  "Dark": ["Charcoal gray suit", "Deep navy blazer", "Rich jewel-toned shirts"]
              },
              "Winter": {
                  "Light": ["Dark blue blazer", "White dress shirt", "Black trousers"],
                  "Medium": ["Gray suit", "Black blazer", "Crimson red shirt"],
                  "Dark": ["Black suit", "Deep maroon shirt", "Charcoal trousers"]
              },
              "Spring": {
                  "Light": ["Light green dress shirt", "Beige trousers", "Light brown shoes"],
                  "Medium": ["Peach blouse", "Khaki jacket", "Cream colored pants"],
                  "Dark": ["Warm brown blazer", "Olive shirt", "Dark jeans"]
              },
              "Autumn": {
                  "Light": ["Burnt orange dress shirt", "Brown blazer", "Beige pants"],
                  "Medium": ["Olive shirt", "Brown leather jacket", "Dark trousers"],
                  "Dark": ["Dark burgundy suit", "Forest green shirt", "Charcoal jeans"]
              }
          },
          "wedding": {
              "Summer": {
                  "Light": ["Ivory satin gown", "Soft blush pink dress", "Silver cufflinks", "Pearl necklace"],
                  "Medium": ["Champagne colored dress", "Navy tuxedo", "Lavender pocket square", "White dress shirt"],
                  "Dark": ["Deep burgundy gown", "Black tuxedo", "Gold tie", "Emerald earrings"]
              },
              "Winter": {
                  "Light": ["White lace gown", "Ivory dress shirt", "Crystal necklace", "Black velvet blazer"],
                  "Medium": ["Silver wedding dress", "Charcoal tuxedo", "Red rose boutonnière", "Black dress shoes"],
                  "Dark": ["Deep red gown", "Black velvet tuxedo", "Dark emerald tie", "Pearl bracelet"]
              },
              "Spring": {
                  "Light": ["Pastel pink wedding dress", "Soft lavender dress shirt", "Floral bouquet", "Rose gold accessories"],
                  "Medium": ["Soft coral gown", "Gray tuxedo", "Pink bow tie", "Silver watch"],
                  "Dark": ["Burnt orange dress", "Maroon tuxedo", "Dark green boutonnière", "Gold cufflinks"]
              },
              "Autumn": {
                  "Light": ["Champagne colored dress", "Beige suit", "Burgundy tie", "Gold necklace"],
                  "Medium": ["Golden yellow gown", "Brown tuxedo", "Copper accessories", "Orange boutonnière"],
                  "Dark": ["Maroon dress", "Black tuxedo", "Dark copper cufflinks", "Emerald jewelry"]
              }
          },
          "streetwear": {
              "Summer": {
                  "Light": ["White graphic t-shirt", "Light wash jeans", "Sneakers", "Baseball cap"],
                  "Medium": ["Gray hoodie", "Black joggers", "White sneakers", "Canvas backpack"],
                  "Dark": ["Black bomber jacket", "Charcoal cargo pants", "Dark boots", "Silver chain"]
              },
              "Winter": {
                  "Light": ["Puffer jacket", "White hoodie", "Beige cargo pants", "High-top sneakers"],
                  "Medium": ["Plaid flannel shirt", "Dark denim jeans", "Boots", "Wool beanie"],
                  "Dark": ["Leather jacket", "Black jeans", "Combat boots", "Dark sunglasses"]
              },
              "Spring": {
                  "Light": ["Floral print shirt", "Denim shorts", "Slip-on shoes", "Bucket hat"],
                  "Medium": ["Olive jacket", "White t-shirt", "Khaki chinos", "Canvas sneakers"],
                  "Dark": ["Dark denim jacket", "Graphic sweatshirt", "Black skinny jeans", "Leather boots"]
              },
              "Autumn": {
                  "Light": ["Brown leather jacket", "Orange hoodie", "Jeans", "Chukka boots"],
                  "Medium": ["Plaid shirt", "Olive bomber jacket", "Dark jeans", "Wool hat"],
                  "Dark": ["Maroon sweatshirt", "Black leather jacket", "Dark trousers", "High-top boots"]
              }
          },
          "pajamas": {
              "Summer": {
                  "Light": ["Cotton shorts", "White tank top", "Flip flops"],
                  "Medium": ["Short-sleeve pajama set", "Linen shorts", "Cotton slippers"],
                  "Dark": ["Black cotton sleep shirt", "Dark navy pajama pants", "Cozy slippers"]
              },
              "Winter": {
                  "Light": ["Flannel sleep pants", "Long-sleeve cotton shirt", "Warm socks"],
                  "Medium": ["Thermal pajamas", "Cashmere sleep set", "Warm slippers"],
                  "Dark": ["Velvet pajamas", "Black fleece sleep shirt", "Thermal socks"]
              },
              "Spring": {
                  "Light": ["Floral print pajamas", "Cotton shorts", "Slippers"],
                  "Medium": ["Soft cotton sleep set", "Light pajama pants", "Cozy socks"],
                  "Dark": ["Black silk pajama set", "Dark gray fleece pants", "Comfortable slippers"]
              },
              "Autumn": {
                  "Light": ["Cotton sleep shorts", "Long-sleeve t-shirt", "Flannel slippers"],
                  "Medium": ["Cozy fleece pajamas", "Thermal sleep pants", "Wool socks"],
                  "Dark": ["Dark navy pajama set", "Black fleece sleep shirt", "Wool slippers"]
              }
          }
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

        self.app = Flask(__name__)  # Membuat aplikasi Flask
        self.model_analyzer = ModelAnalyzer(
            seasonal_model_path='models/seasonal_color_model_improved.h5',
            skintone_model_path='models/skintone_model.h5'
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
          "x-rapidapi-host": self.RAPIDAPI_HOST
      }

      try:
          # Mengirim permintaan GET ke API Amazon
          response = requests.get(self.RAPIDAPI_URL, headers=headers, params=querystring)

          # Memeriksa jika ada rate-limiting (kode status 429)
          if response.status_code == 429:
              logger.warning(f"Rate limit hit for query: {query}. Retrying after 5 seconds.")
              time.sleep(5)  # Menunggu 5 detik sebelum mencoba ulang
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

                image_file = request.files['image'].read()

                # Default to 'streetwear' if not provided
                clothing_type = request.form.get('clothing_type', 'streetwear').lower()

                # Validate clothing type
                valid_clothing_types = ['formal', 'wedding', 'streetwear', 'pajamas']
                if clothing_type not in valid_clothing_types:
                    clothing_type = 'streetwear'  # Default if invalid type provided

                try:
                    # Predict color and style
                    color_prediction = self.model_analyzer.predict(image_file)

                    # Get outfit recommendations
                    outfit_recommendations = self.model_analyzer.predict_outfit(
                        color_prediction['seasonal_color_label'],
                        color_prediction['skin_tone_label'],
                        clothing_type
                    )

                    # Initialize amazon_products as an empty list
                    amazon_products = []
                    for item in outfit_recommendations:
                        # Log each item being searched on Amazon
                        logger.info(f"Searching for Amazon products with query: {item}")
                        products = self.search_amazon_products(item, page_size=3)  # Get only 3 products
                        # Log the results
                        logger.info(f"Found {len(products)} products for query: {item}")
                        
                        # If products are found, add them to the amazon_products list
                        if products:
                            amazon_products.extend(products)

                    # If no products found, log it and return an empty list
                    if not amazon_products:
                        logger.warning("No Amazon products found for any of the recommendations.")
                    
                    # Log the final list of products being returned
                    logger.info(f"Returning {len(amazon_products)} products.")

                    # Ensure only 3 products are returned
                    amazon_products = amazon_products[:3]  # Limit to the first 3 products

                    return jsonify({
                        **color_prediction,
                        "outfit_recommendations": outfit_recommendations,
                        "amazon_products": amazon_products
                    }), 200

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

    def run(self, debug=True, host='0.0.0.0', port=5000):
        """
        Menjalankan aplikasi Flask di server lokal.
        """
        self.app.run(debug=debug, host=host, port=port)

# Menjalankan aplikasi ketika file dijalankan langsung
if __name__ == '__main__':
    try:
        color_analysis_app = ColorAnalysisApp()
        color_analysis_app.run()
    except Exception as startup_error:
        logger.critical(f"Gagal menjalankan aplikasi: {startup_error}")
        print(f"Startup Error: {startup_error}")
