/** @type {import('next').NextConfig} */
const nextConfig = {
  async redirects() {
    return [
      { source: '/dashboard/:path*', destination: '/gerencia', permanent: false },
      { source: '/agricola/:path*', destination: '/produccion', permanent: false },
      { source: '/comercial/:path*', destination: '/comercial-exportacion', permanent: false },
      { source: '/finanzas/:path*', destination: '/gerencia', permanent: false },
      { source: '/stock/:path*', destination: '/gerencia', permanent: false },
      { source: '/maquinaria/:path*', destination: '/gerencia', permanent: false },
      { source: '/macro/:path*', destination: '/macro-mercado', permanent: false },
      { source: '/contexto/:path*', destination: '/macro-mercado', permanent: false },
    ]
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ]
  },
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
}

export default nextConfig
