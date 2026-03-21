import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import axios from 'axios'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Editor from './pages/Editor'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Axios interceptor to handle 401 Unauthorized errors globally
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('token')
          setUser(null)
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )

    const token = localStorage.getItem('token')
    if (token) {
      setUser({ token })
    }
    setLoading(false)

    return () => {
      axios.interceptors.response.eject(interceptor)
    }
  }, [])

  if (loading) return <div className="h-screen flex items-center justify-center">Cargando...</div>

  return (
    <Router>
      <div className="min-h-screen bg-dark">
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" /> : <Login setUser={setUser} />} />
          <Route path="/" element={user ? <Dashboard user={user} setUser={setUser} /> : <Navigate to="/login" />} />
          <Route path="/editor" element={user ? <Editor user={user} /> : <Navigate to="/login" />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
