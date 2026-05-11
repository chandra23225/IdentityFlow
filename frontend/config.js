// Set this to your Render backend URL after deploying
// e.g. "https://identity-lifecycle-api.onrender.com"
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:5000'
  : 'https://identity-lifecycle-api.onrender.com';
