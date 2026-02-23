"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase/client";
import type { EventWithBook, Memo, User } from "@/lib/types";
import { UserHeader } from "@/components/UserHeader";
import { PullToRefreshWrapper } from "@/components/PullToRefreshWrapper";
import { toast } from "sonner";
import { Pencil, Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

export default function MemosPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [currentEvent, setCurrentEvent] = useState<EventWithBook | null>(null);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [memos, setMemos] = useState<Memo[]>([]);
  const [timing, setTiming] = useState<"before" | "after">("before");
  const [editingContent, setEditingContent] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  const userNameRef = useRef("");

  useEffect(() => {
    const stored = sessionStorage.getItem("bookclub_user");
    if (!stored) { router.replace("/"); return; }
    const user = JSON.parse(stored) as User;
    setCurrentUser(user);
    userNameRef.current = user.user_name;
    loadData(user.user_name);
  }, [router]);

  const loadData = useCallback(async (userName?: string) => {
    const uName = userName || userNameRef.current;
    if (!uName) return;
    try {
      const [eventsRes, usersRes] = await Promise.all([
        supabase.from("events").select("*, books(*)").order("event_date", { ascending: false }).limit(1),
        supabase.from("users").select("user_name, icon").order("user_name"),
      ]);
      const latestEvent = eventsRes.data?.[0] as EventWithBook | null ?? null;
      setCurrentEvent(latestEvent);
      setAllUsers(usersRes.data || []);

      if (latestEvent?.id) {
        const { data: memosData } = await supabase
          .from("memos")
          .select("*")
          .eq("event_id", latestEvent.id)
          .order("created_at");
        setMemos(memosData || []);
      } else {
        setMemos([]);
      }
    } catch {
      toast.error("データの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRefresh = useCallback(async () => { await loadData(); }, [loadData]);

  function startEdit(existingContent: string) {
    setEditingContent(existingContent);
    setIsEditing(true);
  }

  async function handleSave() {
    if (!currentUser || !currentEvent?.id) return;
    if (!editingContent.trim()) { toast.warning("メモを入力してください"); return; }
    setSubmitting(true);
    try {
      // 既存メモを確認してupsert
      const existing = memos.find(
        (m) => m.user_name === currentUser.user_name && m.timing === timing
      );
      if (existing) {
        const { error } = await supabase
          .from("memos")
          .update({ content: editingContent.trim(), updated_at: new Date().toISOString() })
          .eq("id", existing.id);
        if (error) throw error;
      } else {
        const { error } = await supabase.from("memos").insert({
          event_id: currentEvent.id!,
          user_name: currentUser.user_name,
          content: editingContent.trim(),
          timing,
        });
        if (error) throw error;
      }
      toast.success("メモを保存しました ✏️");
      setIsEditing(false);
      await loadData();
    } catch {
      toast.error("保存に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!currentUser) return;
    const existing = memos.find(
      (m) => m.user_name === currentUser.user_name && m.timing === timing
    );
    if (!existing) return;
    setSubmitting(true);
    try {
      const { error } = await supabase.from("memos").delete().eq("id", existing.id);
      if (error) throw error;
      toast.success("メモを削除しました");
      setIsEditing(false);
      setEditingContent("");
      await loadData();
    } catch {
      toast.error("削除に失敗しました");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div>
        <UserHeader />
        <div className="px-4 pt-4 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-2xl border border-gray-100 h-24 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const filteredMemos = memos.filter((m) => m.timing === timing);
  const myMemo = filteredMemos.find((m) => m.user_name === currentUser?.user_name);
  const otherMemos = filteredMemos.filter((m) => m.user_name !== currentUser?.user_name);
  const dateStr = currentEvent
    ? `${currentEvent.event_date.replace(/-/g, "/")}${currentEvent.event_time ? " " + currentEvent.event_time : ""}`
    : null;

  return (
    <PullToRefreshWrapper onRefresh={handleRefresh}>
      <UserHeader onRefresh={handleRefresh} />

      <div className="px-4 pt-4 space-y-4">
        <h2 className="text-lg font-bold text-gray-900">📝 読書メモ</h2>

        {/* Current event info */}
        {currentEvent?.books ? (
          <div className="bg-blue-50 border border-blue-100 rounded-2xl p-3">
            <p className="text-xs text-blue-500 font-medium">{dateStr}</p>
            <p className="text-sm font-bold text-blue-800 mt-0.5">{currentEvent.books.title}</p>
          </div>
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-2xl p-3">
            <p className="text-sm text-gray-400">次回の予定がまだ登録されていません</p>
          </div>
        )}

        {/* Before / After toggle */}
        <div className="flex bg-gray-100 rounded-xl p-1 gap-1">
          {(["before", "after"] as const).map((t) => (
            <button
              key={t}
              onClick={() => { setTiming(t); setIsEditing(false); }}
              className={cn(
                "flex-1 py-2 rounded-lg text-sm font-medium transition-all",
                timing === t ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
              )}
            >
              {t === "before" ? "📖 事前メモ" : "💬 事後メモ"}
            </button>
          ))}
        </div>

        {!currentEvent && (
          <p className="text-sm text-gray-400 text-center py-8">イベントが登録されるとメモを書けます</p>
        )}

        {currentEvent && (
          <>
            {/* My memo */}
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                ✏️ 自分のメモ
              </h3>
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
                {isEditing ? (
                  <div className="space-y-2">
                    <textarea
                      value={editingContent}
                      onChange={(e) => setEditingContent(e.target.value)}
                      placeholder={timing === "before" ? "読む前の感想や期待を書こう..." : "読んだ後の感想・気づきを書こう..."}
                      rows={5}
                      className="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                      autoFocus
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={handleSave}
                        disabled={submitting}
                        className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 active:scale-[0.98] transition-all disabled:opacity-50"
                      >
                        <Check size={14} />
                        {submitting ? "保存中..." : "保存する"}
                      </button>
                      {myMemo && (
                        <button
                          onClick={handleDelete}
                          disabled={submitting}
                          className="px-3 py-2 text-xs text-red-500 border border-red-200 rounded-xl hover:bg-red-50 transition-colors disabled:opacity-50"
                        >
                          削除
                        </button>
                      )}
                      <button
                        onClick={() => setIsEditing(false)}
                        className="px-3 py-2 text-xs text-gray-500 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </div>
                ) : myMemo ? (
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-base">{currentUser?.icon}</span>
                        <span className="text-xs font-medium text-gray-700">{currentUser?.user_name}</span>
                      </div>
                      <button
                        onClick={() => startEdit(myMemo.content)}
                        className="flex items-center gap-1 text-xs text-blue-600 border border-blue-200 px-2 py-1 rounded-lg hover:bg-blue-50 transition-colors"
                      >
                        <Pencil size={11} />
                        編集
                      </button>
                    </div>
                    <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">{myMemo.content}</p>
                    <p className="text-[10px] text-gray-400 mt-2">
                      {new Date(myMemo.updated_at).toLocaleString("ja-JP", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                ) : (
                  <button
                    onClick={() => startEdit("")}
                    className="w-full py-3 text-sm text-gray-400 border-2 border-dashed border-gray-200 rounded-xl hover:border-blue-300 hover:text-blue-500 transition-colors"
                  >
                    + {timing === "before" ? "事前メモ" : "事後メモ"}を書く
                  </button>
                )}
              </div>
            </div>

            {/* Others' memos */}
            {(otherMemos.length > 0 || allUsers.filter((u) => u.user_name !== currentUser?.user_name).length > 0) && (
              <div>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  👥 みんなのメモ
                </h3>
                <div className="space-y-2">
                  {allUsers
                    .filter((u) => u.user_name !== currentUser?.user_name)
                    .map((u) => {
                      const memo = filteredMemos.find((m) => m.user_name === u.user_name);
                      return (
                        <div key={u.user_name} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
                          <div className="flex items-center gap-1.5 mb-2">
                            <span className="text-base">{u.icon}</span>
                            <span className="text-xs font-medium text-gray-700">{u.user_name}</span>
                          </div>
                          {memo ? (
                            <>
                              <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">{memo.content}</p>
                              <p className="text-[10px] text-gray-400 mt-2">
                                {new Date(memo.updated_at).toLocaleString("ja-JP", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                              </p>
                            </>
                          ) : (
                            <p className="text-sm text-gray-300 italic">まだ書いていません</p>
                          )}
                        </div>
                      );
                    })}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </PullToRefreshWrapper>
  );
}
