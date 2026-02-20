"use client";

import { useRef } from "react";
import { usePullToRefresh } from "@/hooks/usePullToRefresh";
import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface PullToRefreshWrapperProps {
  onRefresh: () => Promise<void>;
  children: React.ReactNode;
  className?: string;
}

export function PullToRefreshWrapper({
  onRefresh,
  children,
  className,
}: PullToRefreshWrapperProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { pullDistance, isPastThreshold, isRefreshing } = usePullToRefresh(
    containerRef,
    { onRefresh, threshold: 72, maxPull: 110 }
  );

  const indicatorVisible = pullDistance > 0 || isRefreshing;
  // インジケーターは引っ張り距離に合わせて降りてくる（最大 48px）
  const indicatorTranslate = isRefreshing
    ? 48
    : Math.min(pullDistance * 0.7, 48);

  return (
    <div
      ref={containerRef}
      className={cn("overflow-y-auto h-full pb-28", className)}
      style={{ overscrollBehaviorY: "contain" }}
    >
      {/* Pull indicator */}
      <div
        className="flex justify-center pointer-events-none"
        style={{
          height: isRefreshing ? 48 : pullDistance > 0 ? pullDistance * 0.6 : 0,
          transition: isRefreshing || pullDistance === 0 ? "height 0.25s ease" : "none",
          overflow: "hidden",
        }}
      >
        <div
          className={cn(
            "flex items-center justify-center w-10 h-10 rounded-full bg-white shadow-md border border-gray-100 mt-2",
            "transition-transform duration-150"
          )}
          style={{
            transform: `translateY(${indicatorTranslate - 40}px)`,
            transition: isRefreshing || pullDistance === 0 ? "transform 0.25s ease" : "none",
            opacity: indicatorVisible ? 1 : 0,
          }}
        >
          <RefreshCw
            size={16}
            className={cn(
              "transition-colors duration-150",
              isPastThreshold || isRefreshing ? "text-blue-600" : "text-gray-400",
              isRefreshing && "animate-spin"
            )}
            style={{
              // 引っ張り量に応じてアイコンを回転
              transform: isRefreshing ? undefined : `rotate(${pullDistance * 2}deg)`,
            }}
          />
        </div>
      </div>

      {/* Page content */}
      {children}
    </div>
  );
}
