"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import type { User } from "@/lib/types";

interface UserHeaderProps {
  onRefresh?: () => void;
}

export function UserHeader({ onRefresh }: UserHeaderProps) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const stored = sessionStorage.getItem("bookclub_user");
    if (!stored) {
      router.replace("/");
      return;
    }
    setUser(JSON.parse(stored));
  }, [router]);

  async function handleRefresh() {
    setRefreshing(true);
    if (onRefresh) {
      await onRefresh();
    }
    // Small delay for visual feedback
    setTimeout(() => setRefreshing(false), 600);
  }

  if (!user) return null;

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-100 sticky top-0 z-40">
      <div className="flex items-center gap-2">
        <span className="text-2xl">{user.icon}</span>
        <span className="font-semibold text-gray-800 text-sm">
          {user.user_name} さん
        </span>
      </div>
      <button
        onClick={handleRefresh}
        className="p-2 rounded-full text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
        aria-label="更新"
      >
        <RefreshCw
          size={16}
          className={refreshing ? "animate-spin" : ""}
        />
      </button>
    </div>
  );
}
