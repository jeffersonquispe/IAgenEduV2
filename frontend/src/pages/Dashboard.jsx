import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import GenerationWizard from '../components/GenerationWizard'
import { Sparkles, ArrowRight, BookOpen, Clock, Download, FileText } from 'lucide-react'
import { api } from '../lib/api'

export default function Dashboard({ user }) {
  const navigate = useNavigate()
  const [wizard, setWizard] = useState({ open: false, type: 'unidad' })
  const [recentDocs, setRecentDocs] = useState([])
  const [loadingDocs, setLoadingDocs] = useState(true)

  const fetchRecentDocs = async () => {
    try {
      const res = await api.get('/data/documents')
      setRecentDocs(res.data)
    } catch (err) {
      console.error("Error fetching docs", err)
    } finally {
      setLoadingDocs(false)
    }
  }

  useState(() => {
    fetchRecentDocs()
  }, [])

  const handleComplete = (data) => {
    navigate('/editor', { state: { content: data } })
  }

  return (
    <div className="flex h-screen bg-dark">
      <Sidebar />
      
      <main className="flex-1 overflow-y-auto p-10">
        <header className="mb-12 flex justify-between items-end">
          <div>
            <h1 className="text-4xl font-bold mb-2">¡Hola Maestro! 👋</h1>
            <p className="text-slate-400 text-lg">Asistente Generador de Documentos Docentes</p>
          </div>
          <div className="flex gap-4">
            <div className="bg-indigo-500/10 border border-indigo-500/20 px-4 py-2 rounded-2xl flex items-center gap-2">
              <Sparkles className="text-indigo-400 w-5 h-5" />
              <span className="text-indigo-400 font-bold uppercase tracking-tight text-sm">IA Ready</span>
            </div>
          </div>
        </header>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          <ActionCard 
            title="Unidad Didáctica"
            desc="Genera una planificación curricular completa con metas, competencias y secuencia de sesiones."
            icon={<BookOpen className="w-10 h-10 text-indigo-400" />}
            color="border-indigo-500/30"
            onClick={() => setWizard({ open: true, type: 'unidad' })}
          />
          <ActionCard 
            title="Sesión de Aprendizaje"
            desc="Crea el detalle de una clase específica, incluyendo actividades de inicio, desarrollo y cierre."
            icon={<Clock className="w-10 h-10 text-emerald-400" />}
            color="border-emerald-500/30"
            onClick={() => setWizard({ open: true, type: 'sesion' })}
          />
        </div>

        {/* Recent Activity (Placeholder) */}
        <section>
          <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
            Recientes
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping"></span>
          </h2>
          <div className="space-y-4">
            {loadingDocs ? (
               <div className="flex justify-center p-12">
                 <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
               </div>
            ) : recentDocs.length > 0 ? (
              recentDocs.map(doc => (
                <div 
                  key={doc.id} 
                  onClick={() => navigate('/editor', { state: { content: doc.content } })}
                  className="glass p-5 rounded-2xl flex items-center justify-between hover:bg-slate-800/80 transition-all border border-slate-700/50 cursor-pointer group"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-slate-900 rounded-xl flex items-center justify-center">
                      <FileText className="text-slate-500 group-hover:text-indigo-400 transition-colors" size={20} />
                    </div>
                    <div>
                      <h3 className="font-bold">{doc.title}</h3>
                      <p className="text-xs text-slate-500 font-medium">
                        {doc.type.toUpperCase()} • {new Date(doc.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <button className="bg-slate-800 p-2 rounded-lg opacity-0 group-hover:opacity-100 transition-all">
                    <ArrowRight size={18} />
                  </button>
                </div>
              ))
            ) : (
              <div className="text-center p-12 bg-slate-800/20 rounded-3xl border border-dashed border-slate-700">
                <p className="text-slate-500">Aún no has generado documentos. ¡Comienza uno ahora!</p>
              </div>
            )}
          </div>
        </section>

        <GenerationWizard 
          isOpen={wizard.open} 
          type={wizard.type} 
          onClose={() => setWizard({ ...wizard, open: false })}
          onComplete={handleComplete}
        />
      </main>
    </div>
  )
}

function ActionCard({ title, desc, icon, color, onClick }) {
  return (
    <div 
      onClick={onClick}
      className={`p-8 rounded-3xl bg-slate-800/40 border ${color} hover:bg-slate-800/60 transition-all cursor-pointer group relative overflow-hidden`}
    >
      <div className="mb-6">{icon}</div>
      <h3 className="text-2xl font-bold mb-3">{title}</h3>
      <p className="text-slate-400 line-clamp-2 mb-6 group-hover:text-slate-300 transition-colors">{desc}</p>
      <div className="flex items-center gap-2 text-indigo-400 font-bold group-hover:translate-x-2 transition-transform">
        <span>Comenzar</span>
        <ArrowRight size={18} />
      </div>
      <div className="absolute -top-10 -right-10 w-32 h-32 bg-indigo-500/10 blur-3xl rounded-full"></div>
    </div>
  )
}
