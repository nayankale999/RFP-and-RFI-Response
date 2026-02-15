"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [userName, setUserName] = useState("");

  const isLoginPage = pathname === "/login";

  useEffect(() => {
    const token = localStorage.getItem("token");
    const name = localStorage.getItem("user_name") || "";
    setUserName(name);

    if (!token && !isLoginPage) {
      router.replace("/login");
      return;
    }

    setReady(true);
  }, [pathname, isLoginPage, router]);

  function handleLogout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user_name");
    localStorage.removeItem("user_email");
    localStorage.removeItem("user_role");
    router.replace("/login");
  }

  // Show nothing while checking auth (prevents flash)
  if (!ready && !isLoginPage) {
    return (
      <html lang="en">
        <body className="min-h-screen bg-gray-50" />
      </html>
    );
  }

  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        {!isLoginPage && (
          <nav className="bg-white border-b border-gray-200 px-6 py-3">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
              <a href="/" className="text-xl font-bold text-primary-700">
                RFP Automation
              </a>
              <div className="flex items-center gap-4">
                <a href="/projects" className="text-sm text-gray-600 hover:text-primary-600">
                  Projects
                </a>
                <span className="text-sm text-gray-400">|</span>
                <span className="text-sm text-gray-600">{userName}</span>
                <button
                  onClick={handleLogout}
                  className="text-sm text-red-500 hover:text-red-700 font-medium"
                >
                  Logout
                </button>
              </div>
            </div>
          </nav>
        )}
        <main className={isLoginPage ? "" : "max-w-7xl mx-auto px-6 py-8"}>{children}</main>
      </body>
    </html>
  );
}
