"use client";
import { useState, useCallback } from "react";
import { api } from "@/lib/api";

interface FlagSubmitFormProps {
  challengeId: number;
  solved: boolean;
}

export default function FlagSubmitForm({ challengeId, solved }: FlagSubmitFormProps) {
  const [flag, setFlag] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [isSolved, setIsSolved] = useState(solved);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!flag.trim() || isSolved) return;

      setSubmitting(true);
      setMessage(null);
      try {
        const result = await api.submitFlag(challengeId, flag.trim());
        if (result.correct) {
          setMessage({ type: "success", text: "Correct flag! Well done!" });
          setIsSolved(true);
        } else {
          setMessage({ type: "error", text: "Incorrect flag. Try again." });
        }
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : "Submission failed";
        setMessage({ type: "error", text: errorMsg });
      } finally {
        setSubmitting(false);
      }
    },
    [flag, challengeId, isSolved]
  );

  if (isSolved) {
    return (
      <div className="flex items-center gap-2 text-sm text-green-400">
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
        Solved
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input
        type="text"
        value={flag}
        onChange={(e) => setFlag(e.target.value)}
        placeholder="Enter flag..."
        className="w-48 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-100 placeholder-gray-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
        disabled={submitting}
      />
      <button
        type="submit"
        disabled={submitting || !flag.trim()}
        className="rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-green-500 disabled:opacity-50"
      >
        {submitting ? "..." : "Submit"}
      </button>
      {message && (
        <span
          className={`text-xs ${message.type === "success" ? "text-green-400" : "text-red-400"}`}
        >
          {message.text}
        </span>
      )}
    </form>
  );
}
