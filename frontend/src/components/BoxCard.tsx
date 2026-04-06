"use client";
import Link from "next/link";

interface BoxCardProps {
  box: {
    slug: string;
    title: string;
    description: string;
    challenges: { id: number; points: number }[];
    difficulty?: string;
  };
}

function getDifficultyColor(difficulty?: string): string {
  switch (difficulty?.toLowerCase()) {
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

export default function BoxCard({ box }: BoxCardProps) {
  const totalPoints = box.challenges.reduce((sum, c) => sum + c.points, 0);
  const flagCount = box.challenges.length;

  return (
    <Link href={`/boxes/${box.slug}`}>
      <div className="group relative rounded-lg border border-gray-800 bg-gray-900/50 p-5 transition-all hover:border-cyan-500/50 hover:bg-gray-900">
        <div className="mb-3 flex items-start justify-between">
          <h3 className="text-lg font-semibold text-gray-100 group-hover:text-cyan-400 transition-colors">
            {box.title}
          </h3>
          {box.difficulty && (
            <span
              className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${getDifficultyColor(box.difficulty)}`}
            >
              {box.difficulty}
            </span>
          )}
        </div>
        <p className="mb-4 line-clamp-2 text-sm text-gray-400">
          {box.description}
        </p>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
            </svg>
            {flagCount} challenge{flagCount !== 1 ? "s" : ""}
          </span>
          <span className="flex items-center gap-1">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {totalPoints} pts
          </span>
        </div>
        <div className="mt-4 text-xs font-medium text-cyan-500 opacity-0 transition-opacity group-hover:opacity-100">
          View Details &rarr;
        </div>
      </div>
    </Link>
  );
}
