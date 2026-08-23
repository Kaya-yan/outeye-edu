/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  skipTrailingSlashRedirect: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  async redirects() {
    return [
      { source: '/analysis', destination: '/', permanent: false },
      { source: '/projects', destination: '/history', permanent: false },
      { source: '/resources', destination: '/materials', permanent: false },
      { source: '/knowledge', destination: '/materials', permanent: false },
      { source: '/courseware', destination: '/history', permanent: false },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
