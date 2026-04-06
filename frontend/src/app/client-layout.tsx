"use client";
import { AuthProvider } from "@/lib/auth";
import Navbar from "@/components/Navbar";
import { ReactNode } from "react";

export default function ClientLayout({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <Navbar />
      <main className="flex-1">{children}</main>
      <footer className="border-t border-gray-800 bg-gray-950 py-6 text-center text-xs text-gray-500">
        CTFLab UIT &mdash; NT140 Network Security &mdash; University of Information Technology
      </footer>
    </AuthProvider>
  );
}
