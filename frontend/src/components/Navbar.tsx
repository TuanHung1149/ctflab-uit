"use client";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { useState } from "react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-800 bg-gray-950/95 backdrop-blur supports-[backdrop-filter]:bg-gray-950/80">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <span className="text-xl font-bold text-cyan-400">CTFLab</span>
          <span className="text-xl font-bold text-gray-100">UIT</span>
        </Link>

        {/* Desktop Links */}
        <div className="hidden items-center gap-6 md:flex">
          <Link
            href="/boxes"
            className="text-sm font-medium text-gray-300 transition-colors hover:text-cyan-400"
          >
            Boxes
          </Link>
          {user && (
            <Link
              href="/dashboard"
              className="text-sm font-medium text-gray-300 transition-colors hover:text-cyan-400"
            >
              Dashboard
            </Link>
          )}
          <Link
            href="/scoreboard"
            className="text-sm font-medium text-gray-300 transition-colors hover:text-cyan-400"
          >
            Scoreboard
          </Link>
        </div>

        {/* Right Side */}
        <div className="hidden items-center gap-4 md:flex">
          {user ? (
            <>
              <span className="text-sm text-green-400">{user.username}</span>
              <button
                onClick={logout}
                className="rounded-md border border-gray-700 px-3 py-1.5 text-sm text-gray-300 transition-colors hover:border-red-500 hover:text-red-400"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-md border border-gray-700 px-3 py-1.5 text-sm text-gray-300 transition-colors hover:border-cyan-500 hover:text-cyan-400"
              >
                Login
              </Link>
              <Link
                href="/register"
                className="rounded-md bg-cyan-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-cyan-500"
              >
                Register
              </Link>
            </>
          )}
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="inline-flex items-center justify-center rounded-md p-2 text-gray-400 hover:text-gray-100 md:hidden"
          aria-label="Toggle menu"
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {menuOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile Menu */}
      {menuOpen && (
        <div className="border-t border-gray-800 md:hidden">
          <div className="space-y-1 px-4 py-3">
            <Link href="/boxes" className="block rounded-md px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 hover:text-cyan-400" onClick={() => setMenuOpen(false)}>
              Boxes
            </Link>
            {user && (
              <Link href="/dashboard" className="block rounded-md px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 hover:text-cyan-400" onClick={() => setMenuOpen(false)}>
                Dashboard
              </Link>
            )}
            <Link href="/scoreboard" className="block rounded-md px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 hover:text-cyan-400" onClick={() => setMenuOpen(false)}>
              Scoreboard
            </Link>
            {user ? (
              <button onClick={logout} className="block w-full rounded-md px-3 py-2 text-left text-sm text-red-400 hover:bg-gray-800">
                Logout ({user.username})
              </button>
            ) : (
              <>
                <Link href="/login" className="block rounded-md px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 hover:text-cyan-400" onClick={() => setMenuOpen(false)}>
                  Login
                </Link>
                <Link href="/register" className="block rounded-md px-3 py-2 text-sm text-cyan-400 hover:bg-gray-800" onClick={() => setMenuOpen(false)}>
                  Register
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
