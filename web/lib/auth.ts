/**
 * NextAuth.js configuration for SAGE authentication.
 *
 * Supports:
 * - Credentials (email/password) authentication
 * - OAuth providers can be added later (Google, GitHub, etc.)
 *
 * JWT contains: sub (user_id), learner_id, email, name
 */

import type { NextAuthOptions, User } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

// Extend the built-in types to include learner_id
declare module "next-auth" {
  interface User {
    learner_id: string;
  }

  interface Session {
    user: {
      id: string;
      learner_id: string;
      email: string;
      name: string;
    };
    accessToken: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id: string;
    learner_id: string;
    email: string;
    name: string;
  }
}

// Backend auth endpoints are proxied through Next.js at /api/backend-auth/*
const BACKEND_AUTH_URL = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api/auth`
  : "http://localhost:8000/api/auth";

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        try {
          const response = await fetch(`${BACKEND_AUTH_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          });

          if (!response.ok) {
            return null;
          }

          const user = await response.json();
          return {
            id: user.id,
            email: user.email,
            name: user.name,
            learner_id: user.learner_id,
          };
        } catch (error) {
          console.error("Auth error:", error);
          return null;
        }
      },
    }),
  ],

  callbacks: {
    async jwt({ token, user }) {
      // Initial sign in - copy user data to token
      if (user) {
        token.id = user.id;
        token.learner_id = user.learner_id;
        token.email = user.email || "";
        token.name = user.name || "";
      }
      return token;
    },

    async session({ session, token }) {
      // Include custom fields in session
      session.user = {
        id: token.id,
        learner_id: token.learner_id,
        email: token.email,
        name: token.name,
      };

      // Create access token for API calls
      // This is the same JWT that the backend will verify
      session.accessToken = token.sub || "";

      return session;
    },
  },

  pages: {
    signIn: "/login",
    error: "/login",
  },

  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },

  jwt: {
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },

  secret: process.env.NEXTAUTH_SECRET,
};

/**
 * Get the JWT token for API requests.
 * This is used by API clients to include the Authorization header.
 *
 * The token is the NextAuth session token which contains the user's
 * id, learner_id, email, and name - all needed by the backend.
 */
export async function getAuthToken(): Promise<string | null> {
  // This function is only available on the client side
  if (typeof window === "undefined") {
    return null;
  }

  try {
    // Get the raw session token from the cookie
    // NextAuth stores it as next-auth.session-token (or __Secure- prefix in production)
    const cookies = document.cookie.split(";");
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split("=");
      if (
        name === "next-auth.session-token" ||
        name === "__Secure-next-auth.session-token"
      ) {
        return decodeURIComponent(value);
      }
    }
    return null;
  } catch {
    return null;
  }
}
