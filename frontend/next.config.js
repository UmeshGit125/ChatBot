/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // Speed up compilation
  swcMinify: true,
  // Reduce unnecessary type checking during dev
  typescript: {
    ignoreBuildErrors: false,
  },
  // Optimize package imports for large libraries
  experimental: {
    optimizePackageImports: ['recharts', 'lucide-react'],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL
          ? `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`
          : 'http://127.0.0.1:8001/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
