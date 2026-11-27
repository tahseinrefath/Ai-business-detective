/** @type {import('next').NextConfig} */
const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:5000";
const isStaticExport = process.env.NEXT_OUTPUT_EXPORT === "true";

const nextConfig = {
  ...(isStaticExport ? { output: "export", trailingSlash: true } : {}),
  images: { unoptimized: true },
  ...(!isStaticExport
    ? {
        async rewrites() {
          return [
            { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
            { source: "/avatar/:path*", destination: `${backendUrl}/avatar/:path*` },
          ];
        },
      }
    : {}),
};

export default nextConfig;
