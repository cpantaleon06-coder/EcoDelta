import { lazy, Suspense } from 'react';
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { DemoBanner } from './components/DemoBanner';
import { Loading } from './components/Status';

// one chunk per page: the map library loads only on Explore
const Explore = lazy(() => import('./pages/Explore'));
const Guided = lazy(() => import('./pages/Guided'));
const About = lazy(() => import('./pages/About'));

const NAV = [
  { to: '/explore', label: 'Explore' },
  { to: '/guided', label: 'Guided questions' },
  { to: '/about', label: 'About the data' },
];

export default function App() {
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <DemoBanner />
      <header className="site-header">
        <NavLink to="/explore" className="wordmark" aria-label="EcoDelta home">
          {/* delta mark: a triangle with a small rise inside */}
          <svg viewBox="0 0 26 26" aria-hidden="true">
            <path d="M13 3 24 22H2Z" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinejoin="round" />
            <path d="m7.5 18 3.5-4 2.5 2.5 4-5" fill="none" stroke="var(--green)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span aria-hidden="true">
            Eco<b>Delta</b>
          </span>
        </NavLink>
        <nav aria-label="Main">
          <ul className="nav">
            {NAV.map((n) => (
              <li key={n.to}>
                <NavLink to={n.to} className="nav__link">
                  {n.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main id="main" tabIndex={-1}>
        <Suspense fallback={<Loading minHeight={480} />}>
        <Routes>
          <Route path="/" element={<Navigate to="/explore" replace />} />
          <Route path="/explore" element={<Explore />} />
          <Route path="/guided" element={<Guided />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<Navigate to="/explore" replace />} />
        </Routes>
        </Suspense>
      </main>
      <footer className="site-footer">
        <p>
          Data: NASA GES DISC (MERRA-2, GPM IMERG, GLDAS). EcoDelta is a project for the NASA Space Apps Challenge. It
          is not an official NASA product.
        </p>
      </footer>
    </>
  );
}
