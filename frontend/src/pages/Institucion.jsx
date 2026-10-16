import { useEffect, useId, useRef, useState } from 'react'
import Sidebar from '../components/Sidebar'
import { InputField as Field } from '../components/ui/Field'
import { Building2, Save, UploadCloud, CheckCircle2, Trash2, Loader2 } from 'lucide-react'
import { api } from '../lib/api'
import { toast, confirmar, mensajeDeError } from '../lib/notify'

// HU-31: perfil institucional del docente (persistente, reutilizable en
// todas sus generaciones). HU-48: subida de la plantilla .docx (silueta)
// institucional para Unidad/Sesión — cada vez que el docente quiera cambiar
// el formato, puede volver aquí y subir un archivo nuevo.
// HU-47: campos del encabezado de control documentario (mismos nombres que el backend).
const CONTROL_VACIO = {
  red: '', version: '', aprobado_por: '', fecha_aprobacion: '', revisado_por: '', fecha_revision: '',
}

export default function Institucion() {
  const [control, setControl] = useState(CONTROL_VACIO)
  const teniaControl = useRef(false)   // si ya había control guardado, vaciarlo también debe guardarse
  const [perfil, setPerfil] = useState({
    nombre_institucion: '', nivel_modalidad: '', dre_ugel: '', coordinacion_pedagogica: '',
    vision: '', mision: '', contexto_relevante: '',
    valores_institucionales: '', enfoques_transversales: '',
  })
  const [presets, setPresets] = useState([])   // HU-36: listas de valores sugeridas
  const [loadingPerfil, setLoadingPerfil] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savedAt, setSavedAt] = useState(null)

  const [plantillas, setPlantillas] = useState({ unidad: null, sesion: null })
  const [subiendo, setSubiendo] = useState({ unidad: false, sesion: false })
  const [errorPlantilla, setErrorPlantilla] = useState({ unidad: '', sesion: '' })

  useEffect(() => {
    api.get('/institucion')
      .then(res => {
        const p = res.data
        setPerfil({
          nombre_institucion: p.nombre_institucion || '',
          nivel_modalidad: p.nivel_modalidad || '',
          dre_ugel: p.dre_ugel || '',
          coordinacion_pedagogica: p.coordinacion_pedagogica || '',
          vision: p.vision || '',
          mision: p.mision || '',
          contexto_relevante: p.contexto_relevante || '',
          valores_institucionales: (p.valores_institucionales || []).join(', '),
          enfoques_transversales: (p.enfoques_transversales || []).join(', '),
        })
        const c = p.control_documentario || {}
        teniaControl.current = Object.values(c).some(Boolean)
        setControl({ ...CONTROL_VACIO, ...Object.fromEntries(Object.entries(c).map(([k, v]) => [k, v || ''])) })
      })
      .catch(() => {}) // 404 = sin perfil configurado aún, se queda con los valores por defecto
      .finally(() => setLoadingPerfil(false))

    api.get('/institucion/presets-valores')
      .then(res => setPresets(res.data || []))
      .catch(() => {}) // sin presets, el campo de valores se sigue pudiendo escribir a mano

    for (const tipo of ['unidad', 'sesion']) {
      api.get(`/institucion/plantilla/${tipo}`)
        .then(res => setPlantillas(pl => ({ ...pl, [tipo]: res.data })))
        .catch(() => {}) // 404 = sin plantilla activa para este tipo
    }
  }, [])

  const handleChange = e => setPerfil({ ...perfil, [e.target.name]: e.target.value })
  const handleControl = e => setControl({ ...control, [e.target.name]: e.target.value })

  const handleGuardar = async () => {
    setSaving(true)
    try {
      const payload = {
        ...perfil,
        valores_institucionales: perfil.valores_institucionales
          ? perfil.valores_institucionales.split(',').map(v => v.trim()).filter(Boolean)
          : null,
        enfoques_transversales: perfil.enfoques_transversales
          ? perfil.enfoques_transversales.split(',').map(v => v.trim()).filter(Boolean)
          : null,
      }
      // HU-47: solo se envía el control documentario si tiene datos o si había uno guardado
      // (así guardar el perfil no toca esa columna para quien no la usa).
      if (Object.values(control).some(v => v.trim()) || teniaControl.current) {
        payload.control_documentario = control
        teniaControl.current = Object.values(control).some(v => v.trim())
      }
      await api.put('/institucion', payload)
      setSavedAt(new Date())
    } catch (err) {
      toast.error('Error al guardar el perfil institucional: ' + mensajeDeError(err))
    } finally {
      setSaving(false)
    }
  }

  const handleSubirPlantilla = async (tipo, file) => {
    if (!file) return
    setSubiendo(s => ({ ...s, [tipo]: true }))
    setErrorPlantilla(e => ({ ...e, [tipo]: '' }))
    try {
      const formData = new FormData()
      formData.append('tipo', tipo)
      formData.append('archivo', file)
      const res = await api.post('/institucion/plantilla', formData)
      setPlantillas(pl => ({ ...pl, [tipo]: res.data }))
    } catch (err) {
      setErrorPlantilla(e => ({ ...e, [tipo]: err.response?.data?.detail || 'Error al subir la plantilla' }))
    } finally {
      setSubiendo(s => ({ ...s, [tipo]: false }))
    }
  }

  const handleQuitarPlantilla = async (tipo) => {
    const seguir = await confirmar({
      titulo: 'Quitar plantilla',
      mensaje: 'Se dejará de usar la plantilla institucional subida. ¿Quitarla?',
      confirmar: 'Quitar',
      peligro: true,
    })
    if (!seguir) return
    try {
      await api.delete(`/institucion/plantilla/${tipo}`)
      setPlantillas(pl => ({ ...pl, [tipo]: null }))
    } catch (err) {
      toast.error('Error al quitar la plantilla: ' + mensajeDeError(err))
    }
  }

  return (
    <div className="flex flex-col lg:flex-row h-screen bg-bg">
      <Sidebar />
      <main className="flex-1 min-h-0 overflow-y-auto p-5 sm:p-8 lg:p-10 max-w-4xl">
        <header className="mb-10 flex items-center gap-4">
          <div className="w-12 h-12 bg-accent rounded-2xl flex items-center justify-center">
            <Building2 className="text-white w-6 h-6" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Perfil institucional</h1>
            <p className="text-fg-muted">Se usa para contextualizar tus documentos y, si subes una plantilla, para adaptar su formato exacto.</p>
          </div>
        </header>

        {!loadingPerfil && (
          <section className="glass p-8 rounded-3xl border border-line space-y-5 mb-10">
            <div className="grid grid-cols-2 gap-5">
              <Field label="Nombre de la institución" name="nombre_institucion" value={perfil.nombre_institucion} onChange={handleChange} placeholder="Ej. CEP Salesiano" />
              <Field label="Nivel / Modalidad" name="nivel_modalidad" value={perfil.nivel_modalidad} onChange={handleChange} placeholder="Ej. Secundaria" />
              <Field label="DRE / UGEL" name="dre_ugel" value={perfil.dre_ugel} onChange={handleChange} placeholder="Ej. UGEL Cusco" />
              <Field label="Coordinación pedagógica" name="coordinacion_pedagogica" value={perfil.coordinacion_pedagogica} onChange={handleChange} placeholder="Ej. Prof. Juana Martínez" />
            </div>
            <TextAreaField label="Visión institucional" name="vision" value={perfil.vision} onChange={handleChange} />
            <TextAreaField label="Misión institucional" name="mision" value={perfil.mision} onChange={handleChange} />
            <TextAreaField
              label="Contexto relevante de tus estudiantes"
              name="contexto_relevante"
              value={perfil.contexto_relevante}
              onChange={handleChange}
              placeholder="Zona urbana/rural, características de los estudiantes, enfoque institucional..."
            />
            <div className="grid grid-cols-2 gap-5">
              <Field
                label="Valores institucionales (separados por coma)"
                name="valores_institucionales"
                value={perfil.valores_institucionales}
                onChange={handleChange}
                placeholder="Ej. Respeto, Solidaridad, Fe"
              />
              <Field
                label="Enfoques transversales (separados por coma)"
                name="enfoques_transversales"
                value={perfil.enfoques_transversales}
                onChange={handleChange}
                placeholder="Ej. Enfoque ambiental, Enfoque de derechos"
              />
            </div>
            <p className="text-xs text-fg-subtle italic">
              Si dejas estos campos vacíos, tus documentos usan los valores genéricos del CNEB/MINEDU por defecto.
            </p>
            {presets.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="text-fg-subtle">Cargar una lista sugerida de valores:</span>
                {presets.map(p => (
                  <button
                    key={p.id}
                    type="button"
                    title={p.descripcion}
                    onClick={() => setPerfil(pf => ({ ...pf, valores_institucionales: p.valores.join(', ') }))}
                    className="px-3 py-1 rounded-full border border-line text-fg hover:border-accent hover:underline transition-colors"
                  >
                    {p.nombre}
                  </button>
                ))}
                <span className="text-fg-subtle">(rellena el campo; puedes editarlo antes de guardar)</span>
              </div>
            )}

            <fieldset className="border-t border-line pt-5 space-y-4">
              <legend className="text-lg font-bold">Control documentario</legend>
              <p className="text-xs text-fg-subtle">
                Encabezado de tus PDF y DOCX (nombre del formato, versión, aprobado y revisado por, páginas).
                Si dejas todos los campos vacíos, el encabezado no se agrega.
              </p>
              <div className="grid grid-cols-3 gap-5">
                <Field label="Red / institución en el encabezado" name="red" maxLength={80} value={control.red} onChange={handleControl} placeholder="Ej. Red Salesiana de Escuelas" />
                <Field label="Versión" name="version" maxLength={20} value={control.version} onChange={handleControl} placeholder="Ej. 02" />
                <span />
                <Field label="Aprobado por" name="aprobado_por" maxLength={80} value={control.aprobado_por} onChange={handleControl} placeholder="Ej. Dirección General" />
                <Field label="Fecha de aprobación" name="fecha_aprobacion" maxLength={40} value={control.fecha_aprobacion} onChange={handleControl} placeholder="Ej. 15/03/2026" />
                <span />
                <Field label="Revisado por" name="revisado_por" maxLength={80} value={control.revisado_por} onChange={handleControl} placeholder="Ej. Equipo pedagógico" />
                <Field label="Fecha de revisión" name="fecha_revision" maxLength={40} value={control.fecha_revision} onChange={handleControl} placeholder="Ej. 10/03/2026" />
              </div>
            </fieldset>

            <div className="flex items-center gap-4 pt-2">
              <button
                onClick={handleGuardar}
                disabled={saving}
                className="bg-accent hover:bg-accent-hover text-white px-6 py-2.5 rounded-xl transition-all flex items-center gap-2 font-bold disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save size={18} />}
                Guardar perfil
              </button>
              {savedAt && (
                <span className="text-success-text text-sm flex items-center gap-1">
                  <CheckCircle2 size={16} /> Guardado {savedAt.toLocaleTimeString()}
                </span>
              )}
            </div>
          </section>
        )}

        <section className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold mb-1">Plantilla institucional</h2>
            <p className="text-fg-muted text-sm">
              Sube el formato .docx en blanco (silueta) de tu institución. La generación y exportación seguirán exactamente su estructura.
              Puedes reemplazarla cuando quieras — no afecta documentos ya generados con la versión anterior.
            </p>
          </div>

          <PlantillaUploader
            tipo="unidad"
            titulo="Unidad Didáctica"
            plantilla={plantillas.unidad}
            subiendo={subiendo.unidad}
            error={errorPlantilla.unidad}
            onSubir={file => handleSubirPlantilla('unidad', file)}
            onQuitar={() => handleQuitarPlantilla('unidad')}
          />
          <PlantillaUploader
            tipo="sesion"
            titulo="Sesión de Aprendizaje"
            plantilla={plantillas.sesion}
            subiendo={subiendo.sesion}
            error={errorPlantilla.sesion}
            onSubir={file => handleSubirPlantilla('sesion', file)}
            onQuitar={() => handleQuitarPlantilla('sesion')}
          />
        </section>
      </main>
    </div>
  )
}

function PlantillaUploader({ titulo, plantilla, subiendo, error, onSubir, onQuitar }) {
  return (
    <div className="glass p-6 rounded-2xl border border-line flex items-center justify-between gap-6">
      <div className="flex-1">
        <h3 className="font-bold text-lg mb-1">{titulo}</h3>
        {plantilla ? (
          <p className="text-sm text-success-text flex items-center gap-2">
            <CheckCircle2 size={16} /> Plantilla activa: {plantilla.nombre_archivo}
          </p>
        ) : (
          <p className="text-sm text-fg-subtle">Sin plantilla — se usa la estructura estándar del sistema.</p>
        )}
        {error && <p className="text-sm text-danger-text mt-1">{error}</p>}
      </div>
      <div className="flex items-center gap-3">
        {plantilla && (
          <button onClick={onQuitar} className="p-2 text-fg-muted hover:text-danger-text transition-colors" title="Quitar plantilla" aria-label={`Quitar plantilla de ${titulo}`}>
            <Trash2 size={18} />
          </button>
        )}
        <label className="bg-surface-2 hover:bg-line px-4 py-2 rounded-xl transition-all flex items-center gap-2 font-bold cursor-pointer text-sm focus-within:outline focus-within:outline-2 focus-within:outline-accent">
          {subiendo ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud size={18} />}
          {plantilla ? 'Reemplazar .docx' : 'Subir .docx'}
          <input
            type="file"
            accept=".docx"
            className="sr-only"
            disabled={subiendo}
            onChange={e => onSubir(e.target.files?.[0])}
          />
        </label>
      </div>
    </div>
  )
}

function TextAreaField({ label, ...props }) {
  const id = useId()
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-sm font-bold text-fg-muted">{label}</label>
      <textarea id={id} rows={3} className="w-full bg-surface border border-line rounded-xl px-4 py-2 text-fg placeholder:text-fg-subtle focus:outline-none focus:border-accent transition-colors resize-none" {...props} />
    </div>
  )
}
