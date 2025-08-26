import React from 'react';
import { NavLink } from 'react-router-dom';

const Navigation: React.FC = () => (
  <nav className="flex gap-4 border-b border-gray-200 bg-white px-6 py-4 shadow">
    <NavLink
      to="/"
      end
      className={(meta: { isActive: boolean }) =>
        `text-lg font-bold ${
          meta.isActive
            ? 'text-primary-700 border-primary-500 border-b-2'
            : 'hover:text-primary-600 text-gray-700 transition-colors'
        }`
      }
    >
      Home
    </NavLink>
    <NavLink
      to="/recipes"
      className={(meta: { isActive: boolean }) =>
        `text-lg font-bold ${
          meta.isActive
            ? 'text-primary-700 border-primary-500 border-b-2'
            : 'hover:text-primary-600 text-gray-700 transition-colors'
        }`
      }
    >
      Recipes
    </NavLink>
    <NavLink
      to="/recipes/new"
      className={(meta: { isActive: boolean }) =>
        `text-lg font-bold ${
          meta.isActive
            ? 'text-primary-700 border-primary-500 border-b-2'
            : 'hover:text-primary-600 text-gray-700 transition-colors'
        }`
      }
    >
      Add Recipe
    </NavLink>
    <NavLink
      to="/meal-plan"
      className={(meta: { isActive: boolean }) =>
        `text-lg font-bold ${
          meta.isActive
            ? 'text-primary-700 border-primary-500 border-b-2'
            : 'hover:text-primary-600 text-gray-700 transition-colors'
        }`
      }
    >
      Meal Plan
    </NavLink>
    <NavLink
      to="/login"
      className={(meta: { isActive: boolean }) =>
        `text-lg font-bold ${
          meta.isActive
            ? 'text-primary-700 border-primary-500 border-b-2'
            : 'hover:text-primary-600 text-gray-700 transition-colors'
        }`
      }
    >
      Login
    </NavLink>
  </nav>
);

export default Navigation;
