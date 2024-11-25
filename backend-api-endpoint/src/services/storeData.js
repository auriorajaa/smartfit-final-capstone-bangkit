const admin = require('firebase-admin');

const storeUserData = async (userData) => {
  try {
    const db = admin.database();
    const userRef = db.ref(`users/${userData.uid}`);

    const userDataToStore = {
      email: userData.email,
      displayName: userData.displayName || "",
      photoURL: userData.photoURL || "",
      createdAt: admin.database.ServerValue.TIMESTAMP,
      updatedAt: admin.database.ServerValue.TIMESTAMP,
      lastLogin: admin.database.ServerValue.TIMESTAMP,
      provider: userData.providerData.length > 0 ? userData.providerData[0].providerId : "",
      isNewUser: userData.metadata.creationTime === userData.metadata.lastSignInTime,
    };

    await userRef.set(userDataToStore);
    return {
      status: 'success',
      message: 'User data stored successfully',
      data: userDataToStore,
    };
  } catch (error) {
    console.error("Error storing user data:", error);
    throw new Error(`Failed to store user data: ${error.message}`);
  }
};

module.exports = { storeUserData };
