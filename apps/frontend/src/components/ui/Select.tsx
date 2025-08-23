import { Listbox, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { Icon } from './Icon';
import CheckIcon from './icons/check.svg?react';
import ChevronUpDown from './icons/chevron-up-down.svg?react';

export type SelectOption = {
  id: string;
  name: string;
};

type SelectProps = {
  options: SelectOption[];
  value: SelectOption;
  onChange: (value: SelectOption) => void;
  label?: string;
  disabled?: boolean;
  className?: string;
};

/**
 * Select component based on Headless UI's Listbox
 *
 * This provides a custom styled select dropdown with proper accessibility
 *
 * @example
 * ```tsx
 * const options = [
 *   { id: 'easy', name: 'Easy' },
 *   { id: 'medium', name: 'Medium' },
 *   { id: 'hard', name: 'Hard' },
 * ];
 *
 * const [selected, setSelected] = useState(options[0]);
 *
 * <Select
 *   options={options}
 *   value={selected}
 *   onChange={setSelected}
 *   label="Difficulty"
 * />
 * ```
 */
export function Select({
  options,
  value,
  onChange,
  label,
  disabled = false,
  className = '',
}: SelectProps) {
  return (
    <div className={className}>
      <Listbox value={value} onChange={onChange} disabled={disabled}>
        {({ open }) => (
          <>
            {label && (
              <Listbox.Label className="mb-1 block text-sm font-medium text-gray-700">
                {label}
              </Listbox.Label>
            )}
            <div className="relative">
              <Listbox.Button className="relative w-full cursor-default rounded-md border border-gray-300 bg-white py-2 pr-10 pl-3 text-left shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none sm:text-sm">
                <span className="block truncate">{value.name}</span>
                <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                  <Icon svg={ChevronUpDown} className="h-5 w-5 text-gray-400" />
                </span>
              </Listbox.Button>

              <Transition
                show={open}
                as={Fragment}
                leave="transition ease-in duration-100"
                leaveFrom="opacity-100"
                leaveTo="opacity-0"
              >
                <Listbox.Options className="ring-opacity-5 absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black focus:outline-none sm:text-sm">
                  {options.map((option) => (
                    <Listbox.Option
                      key={option.id}
                      className={({ active }) =>
                        `relative cursor-default py-2 pr-4 pl-10 select-none ${
                          active ? 'bg-blue-100 text-blue-900' : 'text-gray-900'
                        }`
                      }
                      value={option}
                    >
                      {({ selected, active }) => (
                        <>
                          <span
                            className={`block truncate ${
                              selected ? 'font-medium' : 'font-normal'
                            }`}
                          >
                            {option.name}
                          </span>
                          {selected ? (
                            <span
                              className={`absolute inset-y-0 left-0 flex items-center pl-3 ${
                                active ? 'text-blue-600' : 'text-blue-600'
                              }`}
                            >
                              <Icon
                                svg={CheckIcon}
                                className="h-5 w-5 text-blue-600"
                              />
                            </span>
                          ) : null}
                        </>
                      )}
                    </Listbox.Option>
                  ))}
                </Listbox.Options>
              </Transition>
            </div>
          </>
        )}
      </Listbox>
    </div>
  );
}
