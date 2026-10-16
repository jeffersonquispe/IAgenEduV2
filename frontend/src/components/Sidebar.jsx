import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { GraduationCap, Flame, Target, LogOut, ChevronRight, LayoutDashboard, FilePlus, Settings, BookOpen, Sun, Moon, Menu, X } from 'lucide-react'
import { api } from '../lib/api'
import { supabase } from '../lib/supabaseClient'
import { useTema } from '../lib/theme'

// `onBeforeNavigate` (opcional): función async que devuelve false para cancelar la navegación
// (p. ej. el Editor con cambios sin guardar).
//
// Responsive: desde `lg` es una columna fija; por debajo, una barra superior con botón de menú que
// abre el mismo contenido como panel deslizable. Las pantallas lo colocan dentro de un contenedor
// `flex flex-col lg:flex-row h-screen`.
export default function Sidebar({ onBeforeNavigate }) {
  const [stats, setStats] = useState(null)
  const [abierto, setAbierto] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { tema, alternar } = useTema()
  const botonMenu = useRef(null)
  const panel = useRef(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await api.get('/auth/stats')
        setStats(res.data)
      } catch (err) {
        console.error("Error fetching stats", err)
      }
    }
    fetchStats()
  }, [])

  // Panel móvil: Esc lo cierra, el foco entra al abrir y vuelve al botón al cerrar.
  useEffect(() => {
    if (!abierto) return
    const alPulsar = (e) => { if (e.key === 'Escape') setAbierto(false) }
    document.addEventListener('keydown', alPulsar)
    panel.current?.querySelector('button')?.focus()
    const boton = botonMenu.current
    return () => { document.removeEventListener('keydown', alPulsar); boton?.focus?.() }
  }, [abierto])

  const ir = async (ruta, state) => {
    if (onBeforeNavigate && !(await onBeforeNavigate())) return
    setAbierto(false)
    navigate(ruta, state ? { state } : undefined)
  }

  const handleLogout = async () => {
    if (onBeforeNavigate && !(await onBeforeNavigate())) return
    await supabase.auth.signOut()
  }

  const level = stats?.level
  const racha = stats?.racha ?? 0
  const userStats = stats?.stats

  const contenido = (
    <>
      <Marca />

      {stats && (
        <>
          <div className="bg-surface-2/50 rounded-2xl p-4 border border-line mb-4">
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-bold text-fg-muted uppercase tracking-widest">{level.nombre}</span>
              <span className="text-xs font-bold text-accent-text" aria-hidden="true">{level.icono}</span>
            </div>
            <div className="h-2 w-full bg-line rounded-full overflow-hidden mb-2"
              role="progressbar" aria-label="Progreso hacia el siguiente nivel"
              aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(level.progreso * 100)}>
              <div className="h-full bg-accent transition-all duration-1000" style={{ width: `${level.progreso * 100}%` }} />
            </div>
            <div className="flex justify-between items-center text-xs text-fg-subtle font-bold">
              <span>{userStats.puntos} PTS</span>
              <span>Siguiente nivel</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-6">
            <div className="bg-surface-2/30 p-3 rounded-xl border border-line flex flex-col items-center">
              <Flame className={`w-5 h-5 mb-1 ${racha > 0 ? 'text-warning' : 'text-fg-subtle'}`} aria-hidden="true" />
              <span className="text-xs font-bold">{racha} Días</span>
              <span className="text-xs uppercase text-fg-subtle font-bold">Racha</span>
            </div>
            <div className="bg-surface-2/30 p-3 rounded-xl border border-line flex flex-col items-center">
              <Target className="w-5 h-5 text-accent-text mb-1" aria-hidden="true" />
              <span className="text-xs font-bold">{userStats.docs_generados}</span>
              <span className="text-xs uppercase text-fg-subtle font-bold">Docs</span>
            </div>
          </div>
        </>
      )}

      <nav aria-label="Navegación principal" className="flex-1 space-y-2">
        <NavItem icon={<LayoutDashboard />} label="Dashboard" active={location.pathname === '/'} onClick={() => ir('/')} />
        <NavItem icon={<FilePlus />} label="Nueva Unidad" onClick={() => ir('/', { nuevo: 'unidad' })} />
        <NavItem icon={<FilePlus />} label="Nueva Sesión" onClick={() => ir('/', { nuevo: 'sesion' })} />
        <NavItem icon={<BookOpen />} label="Ejemplos" active={location.pathname === '/ejemplos'} onClick={() => ir('/ejemplos')} />
        <NavItem icon={<Settings />} label="Perfil institucional" active={location.pathname === '/institucion'} onClick={() => ir('/institucion')} />
      </nav>

      <div className="mt-auto pt-4 space-y-1">
        <button
          onClick={alternar}
          className="w-full flex items-center gap-3 text-fg-muted hover:text-fg font-medium transition-colors p-2 rounded-lg"
        >
          {tema === 'dark' ? <Sun className="w-5 h-5" aria-hidden="true" /> : <Moon className="w-5 h-5" aria-hidden="true" />}
          <span>{tema === 'dark' ? 'Tema claro' : 'Tema oscuro'}</span>
        </button>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 text-fg-muted hover:text-danger-text font-medium transition-colors p-2 rounded-lg"
        >
          <LogOut className="w-5 h-5" aria-hidden="true" />
          <span>Cerrar Sesión</span>
        </button>
      </div>
    </>
  )

  return (
    <>
      {/* Barra superior (móvil / tablet) */}
      <header className="lg:hidden shrink-0 flex items-center gap-3 border-b border-line bg-surface px-4 py-3">
        <button ref={botonMenu} type="button" onClick={() => setAbierto(true)}
          aria-label="Abrir menú" aria-expanded={abierto} aria-controls="menu-movil"
          className="p-2 -ml-2 rounded-lg text-fg-muted hover:text-fg hover:bg-surface-2">
          <Menu size={22} aria-hidden="true" />
        </button>
        <span className="font-bold">IA-GEN-EDU</span>
      </header>

      {/* Columna fija (escritorio) */}
      <aside className="hidden lg:flex w-72 h-screen bg-surface border-r border-line flex-col p-6 sticky top-0 overflow-y-auto shrink-0">
        {contenido}
      </aside>

      {/* Panel deslizable (móvil / tablet) */}
      {abierto && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div ref={panel} id="menu-movil" role="dialog" aria-modal="true" aria-label="Menú principal"
            className="relative w-72 max-w-[85vw] h-full bg-surface border-r border-line flex flex-col p-6 overflow-y-auto">
            <button type="button" onClick={() => setAbierto(false)} aria-label="Cerrar menú"
              className="absolute top-4 right-4 p-2 rounded-lg text-fg-muted hover:text-fg hover:bg-surface-2">
              <X size={20} aria-hidden="true" />
            </button>
            {contenido}
          </div>
          <button type="button" aria-label="Cerrar menú" tabIndex={-1} onClick={() => setAbierto(false)}
            className="flex-1 bg-black/50 cursor-default" />
        </div>
      )}
    </>
  )
}

function Marca() {
  return (
    <div className="flex items-center gap-3 mb-8 pr-8 lg:pr-0">
      <div className="w-10 h-10 bg-accent rounded-xl flex items-center justify-center shrink-0">
        <GraduationCap className="text-white w-6 h-6" aria-hidden="true" />
      </div>
      <div>
        <h2 className="font-bold text-lg leading-tight">IA-GEN-EDU</h2>
        <span className="text-xs text-fg-subtle font-medium">Planificación curricular</span>
      </div>
    </div>
  )
}

function NavItem({ icon, label, active = false, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
      className={`w-full text-left flex items-center justify-between p-3 rounded-xl transition-all group ${active ? 'bg-accent text-white' : 'hover:bg-surface-2 text-fg-muted hover:text-fg'}`}
    >
      <div className="flex items-center gap-3">
        {React.cloneElement(icon, { size: 20, 'aria-hidden': true })}
        <span className="font-semibold text-sm">{label}</span>
      </div>
      <ChevronRight size={14} aria-hidden="true" className={`transition-transform ${active ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100 group-hover:translate-x-1'}`} />
    </button>
  )
}
