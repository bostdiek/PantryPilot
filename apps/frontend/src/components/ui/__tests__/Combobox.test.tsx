import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Combobox, type ComboboxOption } from '../Combobox';

const mockOptions: ComboboxOption[] = [
  { id: '1', name: 'Option 1' },
  { id: '2', name: 'Option 2' },
  { id: '3', name: 'Option 3' },
];

describe('Combobox', () => {
  it('handles null value in displayValue without errors', () => {
    const mockOnChange = vi.fn();

    render(
      <Combobox
        options={mockOptions}
        value={null}
        onChange={mockOnChange}
        placeholder="Select an option"
      />
    );

    // Verify the input is rendered and shows placeholder when value is null
    const input = screen.getByPlaceholderText('Select an option');
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue(''); // displayValue should return empty string for null
  });

  it('displays selected option name when value is provided', () => {
    const mockOnChange = vi.fn();

    render(
      <Combobox
        options={mockOptions}
        value={mockOptions[0]}
        onChange={mockOnChange}
        placeholder="Select an option"
      />
    );

    const input = screen.getByDisplayValue('Option 1');
    expect(input).toBeInTheDocument();
  });

  it('renders with label when provided', () => {
    const mockOnChange = vi.fn();

    render(
      <Combobox
        options={mockOptions}
        value={null}
        onChange={mockOnChange}
        label="Choose Option"
      />
    );

    expect(screen.getByText('Choose Option')).toBeInTheDocument();
  });
});
