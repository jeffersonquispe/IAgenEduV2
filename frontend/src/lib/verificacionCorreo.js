import { supabase } from './supabaseClient'

// HU-20: la verificación de correo la hace Supabase Auth ("Confirm email"). Estas
// utilidades solo reenvían el correo y reconocen el error de "correo sin confirmar".

export const SEGUNDOS_ENTRE_REENVIOS = 60

// Supabase devuelve code 'email_not_confirmed' (y, en versiones anteriores, solo el mensaje).
export const esErrorCorreoSinConfirmar = (err) =>
  err?.code === 'email_not_confirmed' || /email not confirmed/i.test(err?.message || '')

// Un 403 del backend con REQUIRE_VERIFIED_EMAIL activo.
export const esErrorCorreoNoVerificado = (err) =>
  err?.response?.status === 403 && err?.response?.data?.detail?.code === 'email_not_verified'

export async function reenviarCorreoConfirmacion(email) {
  const { error } = await supabase.auth.resend({
    type: 'signup',
    email,
    options: { emailRedirectTo: window.location.origin },
  })
  if (error) {
    // Supabase limita los envíos (p. ej. "email rate limit exceeded"): se muestra tal cual.
    return { ok: false, mensaje: error.message || 'No se pudo reenviar el correo.' }
  }
  return { ok: true, mensaje: 'Te reenviamos el correo de confirmación. Revisa también la carpeta de spam.' }
}
