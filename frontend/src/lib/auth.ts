/**
 * Authentication utilities.
 * 
 * Handles API key storage and retrieval from localStorage.
 * Uses X-API-Key header for authentication.
 */

const API_KEY_STORAGE = 'api_key';
const USER_KEY = 'user_data';

export interface UserData {
  email?: string;
  company_name?: string;
  api_key_masked?: string; // Last 4 chars for display
}

/**
 * Gets the stored API key.
 */
export const getApiKey = (): string | null => {
  try {
    console.log('Retrieving API key from localStorage');
    console.log('Current localStorage keys:', Object.keys(localStorage));
    console.log('API Key Value:', localStorage.getItem(API_KEY_STORAGE));
    return localStorage.getItem(API_KEY_STORAGE);

  } catch (error) {
    console.error('Error getting API key:', error);
    return null;
  }
};

/**
 * Sets the API key.
 */
export const setApiKey = (apiKey: string): void => {
  try {
    localStorage.setItem(API_KEY_STORAGE, apiKey);
    
    // Store masked version for display (last 4 chars)
    const masked = apiKey.length > 4 
      ? `sk-...${apiKey.slice(-4)}`
      : `sk-...${apiKey}`;
    
    setUserData({
      api_key_masked: masked,
    });
  } catch (error) {
    console.error('Error setting API key:', error);
  }
};

/**
 * Clears the stored API key and user data.
 */
export const clearApiKey = (): void => {
  try {
    localStorage.removeItem(API_KEY_STORAGE);
    localStorage.removeItem(USER_KEY);
  } catch (error) {
    console.error('Error clearing API key:', error);
  }
};

/**
 * Checks if user is authenticated (has API key).
 */
export const isAuthed = (): boolean => {
  return getApiKey() !== null;
};

/**
 * Gets stored user data.
 */
export const getUserData = (): UserData | null => {
  try {
    const data = localStorage.getItem(USER_KEY);
    return data ? JSON.parse(data) : null;
  } catch (error) {
    console.error('Error getting user data:', error);
    return null;
  }
};

/**
 * Sets user data.
 */
export const setUserData = (userData: UserData): void => {
  try {
    const existing = getUserData() || {};
    localStorage.setItem(USER_KEY, JSON.stringify({ ...existing, ...userData }));
  } catch (error) {
    console.error('Error setting user data:', error);
  }
};

/**
 * Masks API key for display (shows last 4 characters).
 */
export const maskApiKey = (apiKey: string): string => {
  if (apiKey.length <= 4) {
    return `sk-...${apiKey}`;
  }
  return `sk-...${apiKey.slice(-4)}`;
};

