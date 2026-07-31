import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { LoginPage } from '../pages/LoginPage';

const TestAuthConsumer = () => {
  const { user, isAuthenticated, isAdmin } = useAuth();
  return (
    <div>
      <span data-testid="auth-status">{isAuthenticated ? 'authenticated' : 'anonymous'}</span>
      <span data-testid="user-role">{user?.role || 'none'}</span>
      <span data-testid="is-admin">{isAdmin ? 'yes' : 'no'}</span>
    </div>
  );
};

describe('AuthContext and LoginPage', () => {
  it('renders login form with username and password inputs', () => {
    render(
      <AuthProvider>
        <BrowserRouter>
          <LoginPage />
        </BrowserRouter>
      </AuthProvider>
    );

    expect(screen.getByLabelText(/username or email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('provides default anonymous auth state', () => {
    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status')).toHaveTextContent('anonymous');
    expect(screen.getByTestId('user-role')).toHaveTextContent('none');
    expect(screen.getByTestId('is-admin')).toHaveTextContent('no');
  });
});
