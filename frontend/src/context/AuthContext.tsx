import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types/api';
import { apiClient } from '../services/apiClient';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isOperator: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // The JWT is only required for the WebSocket upgrade (query token param).
  // REST API authentication is handled by the secure HttpOnly cookie, so the
  // token is kept in sessionStorage (ephemeral, tab-scoped) instead of
  // localStorage to reduce XSS persistence exposure.
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem('token'));
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });

  const login = (newToken: string, newUser: User) => {
    sessionStorage.setItem('token', newToken);
    localStorage.setItem('user', JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
  };

  const logout = () => {
    sessionStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  useEffect(() => {
    if (token && !user) {
      apiClient.get<User>('/auth/me')
        .then((fetchedUser) => {
          setUser(fetchedUser);
          localStorage.setItem('user', JSON.stringify(fetchedUser));
        })
        .catch(() => logout());
    }
  }, [token, user]);

  const isAdmin = user?.role === 'admin';
  const isOperator = user?.role === 'operator' || isAdmin;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        isAdmin,
        isOperator,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
