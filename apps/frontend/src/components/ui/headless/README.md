# Headless UI Integration

[Headless UI](https://headlessui.com) is a completely unstyled, fully accessible UI component library designed to integrate seamlessly with Tailwind CSS. This guide explains our approach to using Headless UI components in PantryPilot.

## Our Integration Approach

We've chosen a lightweight approach that:

1. Creates wrapper components around Headless UI primitives
2. Uses custom SVG icons instead of a full icon library
3. Applies consistent Tailwind styling patterns
4. Enhances accessibility through proper ARIA attributes

## Icon Approach

Instead of using a full icon library like Heroicons, we're using individual SVG files:

- Storing them in the `src/components/ui/icons` directory
- Creating an `Icon` component to use them consistently
- Importing SVGs directly using Vite's built-in SVG support

This approach keeps our bundle size smaller and gives us more control.

## Core Headless UI Components

Based on the latest documentation, we'll be integrating these key components:

1. **Select/Listbox** - For dropdown selection
2. **Dialog** - For modal dialogs and popovers
3. **Disclosure** - For collapsible sections (like recipe instructions)
4. **Tabs** - For tabbed interfaces (like recipe info tabs)
5. **Switch** - For toggle switches

## Styling Patterns

Headless UI provides two main ways to style components:

1. **Data Attributes**: Use Tailwind's data-\* modifiers:

   ```jsx
   <Button className="bg-white data-active:bg-blue-100">Click me</Button>
   ```

2. **Render Props**: For more complex styling needs:
   ```jsx
   <Button as={Fragment}>
     {({ active }) => (
       <button className={active ? 'bg-blue-100' : 'bg-white'}>Click me</button>
     )}
   </Button>
   ```

## Usage Example

```tsx
// Import our wrapped components
import { Select, Button, Dialog } from '@/components/ui';

// All components use a consistent API and styling
const MyComponent = () => {
  const options = [
    { id: 'easy', name: 'Easy' },
    { id: 'medium', name: 'Medium' },
    { id: 'hard', name: 'Hard' },
  ];

  return (
    <Select
      options={options}
      value={options[0]}
      onChange={(option) => console.log(option)}
      label="Difficulty"
    />
  );
};
```

## Adding New Components

When adding a new component:

1. Create the component file in `src/components/ui/`
2. Add any required SVG icons to `src/components/ui/icons/`
3. Re-export the component in `src/components/ui/index.ts`
4. Document the component with JSDoc comments

## Available Components

- `Icon.tsx` - SVG icon renderer
- `Select.tsx` - Dropdown select (wraps Headless UI's Listbox)
- More coming soon...
