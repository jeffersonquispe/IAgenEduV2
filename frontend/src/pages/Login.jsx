import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Rocket, Mail, Lock, User } from 'lucide-react'
import { supabase } from '../lib/supabaseClient'

export default function Login() {
  const [isLogin, setIsLogin] = useState(true)
  const [showForgotPassword, setShowForgotPassword] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [forgotPasswordMessage, setForgotPasswordMessage] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      if (isLogin) {
        const { error: err } = await supabase.auth.signInWithPassword({ email, password })
        if (err) throw err
        // App.jsx escucha onAuthStateChange y actualiza la sesión — solo navegamos.
        navigate('/')
      } else {
        const { data, error: err } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { full_name: fullName } },
        })
        if (err) throw err
        setIsLogin(true)
        if (data.session) {
          navigate('/')
        } else {
          alert('Registro exitoso. Revisa tu correo para confirmar la cuenta antes de iniciar sesión.')
        }
      }
    } catch (err) {
      setError(err.message || 'Algo salió mal')
    }
  }

  const handleForgotPassword = async (e) => {
    e.preventDefault()
    setForgotPasswordMessage('')
    const { error: err } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    })
    setForgotPasswordMessage(
      err ? err.message : 'Si el correo existe en el sistema, se envió un enlace de recuperación.'
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md glass rounded-3xl p-8 shadow-2xl">
        <div className="flex flex-col items-center mb-8">
          <div className="p-4 bg-indigo-500 rounded-full mb-4 shadow-[0_0_20px_rgba(99,102,241,0.5)]">
            <Rocket className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold gradient-text">EduGen AI 2.0</h1>
          <p className="text-slate-400 mt-2 text-center">
            {showForgotPassword ? 'Recupera el acceso a tu cuenta' : (isLogin ? 'Bienvenido de nuevo, maestro' : 'Herramienta de generación de sesiones y unidades')}
          </p>
        </div>

        {showForgotPassword ? (
          <>
            <form onSubmit={handleForgotPassword} className="space-y-4">
              <div className="relative">
                <Mail className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                <input
                  type="email"
                  placeholder="Tu email"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-indigo-500 transition-colors"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              {forgotPasswordMessage && (
                <p className="text-emerald-400 text-sm text-center">{forgotPasswordMessage}</p>
              )}

              <button type="submit" className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-bold shadow-lg shadow-indigo-500/20 transition-all">
                Enviar enlace de recuperación
              </button>
            </form>

            <div className="mt-6 text-center">
              <button
                onClick={() => { setShowForgotPassword(false); setForgotPasswordMessage('') }}
                className="text-indigo-400 hover:text-indigo-300 text-sm font-medium transition-colors"
              >
                Volver a inicio de sesión
              </button>
            </div>
          </>
        ) : (
          <>
            <form onSubmit={handleSubmit} className="space-y-4">
              {!isLogin && (
                <div className="relative">
                  <User className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Nombre completo"
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-indigo-500 transition-colors"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                  />
                </div>
              )}
              <div className="relative">
                <Mail className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                <input
                  type="email"
                  placeholder="Email"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-indigo-500 transition-colors"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                <input
                  type="password"
                  placeholder="Contraseña"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-indigo-500 transition-colors"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              {isLogin && (
                <div className="text-right -mt-2">
                  <button
                    type="button"
                    onClick={() => { setShowForgotPassword(true); setError('') }}
                    className="text-slate-500 hover:text-indigo-400 text-xs font-medium transition-colors"
                  >
                    ¿Olvidaste tu contraseña?
                  </button>
                </div>
              )}

              {error && <p className="text-red-400 text-sm text-center">{error}</p>}

              <button type="submit" className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-bold shadow-lg shadow-indigo-500/20 transition-all flex items-center justify-center gap-2">
                {isLogin ? 'Ingresar' : 'Registrarse'}
              </button>
            </form>

            <div className="mt-6 text-center">
              <button
                onClick={() => setIsLogin(!isLogin)}
                className="text-indigo-400 hover:text-indigo-300 text-sm font-medium transition-colors"
              >
                {isLogin ? '¿No tienes cuenta? Regístrate aquí' : '¿Ya tienes cuenta? Inicia sesión'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
