import type { Metadata } from 'next'
import './globals.css'
import { AppShell } from '@/components/layout/AppShell'

export const metadata: Metadata = {
  title: { default: 'Lemon BI', template: '%s · Lemon BI' },
  description: 'Plataforma de inteligencia operativa y comercial para negocio limonero',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  )
}
