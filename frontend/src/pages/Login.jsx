import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Rocket, Mail, Lock, User } from 'lucide-react'
import { supabase } from '../lib/supabaseClient'
import { esErrorCorreoSinConfirmar } from '../lib/verificacionCorreo'
import ReenviarCorreo from '../components/ReenviarCorreo'

export default function Login() {
  const [isLogin, setIsLogin] = useState(true)
  // HU-20: correo al que se envió la confirmación (tras registrarse) / correo sin confirmar (al ingresar).
  const [pendienteConfirmar, setPendienteConfirmar] = useState('')
  const [correoSinConfirmar, setCorreoSinConfirmar] = useState(false)
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
    setCorreoSinConfirmar(false)
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
        if (data.session) {
          setIsLogin(true)
          navigate('/')
        } else {
          // Con "Confirm email" activo en Supabase no hay sesión hasta confirmar (HU-20).
          setPendienteConfirmar(email)
        }
      }
    } catch (err) {
      if (esErrorCorreoSinConfirmar(err)) {
        setCorreoSinConfirmar(true)
        setError('Tu correo aún no está confirmado. Abre el enlace que te enviamos o reenvía el correo.')
      } else {
        setError(err.message || 'Algo salió mal')
      }
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
          <div className="p-4 bg-accent rounded-full mb-4">
            <Rocket className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold gradient-text">EduGen AI 2.0</h1>
          <p className="text-fg-muted mt-2 text-center">
            {showForgotPassword ? 'Recupera el acceso a tu cuenta' : (isLogin ? 'Bienvenido de nuevo, maestro' : 'Herramienta de generación de sesiones y unidades')}
          </p>
        </div>

        {pendienteConfirmar ? (
          <div className="text-center space-y-4" role="status">
            <Mail className="w-10 h-10 text-accent-text mx-auto" />
            <p className="font-bold text-lg">Revisa tu correo</p>
            <p className="text-fg-muted text-sm">
              Enviamos un enlace de confirmación a <strong className="text-fg">{pendienteConfirmar}</strong>.
              Ábrelo para activar tu cuenta y luego inicia sesión.
            </p>
            <ReenviarCorreo email={pendienteConfirmar} />
            <div>
              <button
                onClick={() => { setPendienteConfirmar(''); setIsLogin(true); setError('') }}
                className="text-accent-text hover:underline text-sm font-medium transition-colors"
              >
                Ya confirmé mi correo: iniciar sesión
              </button>
            </div>
          </div>
        ) : showForgotPassword ? (
          <>
            <form onSubmit={handleForgotPassword} className="space-y-4">
              <div className="relative">
                <Mail className="absolute left-3 top-3 w-5 h-5 text-fg-subtle" />
                <input
                aria-label="Tu email"
                  type="email"
                  placeholder="Tu email"
                  className="w-full bg-surface border border-line rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-accent transition-colors"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              {forgotPasswordMessage && (
                <p className="text-success-text text-sm text-center">{forgotPasswordMessage}</p>
              )}

              <button type="submit" className="w-full py-3 bg-accent hover:bg-accent-hover text-white rounded-xl font-bold transition-all">
                Enviar enlace de recuperación
              </button>
            </form>

            <div className="mt-6 text-center">
              <button
                onClick={() => { setShowForgotPassword(false); setForgotPasswordMessage('') }}
                className="text-accent-text hover:underline text-sm font-medium transition-colors"
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
                  <User className="absolute left-3 top-3 w-5 h-5 text-fg-subtle" />
                  <input
                aria-label="Nombre completo"
                    type="text"
                    placeholder="Nombre completo"
                    className="w-full bg-surface border border-line rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-accent transition-colors"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                  />
                </div>
              )}
              <div className="relative">
                <Mail className="absolute left-3 top-3 w-5 h-5 text-fg-subtle" />
                <input
                aria-label="Email"
                  type="email"
                  placeholder="Email"
                  className="w-full bg-surface border border-line rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-accent transition-colors"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-3 w-5 h-5 text-fg-subtle" />
                <input
                aria-label="Contraseña"
                  type="password"
                  placeholder="Contraseña"
                  className="w-full bg-surface border border-line rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-accent transition-colors"
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
                    className="text-fg-subtle hover:text-accent-text text-xs font-medium transition-colors"
                  >
                    ¿Olvidaste tu contraseña?
                  </button>
                </div>
              )}

              {error && <p className="text-danger-text text-sm text-center">{error}</p>}
              {correoSinConfirmar && <ReenviarCorreo email={email} className="text-center -mt-2" />}

              <button type="submit" className="w-full py-3 bg-accent hover:bg-accent-hover text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2">
                {isLogin ? 'Ingresar' : 'Registrarse'}
              </button>
            </form>

            <div className="mt-6 text-center">
              <button
                onClick={() => setIsLogin(!isLogin)}
                className="text-accent-text hover:underline text-sm font-medium transition-colors"
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
