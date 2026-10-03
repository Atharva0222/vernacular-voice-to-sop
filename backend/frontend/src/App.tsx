import { HashRouter, Route, Routes } from 'react-router-dom'
import { ToastProvider } from './components/Toast'
import Cards from './pages/Cards'
import Create from './pages/Create'
import Dashboard from './pages/Dashboard'
import Home from './pages/Home'
import Inbox from './pages/Inbox'
import Machines from './pages/Machines'
import EmployeeDirectory from './pages/employees/Directory'
import WorkforceRoster from './pages/workforce/Roster'
import HROverview from './pages/hr/Overview'

export default function App() {
  return (
    <ToastProvider>
      <HashRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/machines" element={<Machines />} />
          <Route path="/cards" element={<Cards />} />
          <Route path="/create" element={<Create />} />
          <Route path="/inbox" element={<Inbox />} />
          <Route path="/employees" element={<EmployeeDirectory />} />
          <Route path="/workforce" element={<WorkforceRoster />} />
          <Route path="/hr" element={<HROverview />} />
        </Routes>
      </HashRouter>
    </ToastProvider>
  )
}
