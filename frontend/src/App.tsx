import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Contacts from './pages/Contacts'
import Conversation from './pages/Conversation'
import ProtectedRoute from './components/ProtectedRoute'
import NewConversation from './pages/NewConversation'
import DeleteContact from './pages/DeleteContact'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/contacts/:id/delete" element={<DeleteContact />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/contacts" element={<Contacts />} />
        <Route path="/conversation" element={<Conversation />} />
        <Route path="/contacts/new" element={<NewConversation />} />
      </Route>
    </Routes>
  )
}

export default App