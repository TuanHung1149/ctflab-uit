"use client";
import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface ScoreEntry {
  rank: number;
  username: string;
  total_score: number;
  challenges_solved: number;
}

export default function ScoreboardPage() {
  const { user } = useAuth();
  const [entries, setEntries] = useState<ScoreEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchScoreboard = useCallback(async () => {
    try {
      const data = await api.getScoreboard();
      const list: ScoreEntry[] = Array.isArray(data)
        ? data
        : data.scoreboard || [];
      // Add rank if not present
      const ranked = list.map((entry, i) => ({
        ...entry,
        rank: entry.rank || i + 1,
      }));
      setEntries(ranked);
      setError("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load scoreboard";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScoreboard();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchScoreboard, 30000);
    return () => clearInterval(interval);
  }, [fetchScoreboard]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-100">Scoreboard</h1>
          <p className="mt-2 text-sm text-gray-400">
            Auto-refreshes every 30 seconds
          </p>
        </div>
        <button
          onClick={fetchScoreboard}
          className="rounded-md border border-gray-700 px-3 py-1.5 text-sm text-gray-300 transition-colors hover:border-cyan-500 hover:text-cyan-400"
        >
          Refresh
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {!loading && !error && entries.length === 0 && (
        <div className="rounded-md border border-gray-800 bg-gray-900/50 px-6 py-12 text-center">
          <p className="text-gray-400">
            No scores yet. Be the first to capture a flag!
          </p>
        </div>
      )}

      {!loading && !error && entries.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900/50 text-left text-xs uppercase text-gray-500">
                <th className="px-5 py-3 font-medium">Rank</th>
                <th className="px-5 py-3 font-medium">Username</th>
                <th className="px-5 py-3 font-medium text-right">Score</th>
                <th className="px-5 py-3 font-medium text-right">
                  Challenges Solved
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => {
                const isCurrentUser = user?.username === entry.username;
                return (
                  <tr
                    key={entry.username}
                    className={`border-b border-gray-800/50 last:border-b-0 ${
                      isCurrentUser
                        ? "bg-cyan-500/5 border-l-2 border-l-cyan-500"
                        : ""
                    }`}
                  >
                    <td className="px-5 py-3">
                      {entry.rank <= 3 ? (
                        <span
                          className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                            entry.rank === 1
                              ? "bg-yellow-500/20 text-yellow-400"
                              : entry.rank === 2
                                ? "bg-gray-400/20 text-gray-300"
                                : "bg-orange-500/20 text-orange-400"
                          }`}
                        >
                          {entry.rank}
                        </span>
                      ) : (
                        <span className="text-gray-500">{entry.rank}</span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={
                          isCurrentUser
                            ? "font-semibold text-cyan-400"
                            : "text-gray-100"
                        }
                      >
                        {entry.username}
                        {isCurrentUser && (
                          <span className="ml-2 text-xs text-gray-500">
                            (you)
                          </span>
                        )}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right font-mono text-cyan-400">
                      {entry.total_score}
                    </td>
                    <td className="px-5 py-3 text-right text-gray-400">
                      {entry.challenges_solved}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
