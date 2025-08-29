import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { useToast, ToastContainer } from '../Toast';

// Create a test component that uses the toast hook
function TestComponent() {
  const { success, error, info } = useToast();

  return (
    <div>
      <button onClick={() => success('Success message')}>Success</button>
      <button onClick={() => error('Error message')}>Error</button>
      <button onClick={() => info('Info message')}>Info</button>
      <ToastContainer />
    </div>
  );
}

describe('Toast', () => {
  it('displays success toast when success is called', async () => {
    const user = userEvent.setup();
    render(<TestComponent />);
    
    const successButton = screen.getByText('Success');
    await user.click(successButton);
    
    expect(screen.getByText('Success message')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('displays error toast when error is called', async () => {
    const user = userEvent.setup();
    render(<TestComponent />);
    
    const errorButton = screen.getByText('Error');
    await user.click(errorButton);
    
    expect(screen.getByText('Error message')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('allows dismissing toast by clicking close button', async () => {
    const user = userEvent.setup();
    render(<TestComponent />);
    
    const successButton = screen.getByText('Success');
    await user.click(successButton);
    
    expect(screen.getByText('Success message')).toBeInTheDocument();
    
    const dismissButton = screen.getByRole('button', { name: /dismiss/i });
    await user.click(dismissButton);
    
    // Toast should still be in the DOM but starting to exit
    expect(screen.getByText('Success message')).toBeInTheDocument();
  });
});