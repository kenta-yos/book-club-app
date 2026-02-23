"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase/client";
import type { EventWithBook, Memo, User } from "@/lib/types";
import { UserHeader } from "@/components/UserHeader";
import { PullToRefreshWrapper } from "@/components/PullToRefreshWrapper";
import { RichTextEditor, RichTextViewer } from "@/components/RichTextEditor";
import { toast } from "sonner";
import { Pencil, Check, X, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export default function MemosPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [allEvents, setAllEvents] = useState<EventWithBook[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string>("");
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [memos, setMemos] = useState<Memo[]>([]);
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
    loadInitial();
  }, [router]);

  async function loadInitial() {
    try {
      const [eventsRes, usersRes] = await Promise.all([
        supabase.from("events").select("*, books(*)").order("event_date", { ascending: false }),
        supabase.from("users").select("user_name, icon").order("user_name"),
      ]);
      const events = (eventsRes.data as EventWithBook[]) || [];
      setAllEvents(events);
      setAllUsers(usersRes.data || []);

      if (events.length > 0 && events[0].id) {
        setSelectedEventId(events[0].id);
        await loadMemos(events[0].id);
      }
    } catch {
      toast.error("データの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }

  async function loadMemos(eventId: string) {
    if (!eventId) return;
    const { data, error } = await supabase
      .from("memos")
      .select("*")
      .eq("event_id", eventId)
      .order("created_at");
    if (error) { toast.error("メモの取得に失敗しました"); return; }
    setMemos(data || []);
  }

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    await loadInitial();
  }, []);

  async function handleEventChange(eventId: string) {
    setSelectedEventId(eventId);
    setIsEditing(false);
    setEditingContent("");
    setMemos([]);
    await loadMemos(eventId);
  }

  function startEdit(existingContent: string) {
    setEditingContent(existingContent);
    setIsEditing(true);
  }

  async function handleSave() {
    if (!currentUser || !selectedEventId) return;
    // 空チェック: タグだけで実質空のケースも弾く
    const stripped = editingContent.replace(/<[^>]+>/g, "").trim();
    if (!stripped) { toast.warning("メモを入力してください"); return; }
    setSubmitting(true);
    try {
      const { error } = await supabase.from("memos").upsert(
        {
          event_id: selectedEventId,
          user_name: currentUser.user_name,
          content: editingContent,
          updated_at: new Date().toISOString(),
        },
        { onConflict: "event_id,user_name" }
      );
      if (error) throw error;
      toast.success("メモを保存しました ✏️");
      setIsEditing(false);
      await loadMemos(selectedEventId);
    } catch (e: any) {
      toast.error("保存に失敗しました: " + (e?.message ?? ""));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!currentUser) return;
    const existing = memos.find((m) => m.user_name === currentUser.user_name);
    if (!existing) return;
    setSubmitting(true);
    try {
      const { error } = await supabase.from("memos").delete().eq("id", existing.id);
      if (error) throw error;
      toast.success("メモを削除しました");
      setIsEditing(false);
      setEditingContent("");
      await loadMemos(selectedEventId);
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

  const selectedEvent = allEvents.find((e) => e.id === selectedEventId) ?? null;
  const myMemo = memos.find((m) => m.user_name === currentUser?.user_name);
  const otherUsers = allUsers.filter((u) => u.user_name !== currentUser?.user_name);

  function formatEventLabel(event: EventWithBook) {
    const date = event.event_date.replace(/-/g, "/");
    const time = event.event_time ? ` ${event.event_time}` : "";
    const title = event.books?.title ?? "未定";
    return `${date}${time} — ${title}`;
  }

  return (
    <PullToRefreshWrapper onRefresh={handleRefresh}>
      <UserHeader onRefresh={handleRefresh} />

      <div className="px-4 pt-4 pb-10 space-y-4">
        <h2 className="text-lg font-bold text-gray-900">📝 読書メモ</h2>

        {allEvents.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-4xl mb-3">📭</p>
            <p className="text-sm">読書会の予定がまだ登録されていません</p>
          </div>
        ) : (
          <>
            {/* Event selector */}
            <div className="relative">
              <select
                value={selectedEventId}
                onChange={(e) => handleEventChange(e.target.value)}
                className="w-full appearance-none bg-white border border-gray-200 rounded-2xl px-4 py-3 pr-10 text-sm font-medium text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
              >
                {allEvents.map((event) => (
                  <option key={event.id} value={event.id ?? ""}>
                    {formatEventLabel(event)}
                  </option>
                ))}
              </select>
              <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
            </div>

            {/* Selected event info */}
            {selectedEvent?.books && (
              <div className="bg-blue-50 border border-blue-100 rounded-2xl px-4 py-3">
                <p className="text-xs text-blue-500 font-medium">
                  {selectedEvent.event_date.replace(/-/g, "/")}
                  {selectedEvent.event_time ? ` ${selectedEvent.event_time}` : ""}
                </p>
                <p className="text-sm font-bold text-blue-800 mt-0.5 leading-snug">{selectedEvent.books.title}</p>
              </div>
            )}

            {/* ── My memo ─────────────────────────────────── */}
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">✏️ 自分のメモ</h3>

              {isEditing ? (
                <div className="space-y-3">
                  <RichTextEditor
                    content={editingContent}
                    onChange={setEditingContent}
                    minHeight={200}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={handleSave}
                      disabled={submitting}
                      className="flex-1 flex items-center justify-center gap-1.5 py-3 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 active:scale-[0.98] transition-all disabled:opacity-50"
                    >
                      <Check size={15} />
                      {submitting ? "保存中..." : "保存する"}
                    </button>
                    {myMemo && (
                      <button
                        onClick={handleDelete}
                        disabled={submitting}
                        className="px-4 py-3 text-sm text-red-500 border border-red-200 rounded-xl hover:bg-red-50 transition-colors disabled:opacity-50"
                      >
                        削除
                      </button>
                    )}
                    <button
                      onClick={() => setIsEditing(false)}
                      className="px-3 py-3 text-gray-400 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
                    >
                      <X size={15} />
                    </button>
                  </div>
                </div>
              ) : myMemo ? (
                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{currentUser?.icon}</span>
                      <span className="text-sm font-medium text-gray-700">{currentUser?.user_name}</span>
                    </div>
                    <button
                      onClick={() => startEdit(myMemo.content)}
                      className="flex items-center gap-1 text-xs text-blue-600 border border-blue-200 px-2.5 py-1.5 rounded-lg hover:bg-blue-50 transition-colors flex-shrink-0"
                    >
                      <Pencil size={11} />
                      編集
                    </button>
                  </div>
                  <RichTextViewer html={myMemo.content} />
                  <p className="text-[10px] text-gray-400 mt-3">
                    更新: {new Date(myMemo.updated_at).toLocaleString("ja-JP", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
              ) : (
                <button
                  onClick={() => startEdit("")}
                  className="w-full py-5 text-sm text-gray-400 border-2 border-dashed border-gray-200 rounded-2xl hover:border-blue-300 hover:text-blue-500 hover:bg-blue-50/30 transition-all"
                >
                  + メモを書く
                </button>
              )}
            </div>

            {/* ── Others' memos ──────────────────────────── */}
            {otherUsers.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">👥 みんなのメモ</h3>
                <div className="space-y-2">
                  {otherUsers.map((u) => {
                    const memo = memos.find((m) => m.user_name === u.user_name);
                    return (
                      <div
                        key={u.user_name}
                        className={cn(
                          "bg-white rounded-2xl border shadow-sm p-4 transition-colors",
                          memo ? "border-gray-100" : "border-dashed border-gray-150"
                        )}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xl">{u.icon}</span>
                          <span className="text-sm font-medium text-gray-700">{u.user_name}</span>
                        </div>
                        {memo ? (
                          <>
                            <RichTextViewer html={memo.content} />
                            <p className="text-[10px] text-gray-400 mt-3">
                              更新: {new Date(memo.updated_at).toLocaleString("ja-JP", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })}
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
