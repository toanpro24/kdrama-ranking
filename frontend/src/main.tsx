import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App'
import ActressDetail from './ActressDetail'
import DramaDetail from './DramaDetail'
import Compare from './Compare'
import Timeline from './Timeline'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/actress/:id" element={<ActressDetail />} />
        <Route path="/drama/:title" element={<DramaDetail />} />
        <Route path="/compare" element={<Compare />} />
        <Route path="/timeline" element={<Timeline />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
