import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000/api';

// Retry configuration
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // ms

/**
 * Centralized Axios instance with error handling, retries, and validation.
 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Retry interceptor: exponential backoff for transient failures
 */
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config;

    // Don't retry if no config or already retried
    if (!config || config.__retryCount === undefined) {
      config.__retryCount = 0;
    }

    // Only retry on network errors or 5xx status codes
    const shouldRetry =
      (error.response?.status >= 500 || !error.response) &&
      config.__retryCount < MAX_RETRIES;

    if (shouldRetry) {
      config.__retryCount += 1;
      const delay = RETRY_DELAY * Math.pow(2, config.__retryCount - 1);
      await new Promise((resolve) => setTimeout(resolve, delay));
      return apiClient(config);
    }

    return Promise.reject(formatError(error));
  }
);

/**
 * Format errors into a consistent shape for the app
 */
export function formatError(error) {
  if (error.response) {
    // Server responded with error status
    return {
      status: error.response.status,
      message: error.response.data?.detail || error.response.statusText,
      type: 'api_error',
      data: error.response.data,
    };
  }
  if (error.request) {
    // Request made but no response
    return {
      status: null,
      message: 'No response from server. Check your connection.',
      type: 'network_error',
      data: error.request,
    };
  }
  // Error during request setup
  return {
    status: null,
    message: error.message || 'An unexpected error occurred',
    type: 'unknown_error',
    data: error,
  };
}

/**
 * Fixtures API
 */
export const fixturesAPI = {
  /**
   * Get all fixtures, optionally filtered by format
   * @param {string} format - Optional: T20, ODI, Test, Hundred, or 'ALL'
   */
  getFixtures: async (format = null) => {
    try {
      const params = format && format !== 'ALL' ? { format } : {};
      const response = await apiClient.get('/fixtures', { params });
      return {
        data: response.data,
        error: null,
      };
    } catch (error) {
      return {
        data: null,
        error: formatError(error),
      };
    }
  },

  /**
   * Get supported formats and their counts
   */
  getFormats: async () => {
    try {
      const response = await apiClient.get('/fixtures/formats');
      return {
        data: response.data,
        error: null,
      };
    } catch (error) {
      return {
        data: null,
        error: formatError(error),
      };
    }
  },

  /**
   * Get a single fixture by ID
   */
  getFixtureById: async (fixtureId) => {
    if (!fixtureId) throw new Error('fixtureId is required');
    try {
      const response = await apiClient.get(`/fixtures/${fixtureId}`);
      return {
        data: response.data,
        error: null,
      };
    } catch (error) {
      return {
        data: null,
        error: formatError(error),
      };
    }
  },

  /**
   * Get predictions and markets for a fixture
   */
  getFixturePredictions: async (fixtureId) => {
    if (!fixtureId) throw new Error('fixtureId is required');
    try {
      const response = await apiClient.get(`/fixtures/${fixtureId}/predictions`);
      return {
        data: response.data,
        error: null,
      };
    } catch (error) {
      return {
        data: null,
        error: formatError(error),
      };
    }
  },
};

/**
 * Health & Model API
 */
export const healthAPI = {
  /**
   * Check API health and model status
   */
  getHealth: async () => {
    try {
      const response = await apiClient.get('/health');
      return {
        data: response.data,
        error: null,
      };
    } catch (error) {
      return {
        data: null,
        error: formatError(error),
      };
    }
  },
};

export default apiClient;
