/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  basePath: '/calrims',
  trailingSlash: true,
  devIndicators: {
    appIsrStatus: false,
    buildActivity: false,
    buildActivityPosition: 'bottom-right',
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async redirects() {
    return [
      // Redirect bare root (e.g. localhost:3000) → /calrims/
      // basePath:false means this runs BEFORE basePath is applied
      {
        source: '/',
        destination: '/calrims/',
        permanent: false,
        basePath: false,
      },
    ]
  },
  async rewrites() {
    return [
      {
        source: '/api/((?!generate-pdf|health).*)',
        destination: 'http://localhost:10000/api/:1',
      },
    ]
  }
}
export default nextConfig
