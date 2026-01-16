/**
 * Next.js middleware for route protection.
 *
 * Redirects unauthenticated users to login for protected routes.
 */

import { withAuth } from "next-auth/middleware";
import { NextResponse } from "next/server";

export default withAuth(
  function middleware(req) {
    // Custom middleware logic can go here
    return NextResponse.next();
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        // Allow access if user has a valid token
        // OR if accessing public routes
        const publicPaths = ["/", "/login", "/register"];
        const isPublicPath = publicPaths.includes(req.nextUrl.pathname);

        return isPublicPath || !!token;
      },
    },
  }
);

// Specify which routes this middleware should run on
export const config = {
  matcher: [
    /*
     * Match all paths except:
     * - api/auth (NextAuth routes need to be accessible)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico
     * - public files (images, etc.)
     */
    "/((?!api/auth|_next/static|_next/image|favicon.ico|.*\\.png$|.*\\.svg$).*)",
  ],
};
