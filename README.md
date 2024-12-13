# SmartFit Machine Learning Repository

## 📌 Project Overview
**SmartFit** is an innovative machine learning-powered application designed to provide personalized color analysis and style recommendations.

---

## 👥 Team Members

### 1. **Hawarizmi Ummul Adzkia**  
- **ID**: M267B4KX1751  
- **University**: Universitas Muhammadiyah Sukabumi  

### 2. **Kanaya Defitra Prasetyo Putri**  
- **ID**: M180B4KX2134  
- **University**: Universitas Airlangga  

### 3. **Regi Aprilian**  
- **ID**: M200B4KY3731  
- **University**: Universitas Diponegoro  

---

## Model Summary

![Screenshot 2024-12-13 104108](https://github.com/user-attachments/assets/64ab0aaa-4a9d-4b14-b077-5908048fb161)

The image shows a summary of a sequential machine learning model, specifically a Convolutional Neural Network (CNN). The summary includes details about each layer in the model, their types, output shapes, and the number of parameters.

Here is a detailed breakdown of the model summary:

1. **Layer (type)**:
   - **conv2d (Conv2D)**: This is a 2D convolutional layer.
   - **max_pooling2d (MaxPooling2D)**: This is a 2D max pooling layer.
   - **conv2d_1 (Conv2D)**: This is another 2D convolutional layer.
   - **max_pooling2d_1 (MaxPooling2D)**: This is another 2D max pooling layer.
   - **flatten (Flatten)**: This layer flattens the input.
   - **dense (Dense)**: This is a dense (fully connected) layer.
   - **dropout (Dropout)**: This layer applies dropout to prevent overfitting.
   - **dense_1 (Dense)**: This is another dense (fully connected) layer.

2. **Output Shape**:
   - **conv2d**: (None, 126, 126, 16)
   - **max_pooling2d**: (None, 63, 63, 16)
   - **conv2d_1**: (None, 61, 61, 32)
   - **max_pooling2d_1**: (None, 30, 30, 32)
   - **flatten**: (None, 28800)
   - **dense**: (None, 64)
   - **dropout**: (None, 64)
   - **dense_1**: (None, 4)

3. **Param #**:
   - **conv2d**: 448
   - **max_pooling2d**: 0
   - **conv2d_1**: 4,640
   - **max_pooling2d_1**: 0
   - **flatten**: 0
   - **dense**: 1,843,264
   - **dropout**: 0
   - **dense_1**: 260

4. **Total params**: 1,848,612 (7.05 MB)
5. **Trainable params**: 1,848,612 (7.05 MB)
6. **Non-trainable params**: 0 (0.00 B)

---

## Training and Validation Result

![Screenshot 2024-12-13 104420](https://github.com/user-attachments/assets/cbb4f6dd-878b-40eb-92e8-88d26e52b750)
![Screenshot 2024-12-13 104435](https://github.com/user-attachments/assets/cfd6dc0e-41e0-4e65-b624-5b447ab9e66c)
![Screenshot 2024-12-13 104459](https://github.com/user-attachments/assets/df8e585a-56c7-4c51-943c-bb63c973dc0d)

---

## 🚀 Key Features
- **Advanced Predictive Modeling**: Leverage machine learning algorithms to predict outfit and color palette based on skin tone.
- **Personalized Recommendations**: Get customized outfit and color palette suggestions based on data.

---

Thank you for visiting the SmartFit repository. We are excited to share our work with you and make technology more accessible for everyone!
