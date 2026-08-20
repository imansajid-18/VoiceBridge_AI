import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Contacts from './pages/Contacts'
import Conversation from './pages/Conversation'
import ProtectedRoute from './components/ProtectedRoute'
import NewConversation from './pages/NewConversation'
import DeleteContact from './pages/DeleteContact'
import SessionDecision from './pages/SessionDecision'
import MemoryViewer from './pages/MemoryViewer'
import SessionSummary from './pages/SessionSummary'

function App() {
  return (
  <Routes>
  <Route path="/" element={<Navigate to="/login" replace />} />
  <Route path="/login" element={<Login />} />
  <Route path="/register" element={<Register />} />
  <Route element={<ProtectedRoute />}>
  <Route path="/contacts" element={<Contacts />} />
  <Route path="/contacts/new" element={<NewConversation />} />
  <Route path="/contacts/:id/delete" element={<DeleteContact />} />
  <Route path="/conversation" element={<Conversation />} />
  <Route path="/sessions/:id/decide" element={<SessionDecision />} />
  <Route path="/sessions/:id/summary" element={<SessionSummary />} />
  <Route path="/memory" element={<MemoryViewer />} />
  <Route path="/memory/:contactId" element={<MemoryViewer />} />
  </Route>
  <Route path="*" element={<Navigate to="/contacts" replace />} />
</Routes>
  )
}

export default App