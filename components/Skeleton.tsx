"use client";

import { cn } from "@/lib/utils";

// ── 基本スケルトンブロック ──────────────────────────────────────────
export function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={cn("skeleton-shimmer rounded-md", className)}
      style={style}
    />
  );
}

// ── Books ページ用 ──────────────────────────────────────────────────
export function BooksPageSkeleton() {
  return (
    <div className="px-4 pt-4 space-y-4">
      {/* Banner */}
      <Skeleton className="h-14 w-full rounded-xl" />
      {/* Action button */}
      <Skeleton className="h-10 w-full rounded-xl" />
      {/* Filter pills */}
      <div className="flex gap-2">
        {[80, 64, 72, 56].map((w, i) => (
          <Skeleton key={i} className={`h-7 rounded-full`} style={{ width: w }} />
        ))}
      </div>
      {/* Category header */}
      <Skeleton className="h-4 w-32 rounded" />
      {/* Book cards */}
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-white rounded-2xl border border-gray-100 p-4 shadow-sm space-y-3">
          <Skeleton className="h-5 w-3/4 rounded" />
          <Skeleton className="h-3 w-1/3 rounded" />
          <Skeleton className="h-9 w-full rounded-xl" />
        </div>
      ))}
    </div>
  );
}

// ── Votes ページ用 ──────────────────────────────────────────────────
export function VotesPageSkeleton() {
  return (
    <div className="px-4 pt-4 space-y-4">
      {/* Ranking */}
      <Skeleton className="h-5 w-24 rounded" />
      <div className="bg-white rounded-2xl border border-gray-100 p-3 shadow-sm space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center justify-between py-1">
            <Skeleton className="h-4 w-1/2 rounded" />
            <Skeleton className="h-6 w-10 rounded" />
          </div>
        ))}
      </div>
      {/* Vote cards */}
      <Skeleton className="h-5 w-16 rounded mt-2" />
      {[1, 2].map((i) => (
        <div key={i} className="bg-white rounded-2xl border border-gray-100 p-4 shadow-sm space-y-3">
          <Skeleton className="h-5 w-2/3 rounded" />
          <Skeleton className="h-3 w-1/3 rounded" />
          <Skeleton className="h-6 w-28 rounded-full" />
          <div className="flex gap-2">
            <Skeleton className="flex-1 h-10 rounded-xl" />
            <Skeleton className="flex-1 h-10 rounded-xl" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── History ページ用 ────────────────────────────────────────────────
export function HistoryPageSkeleton() {
  return (
    <div className="px-4 pt-4 space-y-4">
      <Skeleton className="h-5 w-24 rounded" />
      {/* Year pills */}
      <div className="flex gap-2">
        {[48, 48, 48, 56].map((w, i) => (
          <Skeleton key={i} className="h-7 rounded-full" style={{ width: w }} />
        ))}
      </div>
      {/* Event list */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex gap-3 p-4 border-b border-gray-50 last:border-0">
            <div className="w-24 space-y-1.5">
              <Skeleton className="h-3 w-20 rounded" />
              <Skeleton className="h-3 w-16 rounded" />
            </div>
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-3/4 rounded" />
              <Skeleton className="h-4 w-14 rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Admin ページ用 ──────────────────────────────────────────────────
export function AdminPageSkeleton() {
  return (
    <div className="px-4 pt-4 space-y-4">
      <Skeleton className="h-5 w-20 rounded" />
      {/* Card 1 */}
      <div className="bg-white rounded-2xl border border-gray-100 p-4 shadow-sm space-y-3">
        <Skeleton className="h-4 w-40 rounded" />
        <Skeleton className="h-8 w-full rounded-lg" />
        <Skeleton className="h-8 w-full rounded-lg" />
        <Skeleton className="h-10 w-full rounded-xl" />
      </div>
      {/* Card 2 */}
      <div className="bg-white rounded-2xl border border-gray-100 p-4 shadow-sm space-y-3">
        <Skeleton className="h-4 w-36 rounded" />
        <Skeleton className="h-8 w-full rounded-lg" />
        <Skeleton className="h-10 w-full rounded-xl" />
      </div>
    </div>
  );
}
