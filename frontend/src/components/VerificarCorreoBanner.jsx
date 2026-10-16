import { useState, useEffect } from 'react'
import { MailWarning } from 'lucide-react'
import { api } from '../lib/api'
import { supabase } from '../lib/supabaseClient'
import { esErrorCorreoNoVerificado } from '../lib/verificacionCorreo'
import ReenviarCorreo from './ReenviarCorreo'

// HU-20: aviso persistente mientras el correo de la sesión no esté verificado. Con
// "Confirm email" activo en Supabase no se puede iniciar sesión sin confirmar, así
// que esto cubre los casos restantes: cuentas creadas sin confirmación y el 403
// "email_not_verified" del backend cuando REQUIRE_VERIFIED_EMAIL está activo.
export default function VerificarCorreoBanner() {
  const [email, setEmail] = useState(null) // solo se informa si hay algo que avisar

  useEffect(() => {
    let vivo = true
    const emailDeSesion = async () => (await supabase.auth.getSession()).data.session?.user?.email || ''

    api.get('/auth/me')
      .then(async res => {
        if (vivo && res.data?.email_verified === false) setEmail(res.data.email || await emailDeSesion())
      })
      .catch(async err => {
        if (vivo && esErrorCorreoNoVerificado(err)) setEmail(await emailDeSesion())
      })
    return () => { vivo = false }
  }, [])

  if (!email) return null
  return (
    <div role="alert" className="mb-8 rounded-2xl border border-warning/30 bg-warning/10 p-5 flex items-start gap-4">
      <MailWarning className="text-warning-text shrink-0 mt-0.5" size={22} />
      <div>
        <p className="font-bold text-warning-text">Confirma tu correo electrónico</p>
        <p className="text-sm text-warning-text mt-1">
          Aún no confirmaste <strong>{email}</strong>. Abre el enlace que te enviamos para activar tu cuenta por completo.
        </p>
        <ReenviarCorreo email={email} className="mt-3" />
      </div>
    </div>
  )
}
