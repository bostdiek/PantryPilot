import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';

const canonicalOrigin = import.meta.env.VITE_CANONICAL_ORIGIN;
if (canonicalOrigin && window.location.origin !== canonicalOrigin) {
  window.location.replace(
    canonicalOrigin +
      window.location.pathname +
      window.location.search +
      window.location.hash
  );
} else {
  const { default: App } = await import('./App.tsx');
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>
  );
}
