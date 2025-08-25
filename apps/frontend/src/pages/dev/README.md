# UI Components Showcase

This directory contains a dedicated Component Showcase page for development purposes.

## Purpose

- Provides a centralized location to view and test all UI components
- Makes it easier to visualize different component states and variants
- Serves as a living style guide for the application
- Helps with component development and debugging

## Usage

The Component Showcase page is available at the following route during development:

```bash
/dev/components
```

This route is only intended for development use and would typically be disabled in production builds.

## Adding New Components

When creating new UI components:

1. Build the component in the `src/components/ui/` directory
2. Create a demo component in `src/components/ui/demo.tsx`
3. Update the Component Showcase page to include your new component

## Structure

- `ComponentShowcase.tsx` - Main component showcase page with navigation
- `index.tsx` - Export file for easier imports
