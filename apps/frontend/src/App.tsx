import React from 'react';
import Routes from './routes';
import { ErrorBoundary } from './components/ErrorBoundary';

const App: React.FC = () => {
  return (
    <ErrorBoundary
      onError={(error, _errorInfo) => {
        // In production, you could send this to an error reporting service
        if (import.meta.env.MODE === 'production') {
          console.error('Application error:', error);
          // Example: reportError(error, errorInfo);
        }
      }}
    >
      <Routes />
    </ErrorBoundary>
  );
};

export default App;
