/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return {
      beforeFiles: [
        // Proxy API requests to backend, EXCEPT NextAuth routes
        // Note: Need both exact paths and wildcard paths for proper routing
        {
          source: "/api/learners",
          destination: "http://localhost:8000/api/learners",
        },
        {
          source: "/api/learners/:path*",
          destination: "http://localhost:8000/api/learners/:path*",
        },
        {
          source: "/api/sessions",
          destination: "http://localhost:8000/api/sessions",
        },
        {
          source: "/api/sessions/:path*",
          destination: "http://localhost:8000/api/sessions/:path*",
        },
        {
          source: "/api/practice/:path*",
          destination: "http://localhost:8000/api/practice/:path*",
        },
        {
          source: "/api/chat/:path*",
          destination: "http://localhost:8000/api/chat/:path*",
        },
        {
          source: "/api/voice/:path*",
          destination: "http://localhost:8000/api/voice/:path*",
        },
        {
          source: "/api/scenarios",
          destination: "http://localhost:8000/api/scenarios",
        },
        {
          source: "/api/scenarios/:path*",
          destination: "http://localhost:8000/api/scenarios/:path*",
        },
        {
          source: "/api/graph/:path*",
          destination: "http://localhost:8000/api/graph/:path*",
        },
        // Backend auth endpoints (login, register, sync) - NOT NextAuth
        {
          source: "/api/backend-auth/:path*",
          destination: "http://localhost:8000/api/auth/:path*",
        },
      ],
    };
  },
};

export default nextConfig;
