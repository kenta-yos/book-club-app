"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase/client";
import type { EventWithBook } from "@/lib/types";
import { UserHeader } from "@/components/UserHeader";
import { HistoryPageSkeleton } from "@/components/Skeleton";
import { PullToRefreshWrapper } from "@/components/PullToRefreshWrapper";
import { toast } from "sonner";
import { ExternalLink } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer,
} from "recharts";

const COLORS = ["#1d4ed8","#7c3aed","#059669","#d97706","#dc2626","#0891b2","#4f46e5","#16a34a"];

export default function HistoryPage() {
  const router = useRouter();
  const [allEvents, setAllEvents] = useState<EventWithBook[]>([]);
  const [selectedYear, setSelectedYear] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = sessionStorage.getItem("bookclub_user");
    if (!stored) { router.replace("/"); return; }
    loadData();
  }, [router]);

  const loadData = useCallback(async () => {
    try {
      const { data, error } = await supabase
        .from("events")
        .select("*, books(*)")
        .order("event_date", { ascending: false });
      if (error) throw error;
      setAllEvents((data as EventWithBook[]) || []);
    } catch {
      toast.error("データの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  const today = new Date().toISOString().split("T")[0];
  const pastEvents = allEvents.filter((e) => e.event_date < today);
  const years = Array.from(new Set(pastEvents.map((e) => e.event_date.slice(0, 4))))
    .sort((a, b) => b.localeCompare(a));
  const yearOptions = [...years, "すべて"];

  useEffect(() => {
    if (years.length > 0 && !selectedYear) setSelectedYear(years[0]);
  }, [years, selectedYear]);

  const displayEvents = selectedYear === "すべて" || !selectedYear
    ? pastEvents
    : pastEvents.filter((e) => e.event_date.startsWith(selectedYear));

  const uniqueBooks = Array.from(new Map(pastEvents.map((e) => [e.book_id, e])).values());
  const catCounts: Record<string, number> = {};
  uniqueBooks.forEach((e) => {
    const cat = e.books?.category;
    if (cat && cat !== "None" && cat !== "nan") catCounts[cat] = (catCounts[cat] || 0) + 1;
  });
  const chartData = Object.entries(catCounts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);

  const handleRefresh = useCallback(async () => { await loadData(); }, [loadData]);

  if (loading) {
    return (
      <div>
        <UserHeader />
        <HistoryPageSkeleton />
      </div>
    );
  }

  return (
    <PullToRefreshWrapper onRefresh={handleRefresh}>
      <UserHeader onRefresh={handleRefresh} />

      <div className="px-4 pt-4">
        <h2 className="text-lg font-bold text-gray-900 mb-3">📜 History</h2>

        {pastEvents.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-4xl mb-3">📭</p>
            <p className="text-sm">過去の開催履歴はありません</p>
          </div>
        ) : (
          <>
            {/* Year filter */}
            <div className="flex gap-2 overflow-x-auto pb-2 mb-4">
              {yearOptions.map((year) => (
                <button key={year} onClick={() => setSelectedYear(year)}
                  className={`flex-shrink-0 px-4 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                    selectedYear === year
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
                  }`}>
                  {year}
                </button>
              ))}
            </div>

            {/* Event list */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden mb-6">
              {displayEvents.map((event, idx) => {
                const book = event.books;
                if (!book) return null;
                const dateStr = event.event_date.replace(/-/g, "/");
                const hasUrl = book.url && book.url.startsWith("http");
                return (
                  <div key={`${event.event_date}-${event.book_id}`}
                    className={`flex items-start gap-3 p-4 ${idx < displayEvents.length - 1 ? "border-b border-gray-50" : ""}`}>
                    <div className="w-24 flex-shrink-0">
                      <p className="text-xs text-gray-400 mb-1">{dateStr}</p>
                      <p className="text-xs text-gray-500 leading-snug break-all">{book.author || ""}</p>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="mb-2">
                        {hasUrl ? (
                          <a href={book.url!} target="_blank" rel="noopener noreferrer"
                            className="flex items-start gap-1 text-blue-600 font-semibold text-sm leading-snug hover:opacity-80">
                            <span className="flex-1">{book.title}</span>
                            <ExternalLink size={12} className="flex-shrink-0 mt-0.5 opacity-60" />
                          </a>
                        ) : (
                          <p className="font-semibold text-sm text-gray-800 leading-snug">{book.title}</p>
                        )}
                      </div>
                      {book.category && (
                        <span className="inline-block bg-gray-100 text-gray-500 text-[10px] font-bold px-2 py-0.5 rounded border border-gray-200">
                          {book.category}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {/* Category chart */}
        {chartData.length > 0 && (
          <div className="mb-8">
            <h3 className="text-sm font-bold text-gray-700 mb-3">📊 カテゴリランキング</h3>
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <ResponsiveContainer width="100%" height={chartData.length * 48 + 20}>
                <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 32, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                  <XAxis type="number" hide domain={[0, Math.max(...chartData.map((d) => d.count)) + 1]} />
                  <YAxis type="category" dataKey="name" width={100}
                    tick={{ fontSize: 11, fill: "#6b7280" }} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(v) => [`${v} 冊`, "冊数"]}
                    contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 12 }} />
                  <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                    {chartData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <p className="text-xs text-gray-400 mt-2 text-right">※ 複数月で読んだ本は1冊としてカウント</p>
            </div>
          </div>
        )}
      </div>
    </PullToRefreshWrapper>
  );
}
