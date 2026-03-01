/**
 * Authentication Service
 * 
 * Integrates Firebase authentication with MongoDB backend
 * Handles user registration, login, and role management
 */

const API_URL = 'http://localhost:5000/api/auth';

export interface RegisterUserData {
  firebase_uid: string;
  email: string;
  full_name: string;
  role: 'hr' | 'employee';
  company?: string;
  phone?: string;
}

export interface LoginUserData {
  firebase_uid: string;
  email: string;
}

export interface UserResponse {
  success: boolean;
  user?: {
    _id: string;
    email: string;
    full_name: string;
    role: 'hr' | 'employee';
    company?: string;
    phone?: string;
    firebase_uid: string;
    created_at: string;
    last_login: string;
    is_active: boolean;
  };
  message?: string;
  error?: string;
}

/**
 * Register a new user with role selection
 * 
 * @param firebaseUid - Firebase user ID
 * @param email - User email
 * @param fullName - User's full name
 * @param role - User role ('hr' or 'employee')
 * @param company - Company name (optional, for HR users)
 * @param phone - Phone number (optional)
 * @returns Promise with user data
 */
export const registerUser = async (
  firebaseUid: string,
  email: string,
  fullName: string,
  role: 'hr' | 'employee',
  company: string | null = null,
  phone: string | null = null
): Promise<UserResponse> => {
  try {
    const response = await fetch(`${API_URL}/register`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        firebase_uid: firebaseUid,
        email,
        full_name: fullName,
        role,
        company,
        phone
      })
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Registration failed');
    }

    return data;
  } catch (error) {
    console.error('Registration error:', error);
    throw error;
  }
};

/**
 * Login user and sync with MongoDB
 * 
 * @param firebaseUid - Firebase user ID
 * @param email - User email
 * @returns Promise with user data
 */
export const loginUser = async (
  firebaseUid: string,
  email: string
): Promise<UserResponse> => {
  try {
    const response = await fetch(`${API_URL}/login`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        firebase_uid: firebaseUid,
        email
      })
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Login failed');
    }

    return data;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

/**
 * Get user by Firebase UID
 * 
 * @param firebaseUid - Firebase user ID
 * @returns Promise with user data
 */
export const getUserByFirebaseUid = async (
  firebaseUid: string
): Promise<UserResponse> => {
  try {
    const response = await fetch(`${API_URL}/user/${firebaseUid}`, {
      method: 'GET',
      headers: { 
        'Content-Type': 'application/json',
      }
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to fetch user');
    }

    return data;
  } catch (error) {
    console.error('Get user error:', error);
    throw error;
  }
};

/**
 * Update user role
 * 
 * @param firebaseUid - Firebase user ID
 * @param role - New role ('hr' or 'employee')
 * @returns Promise with success status
 */
export const updateUserRole = async (
  firebaseUid: string,
  role: 'hr' | 'employee'
): Promise<{ success: boolean; message?: string; error?: string }> => {
  try {
    const response = await fetch(`${API_URL}/user/${firebaseUid}/role`, {
      method: 'PUT',
      headers: { 
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ role })
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to update role');
    }

    return data;
  } catch (error) {
    console.error('Update role error:', error);
    throw error;
  }
};

/**
 * Get all users by role
 * 
 * @param role - User role to filter by
 * @returns Promise with list of users
 */
export const getUsersByRole = async (
  role: 'hr' | 'employee' | 'admin'
): Promise<{ success: boolean; users?: any[]; count?: number; error?: string }> => {
  try {
    const response = await fetch(`${API_URL}/users/role/${role}`, {
      method: 'GET',
      headers: { 
        'Content-Type': 'application/json',
      }
    });

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to fetch users');
    }

    return data;
  } catch (error) {
    console.error('Get users by role error:', error);
    throw error;
  }
};
