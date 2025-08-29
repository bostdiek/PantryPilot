import React from 'react';
import { Outlet } from 'react-router-dom';
import Navigation from './Navigation';
import { ToastContainer } from './ui/Toast';

/**
 * Root layout component that wraps all routes
 * Contains the navigation and common layout elements
 */
const Root: React.FC = () => {
  return (
    <>
      <Navigation />
      <Outlet />
      <ToastContainer />
    </>
  );
};

export default Root;
