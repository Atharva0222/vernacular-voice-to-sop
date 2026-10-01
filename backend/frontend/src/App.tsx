import { HashRouter, Route, Routes } from 'react-router-dom'
import { ToastProvider } from './components/Toast'
import Cards from './pages/Cards'
import Create from './pages/Create'
import Home from './pages/Home'
import Inbox from './pages/Inbox'
import Machines from './pages/Machines'

export default function App() {
  return (
    <ToastProvider>
      <HashRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/machines" element={<Machines />} />
          <Route path="/cards" element={<Cards />} />
          <Route path="/create" element={<Create />} />
          <Route path="/inbox" element={<Inbox />} />
        </Routes>
      </HashRouter>
    </ToastProvider>
  )
}
