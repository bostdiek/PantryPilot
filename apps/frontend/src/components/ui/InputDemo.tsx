import { useState, type FC } from 'react';
import { Input } from './Input';
import CalendarIcon from './icons/calendar.svg?react';
import SearchIcon from './icons/search.svg?react';
import UserIcon from './icons/user.svg?react';
import XIcon from './icons/x.svg?react';

/**
 * Demo component for Input
 * Displays various input variants, sizes, and states
 */
export const InputDemo: FC = () => {
  const [textValue, setTextValue] = useState('');
  const [emailValue, setEmailValue] = useState('');
  const [passwordValue, setPasswordValue] = useState('');
  const [searchValue, setSearchValue] = useState('');

  return (
    <div className="space-y-8">
      {/* Standard Input Types */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">Input Types</h3>
        <div className="max-w-md space-y-4">
          <Input
            label="Text Input"
            value={textValue}
            onChange={setTextValue}
            placeholder="Enter some text"
            helperText="This is a standard text input"
          />

          <Input
            label="Email Input"
            type="email"
            value={emailValue}
            onChange={setEmailValue}
            placeholder="you@example.com"
            helperText="Enter your email address"
          />

          <Input
            label="Password Input"
            type="password"
            value={passwordValue}
            onChange={setPasswordValue}
            placeholder="Enter your password"
            helperText="Must be at least 8 characters"
          />

          <Input
            label="Search Input"
            type="search"
            value={searchValue}
            onChange={setSearchValue}
            placeholder="Search..."
            rightIconSvg={SearchIcon}
          />
        </div>
      </div>

      {/* Input Sizes */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">Sizes</h3>
        <div className="max-w-md space-y-4">
          <Input
            label="Small Input"
            size="sm"
            value=""
            onChange={() => {}}
            placeholder="Small input"
          />

          <Input
            label="Medium Input (Default)"
            size="md"
            value=""
            onChange={() => {}}
            placeholder="Medium input"
          />

          <Input
            label="Large Input"
            size="lg"
            value=""
            onChange={() => {}}
            placeholder="Large input"
          />
        </div>
      </div>

      {/* Input Variants */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">Variants</h3>
        <div className="max-w-md space-y-4">
          <Input
            label="Outline Variant (Default)"
            variant="outline"
            value=""
            onChange={() => {}}
            placeholder="Outline input"
          />

          <Input
            label="Filled Variant"
            variant="filled"
            value=""
            onChange={() => {}}
            placeholder="Filled input"
          />

          <Input
            label="Unstyled Variant"
            variant="unstyled"
            value=""
            onChange={() => {}}
            placeholder="Unstyled input"
          />
        </div>
      </div>

      {/* States */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">States</h3>
        <div className="max-w-md space-y-4">
          <Input
            label="Disabled Input"
            disabled
            value="Can't edit this"
            onChange={() => {}}
          />

          <Input
            label="With Error"
            value="Invalid value"
            onChange={() => {}}
            error="This field has an error"
          />

          <Input
            label="Required Field"
            required
            value=""
            onChange={() => {}}
            placeholder="This field is required"
          />
        </div>
      </div>

      {/* With Icons */}
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-gray-700">With Icons</h3>
        <div className="max-w-md space-y-4">
          <Input
            label="Left Icon"
            leftIconSvg={UserIcon}
            value=""
            onChange={() => {}}
            placeholder="Username"
          />

          <Input
            label="Right Icon"
            rightIconSvg={CalendarIcon}
            value=""
            onChange={() => {}}
            placeholder="Select date"
          />

          <Input
            label="Both Icons"
            leftIconSvg={SearchIcon}
            rightIconSvg={XIcon}
            value=""
            onChange={() => {}}
            placeholder="Search..."
          />
        </div>
      </div>
    </div>
  );
};
