/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // NOTE: do not inline WORKER_URL via `env` here — that bakes a build-time constant.
  // Server components read process.env.WORKER_URL at runtime (see lib/worker.ts).
};

export default nextConfig;
