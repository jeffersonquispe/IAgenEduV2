const VARIANTES = {
  primary: 'bg-accent hover:bg-accent-hover text-white',
  secondary: 'bg-surface-2 hover:bg-line text-fg border border-line',
  danger: 'bg-danger hover:bg-danger/90 text-white',
  success: 'bg-success hover:bg-success/90 text-white',
  ghost: 'text-fg-muted hover:text-fg hover:bg-surface-2',
}
const TAMANOS = { md: 'px-6 py-2', sm: 'px-3 py-1.5 text-sm' }

export default function Button({ variant = 'primary', size = 'md', className = '', type = 'button', ...props }) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-xl font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${VARIANTES[variant]} ${TAMANOS[size]} ${className}`}
      {...props}
    />
  )
}
