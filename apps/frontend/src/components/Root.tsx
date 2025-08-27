import React from 'react';
import { Outlet } from 'react-router-dom';
import Navigation from './Navigation';

/**
 * Root layout component that wraps all routes
 * Contains the navigation and common layout elements
 */
const Root: React.FC = () => {
  return (
    <>
      <Navigation />
      <Outlet />
    </>
  );
};

export default Root;
