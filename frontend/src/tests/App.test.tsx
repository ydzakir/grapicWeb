import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from '../App';

describe('App Shell Component', () => {
  it('redirects unauthenticated user to Login Page', () => {
    render(<App />);
    expect(screen.getByText('InfraTopology MVP')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });
});
