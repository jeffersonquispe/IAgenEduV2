import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { supabase } from './lib/supabaseClient'
import { api } from './lib/api'
import Login from './pages/Login'
import ResetPassword from './pages/ResetPassword'
import Dashboard from './pages/Dashboard'
import Editor from './pages/Editor'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Interceptor de respuesta: cierra sesión globalmente ante cualquier 401.
    const interceptor = api.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          await supabase.auth.signOut()
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )

    // Estado inicial de sesión + reactividad (refresco de token, logout entre pestañas).
    supabase.auth.getSession().then(({ data }) => {
      setUser(data.session?.user ?? null)
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })

    return () => {
      api.interceptors.response.eject(interceptor)
      subscription.unsubscribe()
    }
  }, [])

  if (loading) return <div className="h-screen flex items-center justify-center">Cargando...</div>

  return (
    <Router>
      <div className="min-h-screen bg-dark">
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" /> : <Login />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/" element={user ? <Dashboard user={user} /> : <Navigate to="/login" />} />
          <Route path="/editor" element={user ? <Editor user={user} /> : <Navigate to="/login" />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
