import axios from "axios";

const configuredBase = process.env.REACT_APP_BACKEND_URL?.trim();
const API_BASE_URL = `${configuredBase || "http://localhost:8000"}/api`;

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { Accept: "application/json" },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
      error.userMessage = "The request timed out. Please try again.";
    } else if (!error.response) {
      error.userMessage = "Unable to reach the CricEdge API. Check your connection and try again.";
    } else if (error.response.status === 400 || error.response.status === 422) {
      error.userMessage = error.response.data?.detail || "The request was invalid.";
    } else if (error.response.status === 404) {
      error.userMessage = error.response.data?.detail || "The requested CricEdge resource was not found.";
    } else if (error.response.status === 429) {
      error.userMessage = "Too many requests. Please wait a moment and try again.";
    } else if (error.response.status >= 500) {
      error.userMessage = "The CricEdge service is temporarily unavailable. Please try again shortly.";
    }
    return Promise.reject(error);
  }
);

export const encodePathSegment = (value) => encodeURIComponent(String(value ?? ""));

export default api;
