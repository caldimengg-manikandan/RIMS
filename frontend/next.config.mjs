/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
<<<<<<< HEAD

=======
  basePath: '/calrims', // Uncomment for production deployment
>>>>>>> fc4804a20bddc1b90b757d331e68fafd991d0a6a
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
  experimental: {
    optimizePackageImports: [
      'lucide-react',
      '@radix-ui/react-icons',
      '@radix-ui/react-avatar',
      '@radix-ui/react-dialog',
      '@radix-ui/react-dropdown-menu',
      'framer-motion'
    ]
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:10000/api/:path*',
      },
    ]
  }
}

export default nextConfig
