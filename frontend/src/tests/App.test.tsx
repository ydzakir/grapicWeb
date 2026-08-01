import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from '../App';

describe('App Shell Component', () => {
  it('redirects unauthenticated user to Login Page', () => {
    render(<App />);
    // Unauthenticated users see the Login Page (not the Navbar)
    expect(screen.getByText(/enterprise infrastructure monitoring/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });
});
