"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, Vote, History, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/books", label: "Books", icon: BookOpen, emoji: "📖" },
  { href: "/votes", label: "Votes", icon: Vote, emoji: "🗳️" },
  { href: "/memos", label: "Memo", icon: History, emoji: "📝" },
  { href: "/history", label: "History", icon: History, emoji: "📜" },
  { href: "/admin", label: "Admin", icon: Settings, emoji: "⚙️" },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 shadow-lg">
      <div
        className="flex items-stretch"
        style={{ paddingBottom: "calc(env(safe-area-inset-bottom) + 16px)" }}
      >
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "relative flex-1 flex flex-col items-center justify-center py-3 gap-1 min-h-[64px] transition-colors duration-150",
                isActive
                  ? "text-blue-600"
                  : "text-gray-400 hover:text-gray-600"
              )}
            >
              {isActive && (
                <span className="absolute top-0 left-2 right-2 h-[3px] bg-blue-600 rounded-b-full" />
              )}
              <span className="text-xl leading-none">{item.emoji}</span>
              <span
                className={cn(
                  "text-[10px] font-medium leading-tight",
                  isActive ? "text-blue-600" : "text-gray-400"
                )}
              >
                {item.label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
