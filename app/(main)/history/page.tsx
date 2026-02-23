"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase/client";
import type { EventWithBook, Memo, User } from "@/lib/types";
import { RichTextViewer } from "@/components/RichTextEditor";
import { UserHeader } from "@/components/UserHeader";
import { HistoryPageSkeleton } from "@/components/Skeleton";
import { PullToRefreshWrapper } from "@/components/PullToRefreshWrapper";
import { toast } from "sonner";
import { ExternalLink, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer,
  LabelList, Legend, AreaChart, Area,
} from "recharts";

const COLORS = ["#1d4ed8","#7c3aed","#059669","#d97706","#dc2626","#0891b2","#4f46e5","#16a34a"];

export default function HistoryPage() {
  const router = useRouter();
  const [allEvents, setAllEvents] = useState<EventWithBook[]>([]);
  const [selectedYear, setSelectedYear] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [expandedMemos, setExpandedMemos] = useState<Set<string>>(new Set());
  const [memoCache, setMemoCache] = useState<Record<string, Memo[]>>({});
  const [memoLoading, setMemoLoading] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("bookclub_user");
    if (!stored) { router.replace("/"); return; }
    loadData();
  }, [router]);

  const loadData = useCallback(async () => {
    try {
      const [eventsRes, usersRes] = await Promise.all([
        supabase.from("events").select("*, books(*)").order("event_date", { ascending: false }),
        supabase.from("users").select("user_name, icon").order("user_name"),
      ]);
      if (eventsRes.error) throw eventsRes.error;
      setAllEvents((eventsRes.data as EventWithBook[]) || []);
      setAllUsers(usersRes.data || []);
    } catch {
      toast.error("データの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  async function toggleMemos(event: EventWithBook) {
    const key = event.id ?? `${event.event_date}_${event.book_id}`;
    if (expandedMemos.has(key)) {
      setExpandedMemos((prev) => { const s = new Set(prev); s.delete(key); return s; });
      return;
    }
    if (!memoCache[key] && event.id) {
      setMemoLoading(key);
      try {
        const { data } = await supabase
          .from("memos")
          .select("*")
          .eq("event_id", event.id)
          .order("created_at");
        setMemoCache((prev) => ({ ...prev, [key]: data || [] }));
      } catch {
        toast.error("メモの取得に失敗しました");
      } finally {
        setMemoLoading(null);
      }
    }
    setExpandedMemos((prev) => new Set([...prev, key]));
  }

  const today = new Date(new Date().getTime() + 9 * 60 * 60 * 1000).toISOString().split("T")[0];
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

  // 興味の変遷: 年 × カテゴリ別冊数
  const trendYears = Array.from(new Set(pastEvents.map((e) => e.event_date.slice(0, 4)))).sort();
  const trendCategories = Array.from(
    new Set(uniqueBooks.map((e) => e.books?.category).filter((c): c is string => !!c && c !== "None" && c !== "nan"))
  ).sort((a, b) => (catCounts[b] ?? 0) - (catCounts[a] ?? 0)); // 多い順
  const trendData = trendYears.map((year) => {
    const yearBookMap = new Map(
      pastEvents.filter((e) => e.event_date.startsWith(year)).map((e) => [e.book_id, e])
    );
    const row: Record<string, string | number> = { year };
    trendCategories.forEach((cat) => {
      row[cat] = Array.from(yearBookMap.values()).filter((e) => e.books?.category === cat).length;
    });
    return row;
  });

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
                const key = event.id ?? `${event.event_date}_${event.book_id}`;
                const isExpanded = expandedMemos.has(key);
                const isLoadingMemos = memoLoading === key;
                const eventMemos = memoCache[key] ?? [];
                return (
                  <div key={key}
                    className={idx < displayEvents.length - 1 ? "border-b border-gray-50" : ""}>
                    <div className="flex items-start gap-3 p-4">
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
                        <div className="flex items-center gap-2 flex-wrap">
                          {book.category && (
                            <span className="inline-block bg-gray-100 text-gray-500 text-[10px] font-bold px-2 py-0.5 rounded border border-gray-200">
                              {book.category}
                            </span>
                          )}
                          {event.id && (
                            <button
                              onClick={() => toggleMemos(event)}
                              className={cn(
                                "flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded border transition-colors",
                                isExpanded
                                  ? "bg-blue-50 text-blue-600 border-blue-200"
                                  : "bg-gray-50 text-gray-500 border-gray-200 hover:border-blue-200"
                              )}
                            >
                              📝 メモ
                              {isLoadingMemos ? (
                                <span className="animate-spin">⏳</span>
                              ) : isExpanded ? (
                                <ChevronUp size={10} />
                              ) : (
                                <ChevronDown size={10} />
                              )}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Memos expanded section */}
                    {isExpanded && !isLoadingMemos && (
                      <div className="px-4 pb-4 space-y-2">
                        {eventMemos.length === 0 ? (
                          <p className="text-xs text-gray-400 text-center py-2">このイベントのメモはありません</p>
                        ) : (
                          eventMemos.map((memo) => {
                            const user = allUsers.find((u) => u.user_name === memo.user_name);
                            return (
                              <div key={memo.id} className="bg-gray-50 rounded-xl p-3 border border-gray-100">
                                <div className="flex items-center gap-1.5 mb-1">
                                  <span className="text-sm">{user?.icon ?? "👤"}</span>
                                  <span className="text-xs font-medium text-gray-600">{memo.user_name}</span>
                                </div>
                                <RichTextViewer html={memo.content} className="text-xs" />
                              </div>
                            );
                          })
                        )}
                      </div>
                    )}
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
                <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 40, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                  <XAxis type="number" hide domain={[0, Math.max(...chartData.map((d) => d.count)) * 1.25 + 1]} />
                  <YAxis type="category" dataKey="name" width={100}
                    tick={{ fontSize: 11, fill: "#6b7280" }} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(v) => [`${v} 冊`, "冊数"]}
                    contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 12 }} />
                  <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                    <LabelList dataKey="count" position="right"
                      formatter={(v: number) => `${v}冊`}
                      style={{ fontSize: 11, fill: "#6b7280", fontWeight: 600 }} />
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
        {/* 興味の変遷グラフ */}
        {trendData.length >= 2 && trendCategories.length > 0 && (
          <div className="mb-8">
            <h3 className="text-sm font-bold text-gray-700 mb-1">📈 興味の変遷</h3>
            <p className="text-xs text-gray-400 mb-3">年ごとのカテゴリ別冊数（積み上げエリア）</p>
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={trendData} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                  <defs>
                    {trendCategories.map((cat, i) => (
                      <linearGradient key={cat} id={`gradient-${i}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.85} />
                        <stop offset="95%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.55} />
                      </linearGradient>
                    ))}
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis dataKey="year" tick={{ fontSize: 11, fill: "#6b7280" }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip
                    formatter={(v: number, name: string) => [`${v} 冊`, name]}
                    contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 11 }}
                    cursor={{ stroke: "#e5e7eb", strokeWidth: 1 }}
                  />
                  {trendCategories.map((cat, i) => (
                    <Area
                      key={cat}
                      type="monotone"
                      dataKey={cat}
                      stackId="a"
                      stroke={COLORS[i % COLORS.length]}
                      strokeWidth={1.5}
                      fill={`url(#gradient-${i})`}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
              {/* 凡例 */}
              <div className="flex flex-wrap gap-x-3 gap-y-1.5 mt-3">
                {trendCategories.map((cat, i) => (
                  <div key={cat} className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                    <span className="text-[10px] text-gray-500">{cat}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </PullToRefreshWrapper>
  );
}
