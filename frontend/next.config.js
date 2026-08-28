/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  skipTrailingSlashRedirect: true,
  experimental: {
    // Next 14 rewrites 代理默认 30s 掐断到后端的连接（ECONNRESET，浏览器 500 而后端 200）。
    // 长请求已改 202+轮询，这里只兜底未异步化的慢接口（解析/检索等），3 分钟 > nginx proxy_read_timeout 300s 内的常规慢调用。
    proxyTimeout: 180000,
  },
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
