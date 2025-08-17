import React from 'react';
import { NavLink } from 'react-router-dom';

const Navigation: React.FC = () => (
  <nav className="flex gap-4 bg-white px-4 py-2 shadow">
    <NavLink
      to="/"
      className={({ isActive }) =>
        'font-bold text-blue-600' + (isActive ? ' underline' : '')
      }
    >
      Home
    </NavLink>
    <NavLink
      to="/recipes"
      className={({ isActive }) =>
        'font-bold text-blue-600' + (isActive ? ' underline' : '')
      }
    >
      Recipes
    </NavLink>
    <NavLink
      to="/recipes/new"
      className={({ isActive }) =>
        'font-bold text-blue-600' + (isActive ? ' underline' : '')
      }
    >
      Add Recipe
    </NavLink>
    <NavLink
      to="/meal-plan"
      className={({ isActive }) =>
        'font-bold text-blue-600' + (isActive ? ' underline' : '')
      }
    >
      Meal Plan
    </NavLink>
    <NavLink
      to="/login"
      className={({ isActive }) =>
        'font-bold text-blue-600' + (isActive ? ' underline' : '')
      }
    >
      Login
    </NavLink>
  </nav>
);

export default Navigation;
