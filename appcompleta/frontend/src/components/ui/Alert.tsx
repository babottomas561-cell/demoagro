import clsx from 'clsx'
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from 'lucide-react'

type AlertVariant = 'info' | 'warning' | 'danger' | 'success'

interface AlertProps {
  variant?: AlertVariant
  title?: string
  children: React.ReactNode
  className?: string
}

const config: Record<AlertVariant, { icon: React.ElementType; styles: string }> = {
  info: { icon: Info, styles: 'border-info/25 bg-[linear-gradient(180deg,rgba(93,127,165,0.08),rgba(255,255,255,0.88))] text-info' },
  warning: { icon: AlertTriangle, styles: 'border-warning/25 bg-[linear-gradient(180deg,rgba(214,159,47,0.10),rgba(255,255,255,0.88))] text-warning' },
  danger: { icon: AlertCircle, styles: 'border-danger/25 bg-[linear-gradient(180deg,rgba(207,110,99,0.10),rgba(255,255,255,0.88))] text-danger' },
  success: { icon: CheckCircle2, styles: 'border-accent/25 bg-[linear-gradient(180deg,rgba(48,148,90,0.09),rgba(255,255,255,0.88))] text-accent' },
}

export function Alert({ variant = 'info', title, children, className }: AlertProps) {
  const { icon: Icon, styles } = config[variant]
  return (
    <div className={clsx('flex gap-3 rounded-[1.35rem] border p-4 shadow-[0_1px_0_rgba(24,20,12,0.03)]', styles, className)}>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/70">
        <Icon className="h-4 w-4" />
      </div>
      <div className="text-sm">
        {title && <p className="mb-1 font-semibold">{title}</p>}
        <div className="opacity-90">{children}</div>
      </div>
    </div>
  )
}
