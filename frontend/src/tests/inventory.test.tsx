import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../context/AuthContext';
import { InventoryPage } from '../pages/InventoryPage';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('InventoryPage Component', () => {
  it('renders inventory header, search box, and filter controls', () => {
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <InventoryPage />
        </AuthProvider>
      </QueryClientProvider>
    );

    expect(screen.getByText(/infrastructure inventory/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/search by name, ip, or os/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/all node types/i)).toBeInTheDocument();
  });
});
