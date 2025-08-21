import React from 'react';
import { NavLink } from 'react-router-dom';

const Navigation: React.FC = () => (
  <nav className="flex gap-4 bg-white px-4 py-2 shadow">
    <NavLink
      to="/"
      end
      className={(meta: { isActive: boolean }) =>
        `font-bold text-blue-600 ${meta.isActive ? 'underline' : ''}`
      }
    >
      Home
    </NavLink>
    <NavLink
      to="/recipes"
      className={(meta: { isActive: boolean }) =>
        `font-bold text-blue-600 ${meta.isActive ? 'underline' : ''}`
      }
    >
      Recipes
    </NavLink>
    <NavLink
      to="/recipes/new"
      className={(meta: { isActive: boolean }) =>
        `font-bold text-blue-600 ${meta.isActive ? 'underline' : ''}`
      }
    >
      Add Recipe
    </NavLink>
    <NavLink
      to="/meal-plan"
      className={(meta: { isActive: boolean }) =>
        `font-bold text-blue-600 ${meta.isActive ? 'underline' : ''}`
      }
    >
      Meal Plan
    </NavLink>
    <NavLink
      to="/login"
      className={(meta: { isActive: boolean }) =>
        `font-bold text-blue-600 ${meta.isActive ? 'underline' : ''}`
      }
    >
      Login
    </NavLink>
  </nav>
);

export default Navigation;
