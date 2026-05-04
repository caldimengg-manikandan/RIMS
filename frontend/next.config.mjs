/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // basePath: '/calrims',
  trailingSlash: true,
  devIndicators: {
    appIsrStatus: false,
    buildActivity: false,
    buildActivityPosition: 'bottom-right',
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    unoptimized: true,
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

