// routes.js
const { registerHandler, googleSignInHandler } = require('./handlers');

const routes = [
  {
    method: 'POST',
    path: '/register',
    handler: registerHandler,
  },
  {
    method: 'POST',
    path: '/auth/google',
    handler: googleSignInHandler,
  },
];

module.exports = routes;