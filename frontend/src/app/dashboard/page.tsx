"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Link from "next/link";

interface Instance {
  id: number;
  status: string;
  container_ip: string;
  expires_at: string;
  box_slug: string;
}

interface Submission {
  id: number;
  challenge_id: number;
  challenge_title?: string;
  flag: string;
  correct: boolean;
  created_at: string;
}

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [instances, setInstances] = useState<Instance[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (!user) return;

    const fetchData = async () => {
      try {
        const [instData, subData] = await Promise.all([
          api.getInstances(),
          api.getSubmissions(),
        ]);
        const instList: Instance[] = Array.isArray(instData)
          ? instData
          : instData.instances || [];
        const subList: Submission[] = Array.isArray(subData)
          ? subData
          : subData.submissions || [];
        setInstances(instList);
        setSubmissions(subList);
      } catch {
        // Silently handle
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user]);

  if (authLoading || !user) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
      </div>
    );
  }

  const activeInstances = instances.filter(
    (i) => i.status === "running" || i.status === "starting"
  );
  const correctSubs = submissions.filter((s) => s.correct);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="mb-8 text-3xl font-bold text-gray-100">Dashboard</h1>

      {/* Stats */}
      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-5">
          <p className="text-sm text-gray-500">Active Instances</p>
          <p className="mt-1 text-2xl font-bold text-cyan-400">
            {activeInstances.length}
          </p>
        </div>
        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-5">
          <p className="text-sm text-gray-500">Flags Captured</p>
          <p className="mt-1 text-2xl font-bold text-green-400">
            {correctSubs.length}
          </p>
        </div>
        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-5">
          <p className="text-sm text-gray-500">Total Submissions</p>
          <p className="mt-1 text-2xl font-bold text-gray-100">
            {submissions.length}
          </p>
        </div>
      </div>

      {/* Active Instances */}
      <div className="mb-8">
        <h2 className="mb-4 text-lg font-semibold text-gray-100">
          Active Instances
        </h2>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
          </div>
        ) : activeInstances.length === 0 ? (
          <div className="rounded-md border border-gray-800 bg-gray-900/50 px-6 py-8 text-center text-sm text-gray-400">
            No active instances.{" "}
            <Link href="/boxes" className="text-cyan-400 hover:text-cyan-300">
              Browse boxes
            </Link>{" "}
            to launch one.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-800">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 bg-gray-900/50 text-left text-xs uppercase text-gray-500">
                  <th className="px-5 py-3 font-medium">Box</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">IP</th>
                  <th className="px-5 py-3 font-medium">Expires</th>
                  <th className="px-5 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeInstances.map((inst) => (
                  <tr key={inst.id} className="border-b border-gray-800/50">
                    <td className="px-5 py-3">
                      <Link
                        href={`/boxes/${inst.box_slug}`}
                        className="text-cyan-400 hover:text-cyan-300"
                      >
                        {inst.box_slug}
                      </Link>
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`rounded-full border px-2 py-0.5 text-xs font-medium ${
                          inst.status === "running"
                            ? "border-green-500/30 bg-green-500/10 text-green-400"
                            : "border-yellow-500/30 bg-yellow-500/10 text-yellow-400"
                        }`}
                      >
                        {inst.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 font-mono text-sm text-gray-300">
                      {inst.container_ip || "Pending"}
                    </td>
                    <td className="px-5 py-3 text-gray-400">
                      {new Date(inst.expires_at).toLocaleString()}
                    </td>
                    <td className="px-5 py-3">
                      <Link
                        href={`/boxes/${inst.box_slug}`}
                        className="text-xs text-cyan-400 hover:text-cyan-300"
                      >
                        Open &rarr;
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Submissions */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-gray-100">
          Recent Submissions
        </h2>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
          </div>
        ) : submissions.length === 0 ? (
          <div className="rounded-md border border-gray-800 bg-gray-900/50 px-6 py-8 text-center text-sm text-gray-400">
            No submissions yet. Start solving challenges!
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-800">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 bg-gray-900/50 text-left text-xs uppercase text-gray-500">
                  <th className="px-5 py-3 font-medium">Challenge</th>
                  <th className="px-5 py-3 font-medium">Flag</th>
                  <th className="px-5 py-3 font-medium">Result</th>
                  <th className="px-5 py-3 font-medium">Time</th>
                </tr>
              </thead>
              <tbody>
                {submissions.slice(0, 20).map((sub) => (
                  <tr key={sub.id} className="border-b border-gray-800/50">
                    <td className="px-5 py-3 text-gray-100">
                      {sub.challenge_title || `Challenge #${sub.challenge_id}`}
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-gray-400">
                      {sub.flag.length > 30
                        ? sub.flag.substring(0, 30) + "..."
                        : sub.flag}
                    </td>
                    <td className="px-5 py-3">
                      {sub.correct ? (
                        <span className="flex items-center gap-1 text-green-400">
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Correct
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-red-400">
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                          Incorrect
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-gray-500">
                      {new Date(sub.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
