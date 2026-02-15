"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      let data: any;
      if (isRegister) {
        data = await auth.register(email, name, password);
      } else {
        data = await auth.login(email, password);
      }

      // Store token and user info
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user_name", data.name);
      localStorage.setItem("user_email", data.email);
      localStorage.setItem("user_role", data.role);

      router.push("/");
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 -mt-20">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-primary-700">RFP Automation</h1>
          <p className="text-gray-500 mt-2">Enterprise RFP/RFI Response Platform</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">
            {isRegister ? "Create an Account" : "Sign In"}
          </h2>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                  placeholder="John Doe"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                placeholder="you@company.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none"
                placeholder="Enter your password"
                minLength={6}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary-600 text-white py-2.5 rounded-lg hover:bg-primary-700 text-sm font-medium disabled:opacity-50 transition"
            >
              {loading ? "Please wait..." : isRegister ? "Create Account" : "Sign In"}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-500">
            {isRegister ? (
              <>
                Already have an account?{" "}
                <button
                  onClick={() => { setIsRegister(false); setError(""); }}
                  className="text-primary-600 hover:underline font-medium"
                >
                  Sign In
                </button>
              </>
            ) : (
              <>
                Don&apos;t have an account?{" "}
                <button
                  onClick={() => { setIsRegister(true); setError(""); }}
                  className="text-primary-600 hover:underline font-medium"
                >
                  Create Account
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
