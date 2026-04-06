"use client";
import Link from "next/link";

export default function HomePage() {
  return (
    <div className="flex flex-1 flex-col">
      {/* Hero Section */}
      <section className="relative flex flex-col items-center justify-center px-4 py-24 sm:py-32">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute left-1/2 top-0 h-[500px] w-[500px] -translate-x-1/2 rounded-full bg-cyan-500/5 blur-3xl" />
          <div className="absolute right-0 top-1/4 h-[300px] w-[300px] rounded-full bg-green-500/5 blur-3xl" />
        </div>

        <div className="relative z-10 text-center">
          <h1 className="mb-4 text-5xl font-extrabold tracking-tight sm:text-6xl">
            <span className="text-cyan-400">CTFLab</span>{" "}
            <span className="text-gray-100">UIT</span>
          </h1>
          <p className="mb-2 text-2xl font-semibold text-green-400 sm:text-3xl">
            Hack. Learn. Compete.
          </p>
          <p className="mx-auto mb-10 max-w-2xl text-lg text-gray-400">
            Practice real-world cybersecurity skills in a safe, hands-on lab environment.
            Launch vulnerable machines, exploit them, and capture the flags.
            Built for NT140 students at UIT Vietnam.
          </p>
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/boxes"
              className="rounded-lg bg-cyan-600 px-8 py-3 text-lg font-semibold text-white transition-colors hover:bg-cyan-500"
            >
              Browse Boxes
            </Link>
            <Link
              href="/register"
              className="rounded-lg border border-gray-700 px-8 py-3 text-lg font-semibold text-gray-300 transition-colors hover:border-cyan-500 hover:text-cyan-400"
            >
              Get Started
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="mx-auto max-w-5xl px-4 py-16">
        <div className="grid gap-8 md:grid-cols-3">
          <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-6">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-400">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold text-gray-100">
              Launch Instances
            </h3>
            <p className="text-sm text-gray-400">
              Spin up isolated vulnerable machines with a single click. Each student gets their own private instance.
            </p>
          </div>

          <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-6">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-green-500/10 text-green-400">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold text-gray-100">
              Capture Flags
            </h3>
            <p className="text-sm text-gray-400">
              Find and submit hidden flags to prove you have exploited each vulnerability. Track your progress in real time.
            </p>
          </div>

          <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-6">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-yellow-500/10 text-yellow-400">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold text-gray-100">
              Compete
            </h3>
            <p className="text-sm text-gray-400">
              Climb the scoreboard and compare your skills with classmates. See who can solve the most challenges.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
