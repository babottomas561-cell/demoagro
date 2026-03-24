import clsx from 'clsx'

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  size?: 'sm' | 'md'
  dot?: boolean
  className?: string
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-surface text-text border-border',
  success: 'bg-primary-50 text-primary-700 border-primary-100',
  warning: 'bg-[rgba(169,123,47,0.08)] text-[rgba(133,97,29,1)] border-[rgba(169,123,47,0.14)]',
  danger: 'bg-[rgba(207,110,99,0.08)] text-[rgba(169,92,84,1)] border-[rgba(207,110,99,0.14)]',
  info: 'bg-[rgba(93,127,165,0.08)] text-[rgba(78,108,141,1)] border-[rgba(93,127,165,0.14)]',
  neutral: 'bg-surface text-text-muted border-border',
}

const dotColors: Record<BadgeVariant, string> = {
  default: 'bg-text-muted',
  success: 'bg-accent',
  warning: 'bg-warning',
  danger: 'bg-danger',
  info: 'bg-info',
  neutral: 'bg-text-subtle',
}

export function Badge({ children, variant = 'default', size = 'sm', dot, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        {
          'px-2 py-0.5 text-2xs': size === 'sm',
          'px-2.5 py-1 text-xs': size === 'md',
        },
        variantStyles[variant],
        className
      )}
    >
      {dot && (
        <span className={clsx('h-1.5 w-1.5 rounded-full', dotColors[variant])} />
      )}
      {children}
    </span>
  )
}
