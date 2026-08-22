import axios from "axios";

const API_BASE_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    Accept: "application/json",
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === "ECONNABORTED") {
      error.userMessage = "The request timed out. Please try again.";
    } else if (!error.response) {
      error.userMessage = "Unable to reach the CricEdge API.";
    } else if (error.response.status >= 500) {
      error.userMessage = "The CricEdge service is temporarily unavailable.";
    }
    return Promise.reject(error);
  }
);

export default api;
