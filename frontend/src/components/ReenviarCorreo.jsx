import { useState, useEffect } from 'react'
import { reenviarCorreoConfirmacion, SEGUNDOS_ENTRE_REENVIOS } from '../lib/verificacionCorreo'

// HU-20: botón para reenviar el correo de confirmación. El enfriamiento evita que un
// doble clic gaste el límite de envíos que Supabase aplica por hora.
export default function ReenviarCorreo({ email, className = '' }) {
  const [segundos, setSegundos] = useState(0)
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState(null) // { ok, mensaje }

  useEffect(() => {
    if (segundos <= 0) return
    const t = setTimeout(() => setSegundos(s => s - 1), 1000)
    return () => clearTimeout(t)
  }, [segundos])

  const reenviar = async () => {
    setEnviando(true)
    setResultado(null)
    const r = await reenviarCorreoConfirmacion(email)
    setResultado(r)
    setEnviando(false)
    if (r.ok) setSegundos(SEGUNDOS_ENTRE_REENVIOS)
  }

  return (
    <div className={className}>
      <button
        type="button"
        onClick={reenviar}
        disabled={enviando || segundos > 0 || !email}
        className="text-sm font-bold text-accent-text hover:underline disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {enviando ? 'Enviando…' : segundos > 0 ? `Reenviar correo (${segundos}s)` : 'Reenviar correo de confirmación'}
      </button>
      {resultado && (
        <p role="status" className={`text-xs mt-2 ${resultado.ok ? 'text-success-text' : 'text-danger-text'}`}>
          {resultado.mensaje}
        </p>
      )}
    </div>
  )
}
