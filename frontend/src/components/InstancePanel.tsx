"use client";
import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";

interface Instance {
  id: number;
  status: string;
  container_ip: string;
  expires_at: string;
}

interface InstancePanelProps {
  instance: Instance;
  onDestroy: () => void;
  onReset: () => void;
}

function getStatusBadge(status: string) {
  switch (status) {
    case "running":
      return { text: "Running", cls: "bg-green-500/10 text-green-400 border-green-500/30" };
    case "starting":
      return { text: "Starting", cls: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30" };
    case "stopping":
      return { text: "Stopping", cls: "bg-orange-500/10 text-orange-400 border-orange-500/30" };
    case "error":
      return { text: "Error", cls: "bg-red-500/10 text-red-400 border-red-500/30" };
    default:
      return { text: status, cls: "bg-gray-500/10 text-gray-400 border-gray-500/30" };
  }
}

function formatTimeRemaining(expiresAt: string): string {
  const diff = new Date(expiresAt).getTime() - Date.now();
  if (diff <= 0) return "Expired";
  const hours = Math.floor(diff / 3600000);
  const minutes = Math.floor((diff % 3600000) / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);
  if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

export default function InstancePanel({ instance, onDestroy, onReset }: InstancePanelProps) {
  const [timeLeft, setTimeLeft] = useState(formatTimeRemaining(instance.expires_at));
  const [confirmDestroy, setConfirmDestroy] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setTimeLeft(formatTimeRemaining(instance.expires_at));
    }, 1000);
    return () => clearInterval(interval);
  }, [instance.expires_at]);

  const handleDownloadVpn = useCallback(async () => {
    setDownloading(true);
    try {
      const data = await api.getVpnConfig(instance.id);
      const blob = new Blob([data.config || data.vpn_config || JSON.stringify(data)], {
        type: "application/x-openvpn-profile",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ctflab-${instance.id}.ovpn`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // VPN download error is handled silently
    } finally {
      setDownloading(false);
    }
  }, [instance.id]);

  const handleReset = useCallback(async () => {
    setResetting(true);
    try {
      await api.resetInstance(instance.id);
      onReset();
    } catch {
      // Reset error
    } finally {
      setResetting(false);
    }
  }, [instance.id, onReset]);

  const handleDestroy = useCallback(async () => {
    try {
      await api.deleteInstance(instance.id);
      onDestroy();
    } catch {
      // Destroy error
    }
  }, [instance.id, onDestroy]);

  const badge = getStatusBadge(instance.status);

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
          Instance
        </h3>
        <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${badge.cls}`}>
          {badge.text}
        </span>
      </div>

      <div className="space-y-3">
        <div>
          <span className="text-xs text-gray-500">Container IP</span>
          <p className="font-mono text-sm text-cyan-400">
            {instance.container_ip || "Pending..."}
          </p>
        </div>

        <div>
          <span className="text-xs text-gray-500">Time Remaining</span>
          <p className="font-mono text-sm text-yellow-400">{timeLeft}</p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          onClick={handleDownloadVpn}
          disabled={downloading}
          className="rounded-md bg-cyan-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-cyan-500 disabled:opacity-50"
        >
          {downloading ? "Downloading..." : "Download VPN"}
        </button>
        <button
          onClick={handleReset}
          disabled={resetting}
          className="rounded-md border border-yellow-600 px-3 py-1.5 text-xs font-medium text-yellow-400 transition-colors hover:bg-yellow-600/10 disabled:opacity-50"
        >
          {resetting ? "Resetting..." : "Reset"}
        </button>
        {confirmDestroy ? (
          <div className="flex gap-1">
            <button
              onClick={handleDestroy}
              className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-red-500"
            >
              Confirm
            </button>
            <button
              onClick={() => setConfirmDestroy(false)}
              className="rounded-md border border-gray-700 px-3 py-1.5 text-xs font-medium text-gray-400 transition-colors hover:border-gray-600"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmDestroy(true)}
            className="rounded-md border border-red-600 px-3 py-1.5 text-xs font-medium text-red-400 transition-colors hover:bg-red-600/10"
          >
            Destroy
          </button>
        )}
      </div>
    </div>
  );
}
