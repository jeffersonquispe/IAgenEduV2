import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { Rocket, Lock, ArrowLeft } from 'lucide-react'
import axios from 'axios'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const navigate = useNavigate()

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (newPassword.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Las contraseñas no coinciden')
      return
    }

    setLoading(true)
    try {
      await axios.post('/api/auth/reset-password', { token, new_password: newPassword })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2500)
    } catch (err) {
      setError(err.response?.data?.detail || 'No se pudo restablecer la contraseña')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md glass rounded-3xl p-8 shadow-2xl">
        <div className="flex flex-col items-center mb-8">
          <div className="p-4 bg-indigo-500 rounded-full mb-4 shadow-[0_0_20px_rgba(99,102,241,0.5)]">
            <Rocket className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold gradient-text">Nueva contraseña</h1>
          <p className="text-slate-400 mt-2 text-center">Ingresa tu nueva contraseña para completar la recuperación.</p>
        </div>

        {!token && (
          <p className="text-red-400 text-sm text-center mb-4">
            Falta el token de recuperación en el enlace. Solicita uno nuevo desde la pantalla de inicio de sesión.
          </p>
        )}

        {success ? (
          <p className="text-emerald-400 text-sm text-center">
            Contraseña actualizada correctamente. Redirigiendo a inicio de sesión...
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <Lock className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
              <input
                type="password"
                placeholder="Nueva contraseña"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-indigo-500 transition-colors"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
              <input
                type="password"
                placeholder="Confirmar contraseña"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-indigo-500 transition-colors"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>

            {error && <p className="text-red-400 text-sm text-center">{error}</p>}

            <button
              type="submit"
              disabled={!token || loading}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-bold shadow-lg shadow-indigo-500/20 transition-all disabled:opacity-50"
            >
              {loading ? 'Actualizando...' : 'Actualizar contraseña'}
            </button>
          </form>
        )}

        <div className="mt-6 text-center">
          <Link to="/login" className="inline-flex items-center gap-2 text-indigo-400 hover:text-indigo-300 text-sm font-medium transition-colors">
            <ArrowLeft size={16} /> Volver a inicio de sesión
          </Link>
        </div>
      </div>
    </div>
  )
}
