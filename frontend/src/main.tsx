import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './AuthContext'
import { ActressProvider } from './ActressContext'
import ErrorBoundary from './ErrorBoundary'
import App from './App'
import ActressDetail from './ActressDetail'
import DramaDetail from './DramaDetail'
import Compare from './Compare'
import Timeline from './Timeline'
import Recommendations from './Recommendations'
import StatsPage from './StatsPage'
import Watchlist from './Watchlist'
import UserSettings from './UserSettings'
import SharedTierList from './SharedTierList'
import Leaderboard from './Leaderboard'
import CompareLists from './CompareLists'
import NotFound from './NotFound'

// Register service worker for PWA
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ErrorBoundary>
      <AuthProvider>
      <ActressProvider>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/actress/:id" element={<ActressDetail />} />
          <Route path="/drama/:title" element={<DramaDetail />} />
          <Route path="/stats" element={<StatsPage />} />
          <Route path="/watchlist" element={<Watchlist />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/timeline" element={<Timeline />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/settings" element={<UserSettings />} />
          <Route path="/tier-list/:slug" element={<SharedTierList />} />
          <Route path="/compare-lists/:slug1/:slug2" element={<CompareLists />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </ActressProvider>
      </AuthProvider>
      </ErrorBoundary>
    </BrowserRouter>
  </StrictMode>,
)
