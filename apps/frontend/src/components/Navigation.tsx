import { Home, ListChecks, Menu, MessageSquare, X } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  useAuthStore,
  useDisplayName,
  useIsAuthenticated,
} from '../stores/useAuthStore';
import { CalendarIcon, ChefHatIcon } from './ui';
import { Button } from './ui/Button';

const Navigation: React.FC = () => {
  const { hasHydrated, logout } = useAuthStore();
  const isAuthenticated = useIsAuthenticated();
  const displayName = useDisplayName();
  const navigate = useNavigate();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const mobileMenuRef = useRef<HTMLDivElement>(null);

  // Close menus when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(event.target as Node)
      ) {
        setUserMenuOpen(false);
      }
      if (
        mobileMenuRef.current &&
        !mobileMenuRef.current.contains(event.target as Node)
      ) {
        setMobileMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleLogout = () => {
    logout('manual');
    setUserMenuOpen(false);
    navigate('/login');
  };

  const handleProfileClick = () => {
    setUserMenuOpen(false);
    navigate('/user');
  };

  return (
    <nav className="border-b border-gray-200 bg-white shadow">
      <div className="flex items-center justify-between px-6 py-4">
        {/* Desktop Navigation Links - hidden on mobile */}
        <div className="hidden gap-4 md:flex">
          {/* Show navigation links only when authenticated */}
          {hasHydrated && isAuthenticated && (
            <>
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
                <span className="inline-flex items-center gap-2">
                  <Home className="h-5 w-5" aria-hidden="true" />
                  <span>Home</span>
                </span>
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
                <span className="inline-flex items-center gap-2">
                  <ChefHatIcon className="h-5 w-5" aria-hidden="true" />
                  <span>Recipes</span>
                </span>
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
                <span className="inline-flex items-center gap-2">
                  <CalendarIcon className="h-5 w-5" aria-hidden="true" />
                  <span>Meal Plan</span>
                </span>
              </NavLink>
              <NavLink
                to="/grocery-list"
                className={(meta: { isActive: boolean }) =>
                  `text-lg font-bold ${
                    meta.isActive
                      ? 'text-primary-700 border-primary-500 border-b-2'
                      : 'hover:text-primary-600 text-gray-700 transition-colors'
                  }`
                }
              >
                <span className="inline-flex items-center gap-2">
                  <ListChecks className="h-5 w-5" aria-hidden="true" />
                  <span>Grocery List</span>
                </span>
              </NavLink>
              <NavLink
                to="/assistant"
                className={(meta: { isActive: boolean }) =>
                  `text-lg font-bold ${
                    meta.isActive
                      ? 'text-primary-700 border-primary-500 border-b-2'
                      : 'hover:text-primary-600 text-gray-700 transition-colors'
                  }`
                }
              >
                <span className="inline-flex items-center gap-2">
                  <MessageSquare className="h-5 w-5" aria-hidden="true" />
                  <span>Assistant</span>
                </span>
              </NavLink>
            </>
          )}
        </div>

        {/* Mobile Hamburger Button - shown on mobile only */}
        {hasHydrated && isAuthenticated && (
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="flex items-center justify-center rounded-md p-2 text-gray-700 hover:bg-gray-100 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none md:hidden"
            aria-label="Toggle mobile menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? (
              <X className="h-6 w-6" aria-hidden="true" />
            ) : (
              <Menu className="h-6 w-6" aria-hidden="true" />
            )}
          </button>
        )}

        {/* Spacer for non-authenticated mobile view */}
        {hasHydrated && !isAuthenticated && <div className="md:hidden" />}

        {/* Authentication and User Menu */}
        <div className="flex items-center gap-2">
          {hasHydrated && (
            <>
              {isAuthenticated ? (
                <div className="relative" ref={userMenuRef}>
                  {/* User Menu Button */}
                  <button
                    onClick={() => setUserMenuOpen(!userMenuOpen)}
                    className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none"
                    aria-label="User menu"
                    aria-expanded={userMenuOpen}
                  >
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-blue-700">
                      {displayName.charAt(0).toUpperCase()}
                    </div>
                    <span className="hidden sm:block">{displayName}</span>
                    <svg
                      className={`h-4 w-4 transition-transform ${
                        userMenuOpen ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </button>

                  {/* Dropdown Menu */}
                  {userMenuOpen && (
                    <div className="ring-opacity-5 absolute right-0 z-50 mt-2 w-48 rounded-md bg-white py-1 shadow-lg ring-1 ring-black">
                      <button
                        onClick={handleProfileClick}
                        className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100"
                      >
                        Profile Settings
                      </button>
                      <button
                        onClick={handleLogout}
                        className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100"
                      >
                        Logout
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <NavLink to="/login">
                  <Button variant="primary">Login</Button>
                </NavLink>
              )}
            </>
          )}
        </div>
      </div>

      {/* Mobile Navigation Menu - shown when hamburger is clicked */}
      {hasHydrated && isAuthenticated && mobileMenuOpen && (
        <div
          ref={mobileMenuRef}
          className="border-t border-gray-200 bg-white px-6 py-4 md:hidden"
        >
          <div className="flex flex-col gap-3">
            <NavLink
              to="/"
              end
              onClick={() => setMobileMenuOpen(false)}
              className={(meta: { isActive: boolean }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-base font-medium ${
                  meta.isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`
              }
            >
              <Home className="h-5 w-5" aria-hidden="true" />
              <span>Home</span>
            </NavLink>
            <NavLink
              to="/recipes"
              onClick={() => setMobileMenuOpen(false)}
              className={(meta: { isActive: boolean }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-base font-medium ${
                  meta.isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`
              }
            >
              <ChefHatIcon className="h-5 w-5" aria-hidden="true" />
              <span>Recipes</span>
            </NavLink>
            <NavLink
              to="/meal-plan"
              onClick={() => setMobileMenuOpen(false)}
              className={(meta: { isActive: boolean }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-base font-medium ${
                  meta.isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`
              }
            >
              <CalendarIcon className="h-5 w-5" aria-hidden="true" />
              <span>Meal Plan</span>
            </NavLink>
            <NavLink
              to="/grocery-list"
              onClick={() => setMobileMenuOpen(false)}
              className={(meta: { isActive: boolean }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-base font-medium ${
                  meta.isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`
              }
            >
              <ListChecks className="h-5 w-5" aria-hidden="true" />
              <span>Grocery List</span>
            </NavLink>
            <NavLink
              to="/assistant"
              onClick={() => setMobileMenuOpen(false)}
              className={(meta: { isActive: boolean }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-base font-medium ${
                  meta.isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`
              }
            >
              <MessageSquare className="h-5 w-5" aria-hidden="true" />
              <span>Assistant</span>
            </NavLink>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navigation;
