// src/server/handlers.js
const admin = require('firebase-admin');
const { storeUserData } = require('../services/storeData');
const InputError = require('../exceptions/InputError');

const registerHandler = async (request, h) => {
  try {
    const { email, password } = request.payload;

    if (!email || !password) {
      throw new InputError('Email and password are required');
    }

    const userRecord = await admin.auth().createUser({
      email,
      password,
    });

    const userData = {
      uid: userRecord.uid,
      email: userRecord.email,
      displayName: userRecord.displayName || "",
      photoURL: userRecord.photoURL || "",
      providerData: userRecord.providerData || [],
      metadata: userRecord.metadata,
    };

    const storedData = await storeUserData(userData);

    return h.response({
      status: 'success',
      message: 'User registered successfully',
      data: storedData,
    }).code(201);
  } catch (error) {
    console.error('Error during registration:', error);
    return h.response({
      status: 'error',
      message: error.message,
    }).code(500);
  }
};


const googleSignInHandler = async (request, h) => {
  try {
    const { idToken } = request.payload;

    if (!idToken) {
      throw new InputError('ID Token is required');
    }

    const decodedToken = await admin.auth().verifyIdToken(idToken);
    const userRecord = await admin.auth().getUser(decodedToken.uid);
    const userData = await storeUserData(userRecord);

    return h.response({
      status: 'success',
      message: 'Google sign-in successful',
      data: userData,
    }).code(200);
  } catch (error) {
    console.error('Error during Google sign-in:', error);
    return h.response({
      status: 'error',
      message: error.message,
    }).code(500);
  }
};

module.exports = {
  registerHandler,
  googleSignInHandler,
};
