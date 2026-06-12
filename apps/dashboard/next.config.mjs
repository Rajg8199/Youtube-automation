/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    WORKER_URL: process.env.WORKER_URL ?? "http://localhost:8000",
  },
};

export default nextConfig;
