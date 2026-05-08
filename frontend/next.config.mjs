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
      {
        source: '/',
        destination: '/calrims/',
        permanent: false,
        basePath: false,
      },
      {
        source: '/interview/:path*',
        destination: '/calrims/interview/:path*',
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
