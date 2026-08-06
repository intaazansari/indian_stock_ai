"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { User, Lock, CheckCircle, AlertCircle } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { useAuthStore } from "@/stores/useAuthStore";
import { cn } from "@/lib/utils";

// ── API helpers ───────────────────────────────────────────────────────────────

async function updateProfile(full_name: string) {
  const { data } = await apiClient.patch("/auth/me", { full_name });
  return data;
}

async function changePassword(current_password: string, new_password: string) {
  const { data } = await apiClient.post("/auth/me/change-password", {
    current_password,
    new_password,
  });
  return data;
}

// ── Toast component ───────────────────────────────────────────────────────────

function Toast({ message, type }: { message: string; type: "success" | "error" }) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 text-sm px-4 py-2.5 rounded-lg",
        type === "success"
          ? "bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-400 border border-green-100 dark:border-green-900/50"
          : "bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400 border border-red-100 dark:border-red-900/50"
      )}
    >
      {type === "success"
        ? <CheckCircle className="w-4 h-4 shrink-0" />
        : <AlertCircle className="w-4 h-4 shrink-0" />}
      {message}
    </div>
  );
}

// ── Section card wrapper ──────────────────────────────────────────────────────

function Card({ title, icon: Icon, children }: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 overflow-hidden">
      <div className="flex items-center gap-2.5 px-6 py-4 border-b border-gray-100 dark:border-gray-900">
        <Icon className="w-4 h-4 text-brand-500" />
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h2>
      </div>
      <div className="px-6 py-5">{children}</div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const setAuth = useAuthStore((s) => s.setAuth);

  // Profile form
  const [fullName, setFullName] = useState("");
  const [profileMsg, setProfileMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Password form
  const [pwForm, setPwForm] = useState({ current: "", next: "", confirm: "" });
  const [pwMsg, setPwMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login");
    } else if (user?.full_name) {
      setFullName(user.full_name);
    }
  }, [isAuthenticated, user, router]);

  // Profile mutation
  const profileMutation = useMutation({
    mutationFn: () => updateProfile(fullName.trim()),
    onSuccess: (data) => {
      // Sync updated name back into the auth store so the navbar shows it immediately
      if (user) {
        setAuth({ ...user, full_name: data.full_name }, {
          access_token: localStorage.getItem("access_token") ?? "",
          refresh_token: localStorage.getItem("refresh_token") ?? "",
          token_type: "bearer",
        });
      }
      setProfileMsg({ text: "Display name updated.", type: "success" });
    },
    onError: (err: any) => {
      setProfileMsg({
        text: err?.response?.data?.detail ?? "Failed to update profile.",
        type: "error",
      });
    },
  });

  // Password mutation
  const passwordMutation = useMutation({
    mutationFn: () => changePassword(pwForm.current, pwForm.next),
    onSuccess: () => {
      setPwMsg({ text: "Password changed successfully.", type: "success" });
      setPwForm({ current: "", next: "", confirm: "" });
    },
    onError: (err: any) => {
      setPwMsg({
        text: err?.response?.data?.detail ?? "Failed to change password.",
        type: "error",
      });
    },
  });

  const handleProfileSave = (e: React.FormEvent) => {
    e.preventDefault();
    setProfileMsg(null);
    if (!fullName.trim()) return setProfileMsg({ text: "Name cannot be empty.", type: "error" });
    profileMutation.mutate();
  };

  const handlePasswordSave = (e: React.FormEvent) => {
    e.preventDefault();
    setPwMsg(null);
    if (!pwForm.current) return setPwMsg({ text: "Enter your current password.", type: "error" });
    if (pwForm.next.length < 8) return setPwMsg({ text: "New password must be at least 8 characters.", type: "error" });
    if (pwForm.next !== pwForm.confirm) return setPwMsg({ text: "New passwords do not match.", type: "error" });
    passwordMutation.mutate();
  };

  if (!isAuthenticated) return null;

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Manage your account preferences
        </p>
      </div>

      {/* ── Account Info (read-only) ── */}
      <Card title="Account" icon={User}>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Email
            </label>
            <p className="text-sm text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-900 rounded-lg px-3 py-2 border border-gray-100 dark:border-gray-800">
              {user?.email ?? "—"}
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-600 mt-1">Email cannot be changed.</p>
          </div>
        </div>
      </Card>

      {/* ── Profile ── */}
      <Card title="Profile" icon={User}>
        <form onSubmit={handleProfileSave} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Display Name
            </label>
            <input
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Your name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>

          {profileMsg && <Toast message={profileMsg.text} type={profileMsg.type} />}

          <button
            type="submit"
            disabled={profileMutation.isPending}
            className="px-4 py-2 text-sm rounded-lg bg-brand-600 text-white font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {profileMutation.isPending ? "Saving…" : "Save Changes"}
          </button>
        </form>
      </Card>

      {/* ── Change Password ── */}
      <Card title="Change Password" icon={Lock}>
        <form onSubmit={handlePasswordSave} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              Current Password
            </label>
            <input
              type="password"
              autoComplete="current-password"
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              value={pwForm.current}
              onChange={(e) => setPwForm({ ...pwForm, current: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                New Password
              </label>
              <input
                type="password"
                autoComplete="new-password"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={pwForm.next}
                onChange={(e) => setPwForm({ ...pwForm, next: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Confirm New Password
              </label>
              <input
                type="password"
                autoComplete="new-password"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
                value={pwForm.confirm}
                onChange={(e) => setPwForm({ ...pwForm, confirm: e.target.value })}
              />
            </div>
          </div>

          {pwMsg && <Toast message={pwMsg.text} type={pwMsg.type} />}

          <button
            type="submit"
            disabled={passwordMutation.isPending}
            className="px-4 py-2 text-sm rounded-lg bg-brand-600 text-white font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {passwordMutation.isPending ? "Updating…" : "Update Password"}
          </button>
        </form>
      </Card>

      {/* ── Danger Zone ── */}
      <div className="rounded-xl border border-red-100 dark:border-red-900/30 bg-white dark:bg-gray-950 overflow-hidden">
        <div className="px-6 py-4 border-b border-red-100 dark:border-red-900/30">
          <h2 className="text-sm font-semibold text-red-600 dark:text-red-400">Danger Zone</h2>
        </div>
        <div className="px-6 py-5 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">Sign out of all devices</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Clears your local session immediately.
            </p>
          </div>
          <button
            onClick={() => {
              useAuthStore.getState().clearAuth();
              router.push("/login");
            }}
            className="px-4 py-2 text-sm rounded-lg border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
          >
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}
