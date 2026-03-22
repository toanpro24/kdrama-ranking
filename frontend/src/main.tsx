import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './AuthContext'
import { ActressProvider } from './ActressContext'
import App from './App'
import ActressDetail from './ActressDetail'
import DramaDetail from './DramaDetail'
import Compare from './Compare'
import Timeline from './Timeline'
import Recommendations from './Recommendations'
import StatsPage from './StatsPage'
import Watchlist from './Watchlist'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
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
        </Routes>
      </ActressProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
