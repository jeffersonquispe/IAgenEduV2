import React, { useState, useEffect } from 'react'
import { Trophy, Flame, Target, Award, LogOut, ChevronRight, LayoutDashboard, FilePlus, Settings } from 'lucide-react'
import { api } from '../lib/api'
import { supabase } from '../lib/supabaseClient'

export default function Sidebar() {
  const [stats, setStats] = useState(null)

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

  const handleLogout = async () => {
    await supabase.auth.signOut()
  }

  if (!stats) return <div className="w-72 h-screen bg-slate-900 border-r border-slate-800 animate-pulse" />

  const { level, racha, stats: userStats } = stats

  return (
    <div className="w-72 h-screen bg-slate-900/50 backdrop-blur-xl border-r border-slate-800 flex flex-col p-6 sticky top-0 overflow-y-auto">
      {/* User Branding */}
      <div className="flex items-center gap-3 mb-10">
        <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <Trophy className="text-white w-6 h-6" />
        </div>
        <div>
          <h2 className="font-bold text-lg leading-tight">Master Panel</h2>
          <span className="text-xs text-indigo-400 font-semibold tracking-wider">PREMIUM</span>
        </div>
      </div>

      {/* GamificationCard */}
      <div className="bg-slate-800/50 rounded-2xl p-4 border border-slate-700/50 mb-8">
        <div className="flex justify-between items-center mb-3">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">{level.nombre}</span>
          <span className="text-xs font-bold text-indigo-400">{level.icono}</span>
        </div>
        <div className="h-2 w-full bg-slate-700 rounded-full overflow-hidden mb-2">
          <div 
            className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 transition-all duration-1000" 
            style={{ width: `${level.progreso * 100}%` }}
          />
        </div>
        <div className="flex justify-between items-center text-[10px] text-slate-500 font-bold">
          <span>{userStats.puntos} PTS</span>
          <span>Next Lvl</span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mb-8">
        <div className="bg-slate-800/30 p-3 rounded-xl border border-slate-700/30 flex flex-col items-center">
          <Flame className={`w-5 h-5 mb-1 ${racha > 0 ? 'text-orange-500 animate-bounce' : 'text-slate-600'}`} />
          <span className="text-xs font-bold">{racha} Días</span>
          <span className="text-[9px] uppercase text-slate-500 font-bold">Racha</span>
        </div>
        <div className="bg-slate-800/30 p-3 rounded-xl border border-slate-700/30 flex flex-col items-center">
          <Target className="w-5 h-5 text-indigo-400 mb-1" />
          <span className="text-xs font-bold">{userStats.docs_generados}</span>
          <span className="text-[9px] uppercase text-slate-500 font-bold">Docs</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-2">
        <NavItem icon={<LayoutDashboard />} label="Dashboard" active />
        <NavItem icon={<FilePlus />} label="Nueva Unidad" />
        <NavItem icon={<FilePlus />} label="Nueva Sesión" />
        <NavItem icon={<Award />} label="Mis Badges" />
        <NavItem icon={<Settings />} label="Ajustes" />
      </nav>

      {/* Logout */}
      <button 
        onClick={handleLogout}
        className="mt-auto flex items-center gap-3 text-slate-400 hover:text-red-400 font-medium transition-colors p-2"
      >
        <LogOut className="w-5 h-5" />
        <span>Cerrar Sesión</span>
      </button>
    </div>
  )
}

function NavItem({ icon, label, active = false }) {
  return (
    <div className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all group ${active ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' : 'hover:bg-slate-800 text-slate-400'}`}>
      <div className="flex items-center gap-3">
        {React.cloneElement(icon, { size: 20 })}
        <span className="font-semibold text-sm">{label}</span>
      </div>
      <ChevronRight size={14} className={`transition-transform ${active ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 group-hover:translate-x-1'}`} />
    </div>
  )
}
