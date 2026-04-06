"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import BoxCard from "@/components/BoxCard";

interface Challenge {
  id: number;
  points: number;
}

interface Box {
  slug: string;
  title: string;
  description: string;
  difficulty?: string;
  challenges: Challenge[];
}

export default function BoxesPage() {
  const [boxes, setBoxes] = useState<Box[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getBoxes()
      .then((data) => {
        setBoxes(Array.isArray(data) ? data : data.boxes || []);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Failed to load boxes";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-100">Boxes</h1>
        <p className="mt-2 text-gray-400">
          Choose a vulnerable machine to hack. Each box contains one or more challenges.
        </p>
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

      {!loading && !error && boxes.length === 0 && (
        <div className="rounded-md border border-gray-800 bg-gray-900/50 px-6 py-12 text-center">
          <p className="text-gray-400">No boxes available yet. Check back later.</p>
        </div>
      )}

      {!loading && !error && boxes.length > 0 && (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {boxes.map((box) => (
            <BoxCard key={box.slug} box={box} />
          ))}
        </div>
      )}
    </div>
  );
}
