import { useState } from 'react';
import { Switch } from './Switch';

/**
 * SwitchDemo component that demonstrates the usage of our Switch component
 */
export function SwitchDemo() {
  // State for different switch examples
  const [basicEnabled, setBasicEnabled] = useState(false);
  const [withLabelEnabled, setWithLabelEnabled] = useState(true);
  const [withDescriptionEnabled, setWithDescriptionEnabled] = useState(false);
  const [disabledEnabled, setDisabledEnabled] = useState(true);
  const [disabledOffEnabled, setDisabledOffEnabled] = useState(false);
  const [formEnabled, setFormEnabled] = useState(false);
  const [customValueEnabled, setCustomValueEnabled] = useState(false);
  const [passiveLabelEnabled, setPassiveLabelEnabled] = useState(false);

  // Size examples
  const [smallEnabled, setSmallEnabled] = useState(false);
  const [mediumEnabled, setMediumEnabled] = useState(true);
  const [largeEnabled, setLargeEnabled] = useState(false);

  return (
    <div className="space-y-8 p-6">
      {/* Basic Switch */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Basic Switch</h2>
        <div className="flex items-center space-x-4">
          <Switch checked={basicEnabled} onChange={setBasicEnabled} />
          <span className="text-sm text-gray-500">
            State: {basicEnabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>
      </section>

      {/* Switch with Label */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Switch with Label</h2>
        <div className="space-y-4">
          <Switch
            checked={withLabelEnabled}
            onChange={setWithLabelEnabled}
            label="Enable notifications"
          />
        </div>
      </section>

      {/* Switch with Description */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Switch with Description</h2>
        <div className="space-y-4">
          <Switch
            checked={withDescriptionEnabled}
            onChange={setWithDescriptionEnabled}
            label="Developer mode"
            description="Enable advanced features for developers. This may include experimental features."
          />
        </div>
      </section>

      {/* Disabled Switches */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Disabled Switches</h2>
        <div className="space-y-4">
          <Switch
            checked={disabledEnabled}
            onChange={setDisabledEnabled}
            label="Read-only setting (on)"
            disabled
          />

          <Switch
            checked={disabledOffEnabled}
            onChange={setDisabledOffEnabled}
            label="Read-only setting (off)"
            disabled
          />
        </div>
      </section>

      {/* Form Integration */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Form Integration</h2>
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.currentTarget);
            console.log('Form data:', Object.fromEntries(formData.entries()));
          }}
        >
          <Switch
            checked={formEnabled}
            onChange={setFormEnabled}
            label="Accept terms and conditions"
            name="terms"
          />

          <Switch
            checked={customValueEnabled}
            onChange={setCustomValueEnabled}
            label="Subscribe to newsletter"
            name="newsletter"
            value="subscribe"
          />

          <button
            type="submit"
            className="mt-2 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none"
          >
            Submit
          </button>
        </form>
      </section>

      {/* Passive Label */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Passive Label</h2>
        <div className="space-y-4">
          <Switch
            checked={passiveLabelEnabled}
            onChange={setPassiveLabelEnabled}
            label="Label doesn't toggle switch"
            labelClickable={false}
          />
        </div>
      </section>

      {/* Different Sizes */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Different Sizes</h2>
        <div className="space-y-4">
          <div className="flex items-center space-x-4">
            <Switch
              checked={smallEnabled}
              onChange={setSmallEnabled}
              size="sm"
            />
            <span className="text-sm">Small</span>
          </div>

          <div className="flex items-center space-x-4">
            <Switch
              checked={mediumEnabled}
              onChange={setMediumEnabled}
              size="md"
            />
            <span className="text-sm">Medium (default)</span>
          </div>

          <div className="flex items-center space-x-4">
            <Switch
              checked={largeEnabled}
              onChange={setLargeEnabled}
              size="lg"
            />
            <span className="text-sm">Large</span>
          </div>
        </div>
      </section>
    </div>
  );
}
