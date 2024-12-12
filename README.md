# SmartFit Color Analysis API by Cloud Computing Team 🎨👗

## Project Overview 📖
SmartFit is an innovative machine learning-powered application designed to provide personalized color analysis and style recommendations. This API serves as the core backend service, leveraging advanced machine learning models to help users discover their ideal color palette and outfit recommendations.

## Cloud Computing Architecture 🏗️
![image](https://github.com/user-attachments/assets/eab3d77f-9e97-4c10-84de-5815c295b7d4)

### Architecture Components
- **Google Cloud Platform**: Provides the core infrastructure
- **Vertex AI**: Machine Learning model deployment
- **App Engine**: Hosting and scaling backend services
- **Firebase**: User authentication and data storage
- **Container Registry**: Docker image management

## Team 👥
### Cloud Computing Specialists
- **Fachrio Raditya**
  - Institution: Institut Teknologi dan Bisnis Bina Sarana Global
  - Role: GCP Deployment Specialist
  - Responsibilities: 
    - Configuring Google Cloud Platform infrastructure
    - Managing deployment pipelines
    - Optimizing cloud resources
    - Ensuring scalability and performance of cloud services

- **Aurio Hendrianoko Rajaa**
  - Institution: Politeknik Negeri Jakarta
  - Role: Backend Services and API Development
  - Responsibilities:
    - Designing and implementing RESTful API endpoints
    - Integrating machine learning model predictions
    - Developing Firebase integration for user data management
    - Managing backend service logic for color analysis and style recommendations

## API Endpoint Details 🌈

### 1. Color Palette Prediction
- **Endpoint**: `/predict_color_palette`
- **HTTP Method**: POST
- **Full URL**: `https://your-app-domain.com/predict_color_palette`

#### Request Parameters
- `image`: Image file for color analysis (required)
  - **Type**: Multipart/form-data
  - **Accepted Formats**: JPEG, PNG
  - **Max Size**: Recommended < 5MB

#### Response Structure
```json
{
  "seasonal_color_label": "Summer",
  "skin_tone_label": "Light Warm",
  "color_palette": {
    "primary_colors": ["#PASTEL_BLUE", "#LIGHT_GREEN"],
    "accent_colors": ["#SOFT_PINK"]
  }
}
```

#### Possible Error Responses
- **400 Bad Request**: 
  - No image uploaded
  - Invalid image format
- **422 Unprocessable Entity**: 
  - Image processing error
- **500 Internal Server Error**: 
  - Unexpected server-side issues

### 2. Style Recommendation
- **Endpoint**: `/style_recommendation`
- **HTTP Method**: POST
- **Full URL**: `https://your-app-domain.com/style_recommendation`

#### Request Parameters
- `image`: Image file for style analysis (required)
- `uid`: Firebase User ID (required)
- `clothing_type`: Optional (default: streetwear)

#### Supported Clothing Types
- `formal-men`
- `formal-women`
- `wedding-men`
- `wedding-women`
- `streetwear-men`
- `streetwear-women`
- `pajamas-men`
- `pajamas-women`
- `vintage-men`
- `vintage-women`
- `casual-men`
- `casual-women`
- `sportswear-men`
- `sportswear-women`

#### Response Structure
```json
{
  "seasonal_color_label": "Autumn",
  "skin_tone_label": "Medium Olive",
  "color_palette": {
    "primary_colors": ["#RUST_RED", "#OLIVE_GREEN"],
    "accent_colors": ["#GOLDEN_YELLOW"]
  },
  "outfit_recommendations": [
    {
      "item": "Blazer",
      "description": "Elegant rust-colored blazer perfect for autumn tones"
    }
  ],
  "amazon_products": [
    {
      "product_name": "Classic Rust Blazer",
      "price": "$129.99",
      "url": "amazon-product-link"
    }
  ],
  "firebase_key": "unique_prediction_id"
}
```

### 3. Prediction History Management
#### List Prediction History
- **Endpoint**: `/get_prediction_history_list`
- **HTTP Method**: GET
- **Query Parameter**: `uid` (required)

#### Get Prediction Details
- **Endpoint**: `/get_prediction_history_detail`
- **HTTP Method**: GET
- **Query Parameters**: 
  - `uid` (required)
  - `prediction_key` (required)

#### Delete Prediction History
- **Endpoint**: `/delete_prediction_history`
- **HTTP Method**: POST
- **Form Parameters**:
  - `uid` (required)
  - `prediction_key` (required)

## Seasonal Color Analysis 🌈

### Summer Palette
- **Primary Mood**: Soft, light, refreshing
- **Color Characteristics**: Pastel blues, light greens, soft pinks
- **Style Recommendation**: Light, airy fabrics

### Winter Palette
- **Primary Mood**: Bold, sophisticated, deep
- **Color Characteristics**: Navy, black, deep grays
- **Style Recommendation**: Structured, sharp designs

### Spring Palette
- **Primary Mood**: Vibrant, renewing, hopeful
- **Color Characteristics**: Bright yellows, soft greens, light pinks
- **Style Recommendation**: Layered, adaptable clothing

### Autumn Palette
- **Primary Mood**: Warm, rich, mature
- **Color Characteristics**: Rust, olive green, golden tones
- **Style Recommendation**: Textured, earthy designs

## Technologies Stack 🛠️
- **Backend**: Python, Flask
- **Machine Learning**: TensorFlow
- **Cloud**: Google Cloud Platform (GCP)
- **Authentication**: Firebase
- **Database**: Firebase Realtime Database
