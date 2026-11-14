import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import './index.css';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* Hash routing works on any static host (Vercel, GitHub Pages) without rewrite rules. */}
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
);
