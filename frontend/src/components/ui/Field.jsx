import { useId } from 'react'

const CONTROL = 'w-full bg-surface border border-line rounded-xl px-4 py-2 text-fg placeholder:text-fg-subtle focus:outline-none focus:border-accent transition-colors'

// Etiqueta asociada al control (htmlFor/id), para lectores de pantalla y clic en la etiqueta.
export function InputField({ label, ...props }) {
  const id = useId()
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-sm font-bold text-fg-muted">{label}</label>
      <input id={id} className={CONTROL} {...props} />
    </div>
  )
}

export function SelectField({ label, options, ...props }) {
  const id = useId()
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-sm font-bold text-fg-muted">{label}</label>
      <select id={id} className={CONTROL} {...props}>
        <option value="" disabled>Selecciona una opción...</option>
        {options.map((opt, i) => (
          <option key={i} value={typeof opt === 'object' ? opt.value : opt}>
            {typeof opt === 'object' ? opt.label : opt}
          </option>
        ))}
      </select>
    </div>
  )
}
