import { Tab as HeadlessTab, TabPanel } from '@headlessui/react';
import clsx from 'clsx';
import type { ReactNode } from 'react';
import { Fragment } from 'react';

export type TabsProps = {
  /**
   * Array of tab data objects
   */
  tabs: {
    /**
     * Unique identifier for the tab
     */
    id: string;

    /**
     * Tab label shown in the tab bar
     */
    label: ReactNode;

    /**
     * Tab content shown when the tab is active
     */
    content: ReactNode;

    /**
     * Whether the tab is disabled
     * @default false
     */
    disabled?: boolean;
  }[];

  /**
   * Index of the tab that should be selected by default
   * @default 0
   */
  defaultIndex?: number;

  /**
   * Index of the selected tab (controlled mode)
   */
  selectedIndex?: number;

  /**
   * Callback fired when the selected tab changes
   */
  onChange?: (index: number) => void;

  /**
   * Whether the tabs should use vertical layout
   * @default false
   */
  vertical?: boolean;

  /**
   * Additional classes for the tabs container
   */
  className?: string;

  /**
   * Additional classes for the tab list (tab bar)
   */
  tabListClassName?: string;

  /**
   * Additional classes for individual tabs
   */
  tabClassName?: string;

  /**
   * Additional classes for selected tabs
   */
  selectedTabClassName?: string;

  /**
   * Additional classes for the tab panels container
   */
  panelsClassName?: string;

  /**
   * Additional classes for individual tab panels
   */
  panelClassName?: string;
};

/**
 * Tabs component based on Headless UI's Tab
 *
 * This provides an accessible tabbed interface
 *
 * @example
 * ```tsx
 * const tabs = [
 *   { id: 'tab1', label: 'Tab 1', content: <p>Content for Tab 1</p> },
 *   { id: 'tab2', label: 'Tab 2', content: <p>Content for Tab 2</p> },
 * ];
 *
 * <Tabs tabs={tabs} />
 * ```
 */
export function Tabs({
  tabs,
  defaultIndex = 0,
  selectedIndex,
  onChange,
  vertical = false,
  className = '',
  tabListClassName = '',
  tabClassName = '',
  selectedTabClassName = '',
  panelsClassName = '',
  panelClassName = '',
}: TabsProps) {
  return (
    <HeadlessTab.Group
      defaultIndex={defaultIndex}
      selectedIndex={selectedIndex}
      onChange={onChange}
      vertical={vertical}
      as="div"
      className={className}
    >
      <HeadlessTab.List
        className={clsx(
          'flex',
          vertical
            ? 'flex-col space-y-2'
            : 'space-x-2 border-b border-gray-200',
          tabListClassName
        )}
      >
        {tabs.map((tab) => (
          <HeadlessTab key={tab.id} disabled={tab.disabled} as={Fragment}>
            {({ selected }) => (
              <button
                className={clsx(
                  // Base styles
                  'text-sm font-medium whitespace-nowrap focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none',

                  // Selected state
                  selected && [
                    'bg-white',
                    'text-blue-600',
                    !vertical && 'border-b-2 border-blue-500',
                    selectedTabClassName,
                  ],

                  // Not selected state
                  !selected &&
                    'text-gray-500 hover:border-gray-300 hover:text-gray-700',

                  // Vertical vs horizontal styling
                  vertical
                    ? 'rounded-md px-3 py-2 text-left'
                    : 'rounded-t-lg border-b-2 border-transparent px-4 py-2',

                  // Disabled state
                  tab.disabled
                    ? 'cursor-not-allowed opacity-50'
                    : 'cursor-pointer',

                  // Custom class
                  tabClassName
                )}
              >
                {tab.label}
              </button>
            )}
          </HeadlessTab>
        ))}
      </HeadlessTab.List>

      <HeadlessTab.Panels className={clsx('mt-2', panelsClassName)}>
        {tabs.map((tab) => (
          <TabPanel
            key={tab.id}
            className={clsx(
              'rounded-md p-3 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none',
              panelClassName
            )}
          >
            {tab.content}
          </TabPanel>
        ))}
      </HeadlessTab.Panels>
    </HeadlessTab.Group>
  );
}
