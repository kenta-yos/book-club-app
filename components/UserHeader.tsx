"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import Image from "next/image";
import type { User } from "@/lib/types";

interface UserHeaderProps {
  onRefresh?: () => void;
}

export function UserHeader({ onRefresh }: UserHeaderProps) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const headerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem("bookclub_user");
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

  function handleScrollToTop() {
    const scrollContainer = headerRef.current?.parentElement;
    if (scrollContainer) {
      scrollContainer.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  if (!user) return null;

  return (
    <div ref={headerRef} className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-100 sticky top-0 z-40">
      <button
        onClick={handleScrollToTop}
        className="flex items-center gap-3 active:opacity-60 transition-opacity"
        aria-label="トップへ戻る"
      >
        <div className="flex items-center gap-1.5">
          <Image
            src="/icons/icon.png"
            alt="読書会"
            width={28}
            height={28}
            className="rounded-sm"
          />
          <span className="font-bold text-gray-800 text-sm">読書会</span>
        </div>
        <span className="text-gray-300">|</span>
        <div className="flex items-center gap-1.5">
          <span className="text-xl">{user.icon}</span>
          <span className="font-semibold text-gray-600 text-sm">
            {user.user_name} さん
          </span>
        </div>
      </button>
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
