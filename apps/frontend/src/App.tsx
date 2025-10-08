import React from 'react';
import { ErrorBoundary } from './components/ErrorBoundary';
import { logger } from './lib/logger';
import Routes from './routes';

const App: React.FC = () => {
  return (
    <ErrorBoundary
      onError={(error, _errorInfo) => {
        // In production, you could send this to an error reporting service
        if (import.meta.env.MODE === 'production') {
          logger.error('Application error:', error);
          // Example: reportError(error, errorInfo);
        }
      }}
    >
      <Routes />
    </ErrorBoundary>
  );
};

export default App;
