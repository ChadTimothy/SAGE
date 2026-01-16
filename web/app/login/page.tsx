"use client";

import { Suspense, useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/chat";
  const error = searchParams.get("error");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(
    error === "CredentialsSignin" ? "Invalid email or password" : null
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setLoginError(null);

    try {
      const result = await signIn("credentials", {
        email,
        password,
        redirect: false,
        callbackUrl,
      });

      if (result?.error) {
        setLoginError("Invalid email or password");
      } else if (result?.ok) {
        router.push(callbackUrl);
      }
    } catch {
      setLoginError("An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md p-8 space-y-6 bg-gray-900 rounded-lg border border-gray-800">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-white">Welcome to SAGE</h1>
        <p className="text-gray-400 mt-2">Sign in to continue learning</p>
      </div>

      {loginError && (
        <div className="p-3 text-sm text-red-400 bg-red-900/20 border border-red-800 rounded">
          {loginError}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-gray-300"
          >
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="mt-1 w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-gray-300"
          >
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="mt-1 w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Your password"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white font-medium rounded transition-colors"
        >
          {isLoading ? "Signing in..." : "Sign in"}
        </button>
      </form>

      <p className="text-center text-sm text-gray-400">
        Don&apos;t have an account?{" "}
        <Link
          href="/register"
          className="text-blue-400 hover:text-blue-300 font-medium"
        >
          Create one
        </Link>
      </p>
    </div>
  );
}

function LoginLoading() {
  return (
    <div className="w-full max-w-md p-8 space-y-6 bg-gray-900 rounded-lg border border-gray-800">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-white">Welcome to SAGE</h1>
        <p className="text-gray-400 mt-2">Loading...</p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <Suspense fallback={<LoginLoading />}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
