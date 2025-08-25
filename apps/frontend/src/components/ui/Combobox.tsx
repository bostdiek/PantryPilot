import { Combobox as HeadlessCombobox, Transition } from '@headlessui/react';
import { Fragment, useState } from 'react';
import clsx from 'clsx';
import { Icon } from './Icon';

// Import the SVG components
import CheckIcon from './icons/check.svg?react';
import ChevronUpDownIcon from './icons/chevron-up-down.svg?react';

export type ComboboxOption = {
  id: string;
  name: string;
};

type ComboboxProps = {
  options: ComboboxOption[];
  value: ComboboxOption;
  onChange: (value: ComboboxOption) => void;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  /**
   * Function to filter options based on query
   * If not provided, a default case-insensitive filter is used
   */
  filterFunction?: (
    query: string,
    options: ComboboxOption[]
  ) => ComboboxOption[];
};

/**
 * Combobox component based on Headless UI's Combobox
 *
 * This provides a searchable dropdown with proper accessibility
 *
 * @example
 * ```tsx
 * const options = [
 *   { id: 'apple', name: 'Apple' },
 *   { id: 'banana', name: 'Banana' },
 *   { id: 'orange', name: 'Orange' },
 * ];
 *
 * const [selected, setSelected] = useState(options[0]);
 *
 * <Combobox
 *   options={options}
 *   value={selected}
 *   onChange={setSelected}
 *   label="Fruit"
 * />
 * ```
 */
export function Combobox({
  options,
  value,
  onChange,
  label,
  placeholder = 'Select an option...',
  disabled = false,
  className = '',
  filterFunction,
}: ComboboxProps) {
  const [query, setQuery] = useState('');

  // Default filtering function
  const defaultFilterFunction = (query: string, options: ComboboxOption[]) => {
    return query === ''
      ? options
      : options.filter((option) => {
          return option.name.toLowerCase().includes(query.toLowerCase());
        });
  };

  // Use custom filter function if provided, otherwise use default
  const filteredOptions = (filterFunction || defaultFilterFunction)(
    query,
    options
  );

  return (
    <div className={className}>
      <HeadlessCombobox value={value} onChange={onChange} disabled={disabled}>
        {() => (
          <>
            {label && (
              <HeadlessCombobox.Label className="mb-1 block text-sm font-medium text-gray-700">
                {label}
              </HeadlessCombobox.Label>
            )}
            <div className="relative">
              <div className="relative w-full cursor-default overflow-hidden rounded-md border border-gray-300 bg-white text-left shadow-sm focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500">
                <HeadlessCombobox.Input
                  className="w-full border-none py-2 pr-10 pl-3 text-sm leading-5 text-gray-900 focus:ring-0 focus:outline-none"
                  displayValue={(option: ComboboxOption) => option.name}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={placeholder}
                />
                <HeadlessCombobox.Button className="absolute inset-y-0 right-0 flex items-center pr-2">
                  <Icon
                    svg={ChevronUpDownIcon}
                    className="h-5 w-5 text-gray-400"
                    aria-hidden="true"
                  />
                </HeadlessCombobox.Button>
              </div>
              <Transition
                as={Fragment}
                leave="transition ease-in duration-100"
                leaveFrom="opacity-100"
                leaveTo="opacity-0"
                afterLeave={() => setQuery('')}
              >
                <HeadlessCombobox.Options className="ring-opacity-5 absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black focus:outline-none sm:text-sm">
                  {filteredOptions.length === 0 && query !== '' ? (
                    <div className="relative cursor-default px-4 py-2 text-gray-700 select-none">
                      Nothing found.
                    </div>
                  ) : (
                    filteredOptions.map((option) => (
                      <HeadlessCombobox.Option
                        key={option.id}
                        className={({ active }) =>
                          `relative cursor-default py-2 pr-4 pl-10 select-none ${
                            active
                              ? 'bg-blue-100 text-blue-900'
                              : 'text-gray-900'
                          }`
                        }
                        value={option}
                      >
                        {({ selected, active }) => (
                          <>
                            <span
                              className={clsx(
                                'block truncate',
                                selected ? 'font-medium' : 'font-normal'
                              )}
                            >
                              {option.name}
                            </span>
                            {selected ? (
                              <span
                                className={clsx(
                                  'absolute inset-y-0 left-0 flex items-center pl-3',
                                  active ? 'text-blue-600' : 'text-blue-600'
                                )}
                              >
                                <Icon
                                  svg={CheckIcon}
                                  className="h-5 w-5"
                                  aria-hidden="true"
                                />
                              </span>
                            ) : null}
                          </>
                        )}
                      </HeadlessCombobox.Option>
                    ))
                  )}
                </HeadlessCombobox.Options>
              </Transition>
            </div>
          </>
        )}
      </HeadlessCombobox>
    </div>
  );
}
