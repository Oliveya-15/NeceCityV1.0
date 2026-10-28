import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { CityProvider } from './hooks/CityContext'
import Dashboard from './pages/Dashboard'
import CityMap from './pages/CityMap'
import ReportProblem from './pages/ReportProblem'
import PriorityList from './pages/PriorityList'

export default function App() {
  return (
    <CityProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/map" element={<CityMap />} />
          <Route path="/report" element={<ReportProblem />} />
          <Route path="/priorities" element={<PriorityList />} />
        </Routes>
      </BrowserRouter>
    </CityProvider>
  )
}
