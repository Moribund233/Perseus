import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './i18n';
import './index.css';
import App from './App';
import { ErrorBoundary } from './components/ErrorBoundary';

function logGlobalError(error: unknown) {
  console.error('[Global Error]', error instanceof Error ? error.message : error);
}

window.addEventListener('error', (event) => {
  logGlobalError(event.error ?? event.message);
});

window.addEventListener('unhandledrejection', (event) => {
  logGlobalError(event.reason);
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);
