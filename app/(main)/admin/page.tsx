"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase/client";
import type { Book, EventWithBook, User } from "@/lib/types";
import { UserHeader } from "@/components/UserHeader";
import { AdminPageSkeleton } from "@/components/Skeleton";
import { PullToRefreshWrapper } from "@/components/PullToRefreshWrapper";
import { toast } from "sonner";
import { LogOut, AlertTriangle, ChevronDown, ChevronUp, RotateCcw, Trash2 } from "lucide-react";

const ADMIN_USER_ID = "5a639e0f-b32c-41da-ab61-56c91ddb99b3";

export default function AdminPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [nominatedBooks, setNominatedBooks] = useState<Book[]>([]);
  const [allDisplayBooks, setAllDisplayBooks] = useState<Book[]>([]);
  const [lastEvent, setLastEvent] = useState<EventWithBook | null>(null);
  const [loading, setLoading] = useState(true);

  const [selectedBookId, setSelectedBookId] = useState<string>("");
  const [nextDate, setNextDate] = useState<string>("");
  const [nextTime, setNextTime] = useState<string>("18:00");
  const [submittingEvent, setSubmittingEvent] = useState(false);
  const [contDate, setContDate] = useState<string>("");
  const [contTime, setContTime] = useState<string>("18:00");
  const [submittingCont, setSubmittingCont] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [resetting, setResetting] = useState(false);

  // 削除済み本
  const [deletedBooks, setDeletedBooks] = useState<Book[]>([]);
  const [deletedOpen, setDeletedOpen] = useState(false);
  const [deletedQuery, setDeletedQuery] = useState("");
  const [deletedActionId, setDeletedActionId] = useState<string | null>(null);
  const [confirmHardDelete, setConfirmHardDelete] = useState<Book | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("bookclub_user");
    if (!stored) { router.replace("/"); return; }
    const user = JSON.parse(stored) as User;
    setCurrentUser(user);
    const today = new Date().toISOString().split("T")[0];
    setNextDate(today);
    setContDate(today);
    loadData();
  }, [router]);

  const loadData = useCallback(async () => {
    try {
      const [booksRes, eventsRes, votesRes] = await Promise.all([
        supabase.from("books").select("*"),
        supabase.from("events").select("*, books(*)").order("event_date", { ascending: false }),
        supabase.from("votes").select("*"),
      ]);
      const allBooks = booksRes.data || [];
      const allEvents = eventsRes.data || [];
      const allVotes = votesRes.data || [];
      const usedIds = allEvents.map((e: any) => String(e.book_id));
      const activeVotes = allVotes.filter((v: any) => !usedIds.includes(String(v.book_id)));
      const nomIds = activeVotes.filter((v: any) => v.action === "選出").map((v: any) => String(v.book_id));
      const nomBooks = allBooks.filter((b: any) => nomIds.includes(String(b.id)) && !b.deleted_at);
      setNominatedBooks(nomBooks);
      const displayBooks = allBooks.filter((b: any) => !usedIds.includes(String(b.id)) && !b.deleted_at);
      setAllDisplayBooks(displayBooks);
      setDeletedBooks(allBooks.filter((b: any) => !!b.deleted_at));
      const finalList = nomBooks.length > 0 ? nomBooks : displayBooks;
      if (finalList.length > 0 && !selectedBookId) setSelectedBookId(String(finalList[0].id));
      if (allEvents.length > 0) setLastEvent(allEvents[0] as EventWithBook);
    } catch {
      toast.error("データの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, [selectedBookId]);

  async function handleConfirmEvent(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedBookId || !nextDate) { toast.warning("日程と課題本を選択してください"); return; }
    setSubmittingEvent(true);
    try {
      const { error } = await supabase.from("events").insert({ event_date: nextDate, event_time: nextTime || null, book_id: selectedBookId });
      if (error) throw error;
      toast.success("次回予告を更新しました 🚀");
      setSelectedBookId("");
      await loadData();
    } catch {
      toast.error("登録に失敗しました");
    } finally {
      setSubmittingEvent(false);
    }
  }

  async function handleContinue(e: React.FormEvent) {
    e.preventDefault();
    if (!lastEvent || !contDate) return;
    setSubmittingCont(true);
    try {
      const { error } = await supabase.from("events").insert({ event_date: contDate, event_time: contTime || null, book_id: String(lastEvent.book_id) });
      if (error) throw error;
      toast.success("継続開催を登録しました 🔁");
      await loadData();
    } catch {
      toast.error("登録に失敗しました");
    } finally {
      setSubmittingCont(false);
    }
  }

  async function handleResetVotes() {
    if (!confirmReset) return;
    setResetting(true);
    try {
      const { error } = await supabase.from("votes").delete().eq("action", "投票");
      if (error) throw error;
      toast.success("すべての投票をリセットしました 🙋");
      setConfirmReset(false);
      await loadData();
    } catch {
      toast.error("リセットに失敗しました");
    } finally {
      setResetting(false);
    }
  }

  async function handleRestore(book: Book) {
    setDeletedActionId(String(book.id));
    try {
      const { error } = await supabase
        .from("books")
        .update({ deleted_at: null })
        .eq("id", String(book.id));
      if (error) throw error;
      toast.success(`「${book.title}」を復元しました`);
      await loadData();
    } catch {
      toast.error("復元に失敗しました");
    } finally {
      setDeletedActionId(null);
    }
  }

  async function handleHardDelete(book: Book) {
    setConfirmHardDelete(null);
    setDeletedActionId(String(book.id));
    try {
      const { error } = await supabase
        .from("books")
        .delete()
        .eq("id", String(book.id));
      if (error) throw error;
      toast.success(`「${book.title}」を完全に削除しました`);
      await loadData();
    } catch {
      toast.error("削除に失敗しました");
    } finally {
      setDeletedActionId(null);
    }
  }

  function handleLogout() {
    localStorage.removeItem("bookclub_user");
    router.replace("/");
  }

  const handleRefresh = useCallback(async () => { await loadData(); }, [loadData]);
  const finalList = nominatedBooks.length > 0 ? nominatedBooks : allDisplayBooks;

  if (loading) {
    return (
      <div>
        <UserHeader />
        <AdminPageSkeleton />
      </div>
    );
  }

  return (
    <PullToRefreshWrapper onRefresh={handleRefresh}>
      <UserHeader onRefresh={handleRefresh} />

      <div className="px-4 pt-4 space-y-5">
        <h2 className="text-lg font-bold text-gray-900">⚙️ Admin</h2>

        {/* Section 1 */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
          <h3 className="text-sm font-bold text-gray-800 mb-3">🆕 次回の課題本を確定する</h3>
          {nominatedBooks.length > 0 ? (
            <div className="text-xs text-blue-600 bg-blue-50 border border-blue-100 rounded-lg p-2 mb-3">
              🗳️ 現在メンバーが選出中の本が表示されています
            </div>
          ) : (
            <div className="text-xs text-yellow-600 bg-yellow-50 border border-yellow-100 rounded-lg p-2 mb-3">
              ⚠️ 選出されている本がありません。全リストから表示します。
            </div>
          )}
          {finalList.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">選択可能な本がありません</p>
          ) : (
            <form onSubmit={handleConfirmEvent} className="space-y-3 overflow-hidden">
              <div className="flex gap-2">
                <div className="flex-1 min-w-0">
                  <label className="block text-xs font-medium text-gray-600 mb-1">読書会の日程</label>
                  <input type="date" value={nextDate} onChange={(e) => setNextDate(e.target.value)}
                    className="w-full max-w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 box-border" required />
                </div>
                <div className="w-28 flex-shrink-0">
                  <label className="block text-xs font-medium text-gray-600 mb-1">時間</label>
                  <input type="time" value={nextTime} onChange={(e) => setNextTime(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">課題本を確定</label>
                <select value={selectedBookId} onChange={(e) => setSelectedBookId(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white" required>
                  <option value="">選択してください</option>
                  {finalList.map((book: any) => (
                    <option key={book.id} value={String(book.id)}>[{book.category}] {book.title}</option>
                  ))}
                </select>
              </div>
              <button type="submit" disabled={submittingEvent}
                className="w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 active:scale-[0.98] transition-all disabled:opacity-50">
                {submittingEvent ? "確定中..." : "次回予告を確定する"}
              </button>
            </form>
          )}
        </div>

        {/* Section 2 */}
        {lastEvent && lastEvent.books && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
            <h3 className="text-sm font-bold text-gray-800 mb-3">🔁 前回の本を継続する</h3>
            <p className="text-xs text-gray-500 mb-3">
              前回の課題本: <span className="font-semibold text-gray-700">{lastEvent.books.title}</span>
            </p>
            <form onSubmit={handleContinue} className="space-y-3 overflow-hidden">
              <div className="flex gap-2">
                <div className="flex-1 min-w-0">
                  <label className="block text-xs font-medium text-gray-600 mb-1">継続開催の日付</label>
                  <input type="date" value={contDate} onChange={(e) => setContDate(e.target.value)}
                    className="w-full max-w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 box-border" required />
                </div>
                <div className="w-28 flex-shrink-0">
                  <label className="block text-xs font-medium text-gray-600 mb-1">時間</label>
                  <input type="time" value={contTime} onChange={(e) => setContTime(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              <button type="submit" disabled={submittingCont}
                className="w-full py-2.5 text-sm font-medium text-blue-600 border-2 border-blue-300 rounded-xl hover:bg-blue-50 active:scale-[0.98] transition-all disabled:opacity-50">
                {submittingCont ? "登録中..." : "この本で次回の予告を作る（継続）"}
              </button>
            </form>
          </div>
        )}

        {/* Section 3 */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
          <h3 className="text-sm font-bold text-gray-800 mb-2">🧹 データの管理</h3>
          <div className="text-xs text-gray-500 bg-gray-50 rounded-lg p-2 mb-3 flex items-start gap-1">
            <AlertTriangle size={12} className="flex-shrink-0 mt-0.5 text-yellow-500" />
            「投票」のみを削除します。「選出」のデータは保持されます。
          </div>
          <label className="flex items-center gap-2 mb-3 cursor-pointer">
            <input type="checkbox" checked={confirmReset} onChange={(e) => setConfirmReset(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
            <span className="text-sm text-gray-600">全ユーザーの投票リセットを実行します</span>
          </label>
          <button onClick={handleResetVotes} disabled={!confirmReset || resetting}
            className="w-full py-2.5 bg-red-500 text-white text-sm font-medium rounded-xl hover:bg-red-600 active:scale-[0.98] transition-all disabled:opacity-40 disabled:cursor-not-allowed">
            {resetting ? "リセット中..." : "投票を一括リセット"}
          </button>
        </div>

        {/* Section: 削除済みの本（adminのみ） */}
        {currentUser?.id === ADMIN_USER_ID && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <button
              onClick={() => setDeletedOpen((o) => !o)}
              className="w-full flex items-center justify-between px-4 py-3 text-sm font-bold text-gray-800 hover:bg-gray-50 transition-colors"
            >
              <span>🗑️ 削除済みの本 {deletedBooks.length > 0 && <span className="text-gray-400 font-normal">（{deletedBooks.length}冊）</span>}</span>
              {deletedOpen ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
            </button>

            {deletedOpen && (
              <div className="border-t border-gray-100 px-4 pb-4 pt-3 space-y-3">
                {/* 検索 */}
                <input
                  type="text"
                  value={deletedQuery}
                  onChange={(e) => setDeletedQuery(e.target.value)}
                  placeholder="タイトル・著者で検索..."
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />

                {(() => {
                  const q = deletedQuery.trim().toLowerCase();
                  const filtered = deletedBooks.filter((b) => {
                    if (!q) return true;
                    return (
                      b.title.toLowerCase().includes(q) ||
                      (b.author ?? "").toLowerCase().includes(q)
                    );
                  });
                  if (filtered.length === 0) {
                    return (
                      <p className="text-sm text-gray-400 text-center py-4">
                        {q ? "該当する本が見つかりません" : "削除済みの本はありません"}
                      </p>
                    );
                  }
                  return (
                    <ul className="space-y-2">
                      {filtered.map((book) => {
                        const bId = String(book.id);
                        const isActing = deletedActionId === bId;
                        return (
                          <li key={bId} className="flex items-center gap-2 py-2 border-b border-gray-50 last:border-0">
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-800 truncate">{book.title}</p>
                              {book.author && (
                                <p className="text-xs text-gray-400 truncate">{book.author}</p>
                              )}
                            </div>
                            <button
                              onClick={() => handleRestore(book)}
                              disabled={isActing}
                              className="flex-shrink-0 flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 active:scale-95 transition-all disabled:opacity-50"
                            >
                              <RotateCcw size={12} />
                              復元
                            </button>
                            <button
                              onClick={() => setConfirmHardDelete(book)}
                              disabled={isActing}
                              className="flex-shrink-0 flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-red-500 border border-red-200 rounded-lg hover:bg-red-50 active:scale-95 transition-all disabled:opacity-50"
                            >
                              <Trash2 size={12} />
                              完全削除
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  );
                })()}
              </div>
            )}
          </div>
        )}

        {/* Logout */}
        <div className="pb-4">
          <hr className="border-gray-200 mb-4" />
          <button onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 py-2.5 text-sm text-gray-500 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </div>
      {/* 完全削除確認モーダル */}
      {confirmHardDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/40">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm">
            <h3 className="font-bold text-lg text-gray-900 mb-2">完全に削除しますか？</h3>
            <p className="text-sm text-gray-500 mb-6">
              「{confirmHardDelete.title}」をDBから完全に削除します。<br />
              この操作は取り消せません。
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmHardDelete(null)}
                className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                キャンセル
              </button>
              <button
                onClick={() => handleHardDelete(confirmHardDelete)}
                className="flex-1 py-2.5 bg-red-500 text-white rounded-xl text-sm font-medium hover:bg-red-600 active:scale-[0.98] transition-all"
              >
                完全削除する
              </button>
            </div>
          </div>
        </div>
      )}
    </PullToRefreshWrapper>
  );
}
