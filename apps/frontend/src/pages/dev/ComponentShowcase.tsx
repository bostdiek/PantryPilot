import { useState, type FC } from 'react';
import { LayoutDemo } from '../../components/layout/LayoutDemo';
import {
  ButtonDemo,
  CardDemo,
  ComboboxDemo,
  ContainerDemo,
  DialogDemo,
  DisclosureDemo,
  FeedbackDemo,
  IconDemo,
  InputDemo,
  SelectDemo,
  SwitchDemo,
  TabsDemo,
} from '../../components/ui';

/**
 * Component Showcase page for development
 * This page displays all UI components in a structured way for easy testing and review
 */
const ComponentShowcase: FC = () => {
  const [activeSection, setActiveSection] = useState<string>('buttons');

  // Define navigation items
  const navItems = [
    { id: 'buttons', label: 'Buttons' },
    { id: 'icons', label: 'Icons' },
    { id: 'inputs', label: 'Inputs' },
    { id: 'cards', label: 'Cards' },
    { id: 'containers', label: 'Containers' },
    // Add more as you create components
    { id: 'selects', label: 'Select Dropdowns' },
    { id: 'comboboxes', label: 'Comboboxes' },
    { id: 'dialogs', label: 'Dialogs' },
    { id: 'disclosures', label: 'Disclosures' },
    { id: 'tabs', label: 'Tabs' },
    { id: 'switches', label: 'Switches' },
    { id: 'layouts', label: 'Layouts' },
    { id: 'feedback', label: 'Feedback Components' },
  ];

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar navigation */}
      <aside className="w-64 flex-shrink-0 bg-white p-6 shadow-md">
        <h1 className="mb-6 text-xl font-bold text-blue-600">
          Smart Meal Planner UI
        </h1>
        <nav>
          <ul className="space-y-2">
            {navItems.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => setActiveSection(item.id)}
                  className={`w-full rounded-md px-4 py-2 text-left transition-colors ${
                    activeSection === item.id
                      ? 'bg-blue-100 font-medium text-blue-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      {/* Main content area */}
      <main className="flex-grow overflow-auto p-6">
        <div className="mx-auto max-w-4xl rounded-lg bg-white shadow-sm">
          {/* Buttons Section */}
          {activeSection === 'buttons' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">Buttons</h2>
                <p className="mt-1 text-gray-600">
                  Button components with different variants, sizes, and states
                </p>
              </div>
              <ButtonDemo />
            </section>
          )}

          {/* Icons Section */}
          {activeSection === 'icons' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">Icons</h2>
                <p className="mt-1 text-gray-600">
                  SVG icons available for use throughout the application
                </p>
              </div>
              <IconDemo />
            </section>
          )}

          {/* Inputs Section */}
          {activeSection === 'inputs' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">Inputs</h2>
                <p className="mt-1 text-gray-600">
                  Input components with different types, variants, and states
                </p>
              </div>
              <InputDemo />
            </section>
          )}

          {/* Cards Section */}
          {activeSection === 'cards' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">Cards</h2>
                <p className="mt-1 text-gray-600">
                  Card components for containing and organizing content
                </p>
              </div>
              <CardDemo />
            </section>
          )}

          {/* Containers Section */}
          {activeSection === 'containers' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">Containers</h2>
                <p className="mt-1 text-gray-600">
                  Container components for layout and content organization
                </p>
              </div>
              <ContainerDemo />
            </section>
          )}

          {/* Select Dropdowns Section */}
          {activeSection === 'selects' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">
                  Select Dropdowns
                </h2>
                <p className="mt-1 text-gray-600">
                  Custom select components built with Headless UI
                </p>
              </div>
              <SelectDemo />
            </section>
          )}

          {/* Comboboxes Section */}
          {activeSection === 'comboboxes' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">Comboboxes</h2>
                <p className="mt-1 text-gray-600">
                  Searchable dropdown components built with Headless UI
                </p>
              </div>
              <ComboboxDemo />
            </section>
          )}

          {/* Dialogs Section */}
          {activeSection === 'dialogs' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">Dialogs</h2>
                <p className="mt-1 text-gray-600">
                  Modal dialog components built with Headless UI
                </p>
              </div>
              <DialogDemo />
            </section>
          )}

          {/* Disclosures Section */}
          {activeSection === 'disclosures' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">
                  Disclosures
                </h2>
                <p className="mt-1 text-gray-600">
                  Expandable/collapsible components built with Headless UI
                </p>
              </div>
              <DisclosureDemo />
            </section>
          )}

          {/* Tabs Section */}
          {activeSection === 'tabs' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">Tabs</h2>
                <p className="mt-1 text-gray-600">
                  Tabbed interface components built with Headless UI
                </p>
              </div>
              <TabsDemo />
            </section>
          )}

          {/* Switches Section */}
          {activeSection === 'switches' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">Switches</h2>
                <p className="mt-1 text-gray-600">
                  Toggle switch components for enabling or disabling options
                </p>
              </div>
              <SwitchDemo />
            </section>
          )}
          {/* Layouts Section */}
          {activeSection === 'layouts' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">Layouts</h2>
                <p className="mt-1 text-gray-600">
                  Responsive grid and stack layout components
                </p>
              </div>
              <LayoutDemo />
            </section>
          )}

          {/* Placeholders for future components */}
          {activeSection === 'feedback' && (
            <section className="p-6">
              <div className="mb-6 border-b pb-4">
                <h2 className="text-2xl font-bold text-gray-800">
                  {navItems.find((item) => item.id === activeSection)?.label}
                </h2>
                <p className="mt-1 text-gray-600">
                  Feedback components demonstrating loading, error, and empty
                  states
                </p>
              </div>
              <FeedbackDemo />
            </section>
          )}
        </div>
      </main>
    </div>
  );
};

export default ComponentShowcase;
