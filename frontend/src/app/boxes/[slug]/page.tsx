"use client";
import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import InstancePanel from "@/components/InstancePanel";
import FlagSubmitForm from "@/components/FlagSubmitForm";

interface Challenge {
  id: number;
  order: number;
  title: string;
  points: number;
  description?: string;
}

interface PortMapping {
  container_port: number;
  protocol: string;
  description?: string;
}

interface Box {
  slug: string;
  title: string;
  description: string;
  difficulty?: string;
  challenges: Challenge[];
  port_mappings?: PortMapping[];
}

interface Instance {
  id: number;
  status: string;
  container_ip: string;
  expires_at: string;
  box_slug: string;
}

interface Submission {
  challenge_id: number;
  correct: boolean;
}

export default function BoxDetailPage() {
  const params = useParams();
  const slug = params.slug as string;
  const { user } = useAuth();

  const [box, setBox] = useState<Box | null>(null);
  const [instance, setInstance] = useState<Instance | null>(null);
  const [solvedIds, setSolvedIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [launching, setLaunching] = useState(false);
  const [launchError, setLaunchError] = useState("");

  // Fetch box details
  useEffect(() => {
    api
      .getBox(slug)
      .then(setBox)
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Failed to load box";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, [slug]);

  // Fetch user's instances and submissions
  const fetchUserData = useCallback(async () => {
    if (!user) return;
    try {
      const instances = await api.getInstances();
      const list: Instance[] = Array.isArray(instances)
        ? instances
        : instances.instances || [];
      const active = list.find(
        (i: Instance) =>
          i.box_slug === slug &&
          (i.status === "running" || i.status === "starting")
      );
      setInstance(active || null);
    } catch {
      // Silently fail on instance fetch
    }

    try {
      const subs = await api.getSubmissions();
      const list: Submission[] = Array.isArray(subs)
        ? subs
        : subs.submissions || [];
      const solved = new Set(
        list.filter((s: Submission) => s.correct).map((s: Submission) => s.challenge_id)
      );
      setSolvedIds(solved);
    } catch {
      // Silently fail on submissions fetch
    }
  }, [user, slug]);

  useEffect(() => {
    fetchUserData();
  }, [fetchUserData]);

  // Poll instance status every 5s
  useEffect(() => {
    if (!user || !instance) return;
    const interval = setInterval(async () => {
      try {
        const updated = await api.getInstance(instance.id);
        setInstance(updated);
      } catch {
        setInstance(null);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [user, instance]);

  const handleLaunch = async () => {
    setLaunching(true);
    setLaunchError("");
    try {
      const newInstance = await api.createInstance(slug);
      setInstance(newInstance);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to launch instance";
      setLaunchError(msg);
    } finally {
      setLaunching(false);
    }
  };

  const handleDestroy = () => {
    setInstance(null);
  };

  const handleReset = async () => {
    if (!instance) return;
    try {
      const updated = await api.getInstance(instance.id);
      setInstance(updated);
    } catch {
      // Silently fail
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
      </div>
    );
  }

  if (error || !box) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error || "Box not found"}
        </div>
      </div>
    );
  }

  const sortedChallenges = [...box.challenges].sort(
    (a, b) => a.order - b.order
  );

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-100">{box.title}</h1>
            {box.difficulty && (
              <span
                className={`mt-2 inline-block rounded-full border px-3 py-1 text-xs font-medium ${getDifficultyColor(box.difficulty)}`}
              >
                {box.difficulty}
              </span>
            )}
          </div>
        </div>
        <p className="mt-4 text-gray-400 leading-relaxed">{box.description}</p>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Challenges Table */}
          <div className="rounded-lg border border-gray-800 bg-gray-900/50 overflow-hidden">
            <div className="border-b border-gray-800 px-5 py-3">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
                Challenges
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-left text-xs uppercase text-gray-500">
                    <th className="px-5 py-3 font-medium">#</th>
                    <th className="px-5 py-3 font-medium">Title</th>
                    <th className="px-5 py-3 font-medium">Points</th>
                    {user && instance && instance.status === "running" && (
                      <th className="px-5 py-3 font-medium">Flag</th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {sortedChallenges.map((challenge) => (
                    <tr
                      key={challenge.id}
                      className="border-b border-gray-800/50 last:border-b-0"
                    >
                      <td className="px-5 py-3 text-gray-500">
                        {challenge.order}
                      </td>
                      <td className="px-5 py-3 text-gray-100">
                        {challenge.title}
                        {challenge.description && (
                          <p className="mt-0.5 text-xs text-gray-500">
                            {challenge.description}
                          </p>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <span className="text-cyan-400">{challenge.points}</span>
                        <span className="text-gray-600"> pts</span>
                      </td>
                      {user && instance && instance.status === "running" && (
                        <td className="px-5 py-3">
                          <FlagSubmitForm
                            challengeId={challenge.id}
                            solved={solvedIds.has(challenge.id)}
                          />
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Port Mappings */}
          {box.port_mappings && box.port_mappings.length > 0 && (
            <div className="rounded-lg border border-gray-800 bg-gray-900/50 overflow-hidden">
              <div className="border-b border-gray-800 px-5 py-3">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
                  Port Mappings
                </h2>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-left text-xs uppercase text-gray-500">
                    <th className="px-5 py-3 font-medium">Port</th>
                    <th className="px-5 py-3 font-medium">Protocol</th>
                    <th className="px-5 py-3 font-medium">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {box.port_mappings.map((pm, i) => (
                    <tr
                      key={i}
                      className="border-b border-gray-800/50 last:border-b-0"
                    >
                      <td className="px-5 py-3 font-mono text-cyan-400">
                        {pm.container_port}
                      </td>
                      <td className="px-5 py-3 uppercase text-gray-400">
                        {pm.protocol}
                      </td>
                      <td className="px-5 py-3 text-gray-400">
                        {pm.description || "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {user ? (
            instance ? (
              <InstancePanel
                instance={instance}
                onDestroy={handleDestroy}
                onReset={handleReset}
              />
            ) : (
              <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-5">
                <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">
                  Instance
                </h3>
                <p className="mb-4 text-sm text-gray-400">
                  Launch an instance to start hacking this box.
                </p>
                {launchError && (
                  <div className="mb-3 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                    {launchError}
                  </div>
                )}
                <button
                  onClick={handleLaunch}
                  disabled={launching}
                  className="w-full rounded-md bg-green-600 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-green-500 disabled:opacity-50"
                >
                  {launching ? "Launching..." : "Launch Instance"}
                </button>
              </div>
            )
          ) : (
            <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-5">
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">
                Instance
              </h3>
              <p className="text-sm text-gray-400">
                Please{" "}
                <a href="/login" className="text-cyan-400 hover:text-cyan-300">
                  login
                </a>{" "}
                to launch an instance and submit flags.
              </p>
            </div>
          )}

          {/* Box Stats */}
          <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-5">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">
              Info
            </h3>
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Challenges</dt>
                <dd className="text-gray-100">{box.challenges.length}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Total Points</dt>
                <dd className="text-cyan-400">
                  {box.challenges.reduce((s, c) => s + c.points, 0)}
                </dd>
              </div>
              {user && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Solved</dt>
                  <dd className="text-green-400">
                    {box.challenges.filter((c) => solvedIds.has(c.id)).length} /{" "}
                    {box.challenges.length}
                  </dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}

function getDifficultyColor(difficulty: string): string {
  switch (difficulty.toLowerCase()) {
    case "easy":
      return "text-green-400 border-green-400/30 bg-green-400/10";
    case "medium":
      return "text-yellow-400 border-yellow-400/30 bg-yellow-400/10";
    case "hard":
      return "text-red-400 border-red-400/30 bg-red-400/10";
    case "insane":
      return "text-purple-400 border-purple-400/30 bg-purple-400/10";
    default:
      return "text-gray-400 border-gray-400/30 bg-gray-400/10";
  }
}
