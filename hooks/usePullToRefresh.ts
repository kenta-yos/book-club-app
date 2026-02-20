"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface UsePullToRefreshOptions {
  onRefresh: () => Promise<void>;
  /** 引っ張る距離の閾値 (px) デフォルト 72 */
  threshold?: number;
  /** 最大引っ張れる距離 (px) デフォルト 120 */
  maxPull?: number;
}

interface PullToRefreshState {
  /** 現在引っ張っている距離 (0 ~ maxPull) */
  pullDistance: number;
  /** 閾値を超えているか */
  isPastThreshold: boolean;
  /** リフレッシュ中か */
  isRefreshing: boolean;
}

export function usePullToRefresh(
  containerRef: React.RefObject<HTMLElement | null>,
  { onRefresh, threshold = 72, maxPull = 120 }: UsePullToRefreshOptions
): PullToRefreshState {
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const startYRef = useRef<number | null>(null);
  const isRefreshingRef = useRef(false);
  const isPullingRef = useRef(false);

  const handleRefresh = useCallback(async () => {
    if (isRefreshingRef.current) return;
    isRefreshingRef.current = true;
    setIsRefreshing(true);
    setPullDistance(threshold); // ロック位置で固定
    try {
      await onRefresh();
    } finally {
      // スムーズに戻す
      setIsRefreshing(false);
      isRefreshingRef.current = false;
      setPullDistance(0);
    }
  }, [onRefresh, threshold]);

  useEffect(() => {
    function onTouchStart(e: TouchEvent) {
      // ページ先頭でないと発動しない
      if (window.scrollY > 0) return;
      startYRef.current = e.touches[0].clientY;
      isPullingRef.current = true;
    }

    function onTouchMove(e: TouchEvent) {
      if (!isPullingRef.current || startYRef.current === null) return;
      if (isRefreshingRef.current) return;

      const deltaY = e.touches[0].clientY - startYRef.current;

      // 上方向スクロールは無視
      if (deltaY <= 0) {
        setPullDistance(0);
        return;
      }

      // スクロール位置が先頭を離れたら無効化
      if (window.scrollY > 0) {
        isPullingRef.current = false;
        setPullDistance(0);
        startYRef.current = null;
        return;
      }

      // デフォルトスクロールを止めて引っ張りを開始
      e.preventDefault();

      // ラバーバンド効果：引っ張るほど抵抗が増す
      const resistance = 0.45;
      const pulled = Math.min(deltaY * resistance, maxPull);
      setPullDistance(pulled);
    }

    function onTouchEnd() {
      if (!isPullingRef.current) return;
      isPullingRef.current = false;

      setPullDistance((current) => {
        if (current >= threshold && !isRefreshingRef.current) {
          handleRefresh();
        } else if (!isRefreshingRef.current) {
          // 閾値未満 → スナップバック
          return 0;
        }
        return current;
      });

      startYRef.current = null;
    }

    window.addEventListener("touchstart", onTouchStart, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: false });
    window.addEventListener("touchend", onTouchEnd, { passive: true });

    return () => {
      window.removeEventListener("touchstart", onTouchStart);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
    };
  }, [threshold, maxPull, handleRefresh]);

  return {
    pullDistance,
    isPastThreshold: pullDistance >= threshold,
    isRefreshing,
  };
}
