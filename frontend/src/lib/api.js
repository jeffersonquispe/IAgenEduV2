import axios from 'axios'
import { supabase } from './supabaseClient'

// Instancia compartida: adjunta el token de sesión de Supabase automáticamente
// en cada request. Reemplaza el patrón anterior de pasar
// `headers: { Authorization: ... }` manualmente en cada llamada.
export const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession()
  if (data.session?.access_token) {
    config.headers.Authorization = `Bearer ${data.session.access_token}`
  }
  return config
})
