"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase/client";
import type { Book, EventWithBook, User } from "@/lib/types";
import { UserHeader } from "@/components/UserHeader";
import { NextEventBanner } from "@/components/NextEventBanner";
import { BooksPageSkeleton } from "@/components/Skeleton";
import { PullToRefreshWrapper } from "@/components/PullToRefreshWrapper";
import { toast } from "sonner";
import { Plus, X, ExternalLink, Bookmark, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

export default function BooksPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [usedBookIds, setUsedBookIds] = useState<string[]>([]);

  // ── Optimistic UI 用state ──────────────────────────────────────
  const [myNominationBookId, setMyNominationBookId] = useState<string | null>(null);
  const [nominatedBookIds, setNominatedBookIds] = useState<string[]>([]);
  // ─────────────────────────────────────────────────────────────

  const [nextEvent, setNextEvent] = useState<EventWithBook | null>(null);
  const [lastPastEventDate, setLastPastEventDate] = useState<string | null>(null);
  const [selectedCat, setSelectedCat] = useState<string>("すべて");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Add book form
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newAuthor, setNewAuthor] = useState("");
  const [newCat, setNewCat] = useState("");
  const [newUrl, setNewUrl] = useState("");
  const [submittingBook, setSubmittingBook] = useState(false);

  // ── 削除確認モーダル ───────────────────────────────────────────
  const [bookToDelete, setBookToDelete] = useState<Book | null>(null);

  // ── 推薦コメント: 選出前にコメントを入力するインラインフォーム ──
  const [pendingNominateBook, setPendingNominateBook] = useState<Book | null>(null);
  const [nominationComment, setNominationComment] = useState("");

  // ── 気になる: localStorage に保存する個人ブックマーク ──────────
  const [interestedBookIds, setInterestedBookIds] = useState<Set<string>>(new Set());

  const userNameRef = useRef<string>("");

  useEffect(() => {
    const stored = sessionStorage.getItem("bookclub_user");
    if (!stored) { router.replace("/"); return; }
    const user = JSON.parse(stored) as User;
    setCurrentUser(user);
    userNameRef.current = user.user_name;

    // 気になる: localStorage から読み込み
    const storedInterested = localStorage.getItem(`bookclub_interested_${user.user_name}`);
    if (storedInterested) {
      setInterestedBookIds(new Set(JSON.parse(storedInterested)));
    }

    loadData(user.user_name);
  }, [router]);

  const loadData = useCallback(async (userName?: string) => {
    const uName = userName || userNameRef.current;
    if (!uName) return;

    setLoading((prev) => prev);

    try {
      const [booksRes, catsRes, eventsRes, votesRes] = await Promise.all([
        supabase.from("books").select("*").is("deleted_at", null),
        supabase.from("categories").select("name").order("id"),
        supabase.from("events").select("*, books(*)").order("event_date", { ascending: false }),
        supabase.from("votes").select("*"),
      ]);

      const allBooks = booksRes.data || [];
      const allCats = catsRes.data?.map((c: any) => c.name) || [];
      const allEvents = eventsRes.data || [];
      const allVotes = votesRes.data || [];

      const usedIds = allEvents.map((e: any) => String(e.book_id));
      setUsedBookIds(usedIds);

      const activeVotes = allVotes.filter(
        (v: any) => !usedIds.includes(String(v.book_id))
      );
      const myNom = activeVotes.find(
        (v: any) => v.action === "選出" && v.user_name === uName
      );
      setMyNominationBookId(myNom ? String(myNom.book_id) : null);

      const nomIds = activeVotes
        .filter((v: any) => v.action === "選出")
        .map((v: any) => String(v.book_id));
      setNominatedBookIds(nomIds);

      const today = new Date().toISOString().split("T")[0];
      const futureEvents = allEvents.filter((e: any) => e.event_date >= today);
      if (futureEvents.length > 0) {
        const sorted = [...futureEvents].sort((a: any, b: any) =>
          a.event_date.localeCompare(b.event_date)
        );
        setNextEvent(sorted[0] as EventWithBook);
      } else {
        setNextEvent(null);
      }

      const pastEvents = allEvents.filter((e: any) => e.event_date < today);
      if (pastEvents.length > 0) {
        const latestPast = [...pastEvents].sort((a: any, b: any) =>
          b.event_date.localeCompare(a.event_date)
        )[0];
        setLastPastEventDate(latestPast.event_date);
      } else {
        setLastPastEventDate(null);
      }

      setBooks(allBooks);
      setCategories(allCats);
      if (allCats.length > 0 && !newCat) setNewCat(allCats[0]);
    } catch {
      toast.error("データの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, [newCat]);

  // ── 気になるトグル ─────────────────────────────────────────────
  function toggleInterested(bookId: string) {
    const userName = userNameRef.current;
    setInterestedBookIds((prev) => {
      const next = new Set(prev);
      if (next.has(bookId)) {
        next.delete(bookId);
      } else {
        next.add(bookId);
      }
      localStorage.setItem(`bookclub_interested_${userName}`, JSON.stringify([...next]));
      return next;
    });
  }

  // ── Optimistic UI: 選出（コメント付き） ───────────────────────
  async function handleNominate(book: Book, comment?: string) {
    if (!currentUser) return;
    const bId = String(book.id);

    const prevNomId = myNominationBookId;
    const prevNomIds = [...nominatedBookIds];
    setMyNominationBookId(bId);
    setNominatedBookIds((ids) => [...ids, bId]);
    setActionLoading(bId);
    setPendingNominateBook(null);
    setNominationComment("");

    try {
      const { error } = await supabase.from("votes").insert({
        action: "選出",
        book_id: bId,
        user_name: currentUser.user_name,
        comment: comment?.trim() || null,
      });
      if (error) throw error;
      toast.success(`「${book.title}」を選出したよ 👍`);
      loadData();
    } catch {
      setMyNominationBookId(prevNomId);
      setNominatedBookIds(prevNomIds);
      toast.error("選出に失敗しました。もう一度お試しください");
    } finally {
      setActionLoading(null);
    }
  }

  // ── Optimistic UI: 選出キャンセル ─────────────────────────────
  async function handleCancelNomination() {
    if (!currentUser || !myNominationBookId) return;
    const cancelledId = myNominationBookId;

    setMyNominationBookId(null);
    setNominatedBookIds((ids) => ids.filter((id) => id !== cancelledId));
    setActionLoading("cancel");

    try {
      const { error } = await supabase
        .from("votes")
        .delete()
        .eq("book_id", cancelledId)
        .eq("user_name", currentUser.user_name)
        .eq("action", "選出");
      if (error) throw error;
      toast.success("選出をキャンセルしたよ 🙋");
      loadData();
    } catch {
      setMyNominationBookId(cancelledId);
      setNominatedBookIds((ids) => [...ids, cancelledId]);
      toast.error("キャンセルに失敗しました");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleAddBook(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim() || !currentUser) {
      toast.warning("タイトルは必ず入力してね 🙏");
      return;
    }
    setSubmittingBook(true);
    try {
      const { error } = await supabase.from("books").insert({
        title: newTitle.trim(),
        author: newAuthor.trim() || undefined,
        category: newCat || undefined,
        url: newUrl.trim() || undefined,
        created_by: currentUser.user_name,
      });
      if (error) throw error;
      toast.success(`「${newTitle}」を登録しました 🚀`);
      setNewTitle(""); setNewAuthor(""); setNewUrl("");
      setShowAddForm(false);
      await loadData();
    } catch {
      toast.error("登録に失敗しました");
    } finally {
      setSubmittingBook(false);
    }
  }

  // ── 論理削除（kentaのみ） ───────────────────────────────────────
  async function handleDeleteBook(book: Book) {
    setBookToDelete(null);
    try {
      const { error } = await supabase
        .from("books")
        .update({ deleted_at: new Date().toISOString() })
        .eq("id", String(book.id));
      if (error) throw error;
      toast.success(`「${book.title}」を削除しました`);
      loadData();
    } catch {
      toast.error("削除に失敗しました");
    }
  }

  const displayBooks = books.filter((b) => !usedBookIds.includes(String(b.id)));
  const availableCats = Array.from(
    new Set(displayBooks.map((b) => b.category).filter(Boolean) as string[])
  ).sort();
  const interestedCount = displayBooks.filter((b) => interestedBookIds.has(String(b.id))).length;
  const newBooksCount = displayBooks.filter(
    (b) => lastPastEventDate !== null && b.created_at && b.created_at.substring(0, 10) > lastPastEventDate
  ).length;
  const filterOptions = [
    "すべて",
    ...(newBooksCount > 0 ? ["NEW"] : []),
    ...(interestedCount > 0 ? ["気になる"] : []),
    ...availableCats,
  ];

  const filteredBooks =
    selectedCat === "すべて"
      ? displayBooks
      : selectedCat === "NEW"
        ? displayBooks.filter(
            (b) => lastPastEventDate !== null && b.created_at && b.created_at.substring(0, 10) > lastPastEventDate
          )
        : selectedCat === "気になる"
          ? displayBooks.filter((b) => interestedBookIds.has(String(b.id)))
          : displayBooks.filter((b) => b.category === selectedCat);

  const handleRefresh = useCallback(async () => {
    await loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div>
        <UserHeader />
        <BooksPageSkeleton />
      </div>
    );
  }

  return (
    <PullToRefreshWrapper onRefresh={handleRefresh}>
      <UserHeader onRefresh={handleRefresh} />
      <NextEventBanner event={nextEvent} />

      {/* My nomination status */}
      {myNominationBookId && (
        <div className="mx-4 mt-3 p-3 bg-green-50 border border-green-200 rounded-xl flex items-center justify-between">
          <p className="text-sm text-green-700 font-medium">
            ✅ もうすでに1冊選んでるよ
          </p>
          <button
            onClick={handleCancelNomination}
            disabled={actionLoading === "cancel"}
            className="text-xs text-green-600 border border-green-300 rounded-full px-3 py-1 hover:bg-green-100 transition-colors disabled:opacity-50"
          >
            {actionLoading === "cancel" ? "..." : "選び直す"}
          </button>
        </div>
      )}

      {/* Add book button */}
      <div className="px-4 mt-3">
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className={cn(
            "w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all",
            showAddForm
              ? "bg-gray-100 text-gray-600"
              : "bg-blue-600 text-white hover:bg-blue-700 active:scale-[0.98]"
          )}
        >
          {showAddForm ? <><X size={16} /> 閉じる</> : <><Plus size={16} /> 新しい本を登録する</>}
        </button>
      </div>

      {/* Add book form */}
      {showAddForm && (
        <div className="mx-4 mt-2 p-4 bg-white border border-gray-200 rounded-2xl shadow-sm">
          <form onSubmit={handleAddBook} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">* 書籍タイトル</label>
              <input type="text" value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
                placeholder="タイトルを入力"
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">著者名</label>
              <input type="text" value={newAuthor} onChange={(e) => setNewAuthor(e.target.value)}
                placeholder="著者名を入力"
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-2">カテゴリー</label>
              <div className="flex flex-wrap gap-2">
                {categories.map((cat) => (
                  <button key={cat} type="button" onClick={() => setNewCat(cat)}
                    className={cn(
                      "px-3 py-1 rounded-full text-xs font-medium border transition-colors",
                      newCat === cat
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
                    )}>
                    {cat}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">詳細URL</label>
              <input type="url" value={newUrl} onChange={(e) => setNewUrl(e.target.value)}
                placeholder="https://..."
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
            </div>
            <button type="submit" disabled={submittingBook}
              className="w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 active:scale-[0.98] transition-all disabled:opacity-50">
              {submittingBook ? "登録中..." : "本を登録する"}
            </button>
          </form>
        </div>
      )}

      {/* Category filter pills */}
      <div className="px-4 mt-4">
        <div className="flex flex-wrap gap-2">
          {filterOptions.map((opt) => (
            <button key={opt} onClick={() => setSelectedCat(opt)}
              className={cn(
                "px-4 py-1.5 rounded-full text-xs font-medium border transition-colors",
                selectedCat === opt
                  ? opt === "気になる"
                    ? "bg-yellow-400 text-yellow-900 border-yellow-400"
                    : opt === "NEW"
                      ? "bg-rose-500 text-white border-rose-500"
                      : "bg-blue-600 text-white border-blue-600"
                  : opt === "NEW"
                    ? "bg-white text-rose-500 border-rose-200 hover:border-rose-400"
                    : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
              )}>
              {opt === "気になる" ? `🔖 ${opt}` : opt === "NEW" ? `🆕 ${opt}` : opt}
            </button>
          ))}
        </div>
      </div>

      {/* Book list */}
      <div className="px-4 mt-2 pb-4 space-y-4">
        {filteredBooks.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-4xl mb-3">
              {selectedCat === "気になる" ? "🔖" : selectedCat === "NEW" ? "🆕" : "📭"}
            </p>
            <p className="text-sm">
              {selectedCat === "気になる"
                ? "気になる本をブックマークしてみよう"
                : selectedCat === "NEW"
                  ? "前回以降に追加された本はありません"
                  : "該当する本がありません"}
            </p>
          </div>
        ) : (
          (() => {
            const cats = Array.from(
              new Set(filteredBooks.map((b) => b.category).filter(Boolean) as string[])
            );
            return cats.map((cat) => (
              <div key={cat}>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
                  📂 {cat}
                </h3>
                <div className="space-y-2">
                  {filteredBooks.filter((b) => b.category === cat).map((book) => {
                    const bId = String(book.id);
                    const isMyNom = bId === myNominationBookId;
                    const isOthersNom = !isMyNom && nominatedBookIds.includes(bId);
                    const hasUrl = book.url && book.url.startsWith("http");
                    const isLoading = actionLoading === bId;
                    const isInterested = interestedBookIds.has(bId);
                    const isPendingNominate = pendingNominateBook?.id === book.id;
                    const isNew = lastPastEventDate !== null &&
                      book.created_at &&
                      book.created_at.substring(0, 10) > lastPastEventDate;

                    return (
                      <div key={bId}
                        className={cn(
                          "bg-white rounded-2xl border p-4 shadow-sm book-card transition-all duration-200",
                          isMyNom ? "border-green-200 bg-green-50/30" : "border-gray-100"
                        )}>
                        {/* Title + bookmark button */}
                        <div className="flex items-start gap-2 mb-3">
                          <div className="flex-1 min-w-0">
                            {isNew && (
                              <span className="inline-block text-[10px] font-black tracking-wide bg-rose-500 text-white px-1.5 py-0.5 rounded mr-1.5 align-middle leading-none">
                                NEW
                              </span>
                            )}
                            {hasUrl ? (
                              <a href={book.url!} target="_blank" rel="noopener noreferrer"
                                className="inline items-start gap-1 text-blue-600 font-bold text-base leading-snug hover:opacity-80 active:opacity-60">
                                <span>{book.title}</span>
                                <ExternalLink size={14} className="inline ml-0.5 mb-0.5 opacity-60" />
                              </a>
                            ) : (
                              <span className="font-bold text-base text-gray-900 leading-snug">{book.title}</span>
                            )}
                            {book.author && (
                              <p className="text-xs text-gray-400 mt-1">{book.author}</p>
                            )}
                          </div>
                          {/* 気になるボタン */}
                          <button
                            onClick={() => toggleInterested(bId)}
                            className="flex-shrink-0 p-1.5 rounded-full hover:bg-gray-100 active:scale-90 transition-all"
                            aria-label={isInterested ? "気になるを解除" : "気になる"}
                          >
                            <Bookmark
                              size={16}
                              className={cn(
                                "transition-colors",
                                isInterested
                                  ? "fill-yellow-400 text-yellow-400"
                                  : "text-gray-300"
                              )}
                            />
                          </button>
                          {/* 削除ボタン（kentaのみ） */}
                          {currentUser?.user_name === "kenta" && (
                            <button
                              onClick={() => setBookToDelete(book)}
                              className="flex-shrink-0 p-1.5 rounded-full hover:bg-red-50 active:scale-90 transition-all"
                              aria-label="削除"
                            >
                              <Trash2 size={14} className="text-gray-300 hover:text-red-400 transition-colors" />
                            </button>
                          )}
                        </div>

                        {/* Nomination button / inline comment form */}
                        {isMyNom ? (
                          <div className="w-full text-center py-2 bg-green-100 text-green-700 text-sm font-medium rounded-xl border border-green-200">
                            ✅ これを選んでるよ
                          </div>
                        ) : isOthersNom ? (
                          <div className="w-full text-center py-2 bg-gray-50 text-gray-400 text-sm rounded-xl border border-gray-100">
                            🙅 他の人が選んでるよ
                          </div>
                        ) : isPendingNominate ? (
                          /* インラインコメントフォーム */
                          <div className="space-y-2">
                            <textarea
                              value={nominationComment}
                              onChange={(e) => setNominationComment(e.target.value)}
                              placeholder="推薦コメント（任意）"
                              rows={2}
                              autoFocus
                              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleNominate(book, nominationComment)}
                                disabled={isLoading || actionLoading !== null}
                                className="flex-1 py-2 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 active:scale-[0.98] transition-all disabled:opacity-50"
                              >
                                {isLoading ? "選出中..." : "選出する"}
                              </button>
                              <button
                                onClick={() => { setPendingNominateBook(null); setNominationComment(""); }}
                                className="px-4 py-2 text-sm text-gray-500 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
                              >
                                キャンセル
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => {
                              if (myNominationBookId !== null || actionLoading !== null) return;
                              setPendingNominateBook(book);
                              setNominationComment("");
                            }}
                            disabled={isLoading || myNominationBookId !== null || actionLoading !== null}
                            className={cn(
                              "w-full py-2 rounded-xl text-sm font-medium transition-all active:scale-[0.98]",
                              myNominationBookId !== null
                                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                                : "bg-blue-600 text-white hover:bg-blue-700"
                            )}>
                            {isLoading ? "選出中..." : myNominationBookId !== null ? "既に選出済みです" : "これが読みたい"}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ));
          })()
        )}
      </div>
      {/* Delete confirmation modal */}
      {bookToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/40">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm">
            <h3 className="font-bold text-lg text-gray-900 mb-2">本を削除しますか？</h3>
            <p className="text-sm text-gray-500 mb-6">
              「{bookToDelete.title}」をリストから削除します。<br />
              削除後もデータは保持され、復元できます。
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setBookToDelete(null)}
                className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                キャンセル
              </button>
              <button
                onClick={() => handleDeleteBook(bookToDelete)}
                className="flex-1 py-2.5 bg-red-500 text-white rounded-xl text-sm font-medium hover:bg-red-600 active:scale-[0.98] transition-all"
              >
                削除する
              </button>
            </div>
          </div>
        </div>
      )}
    </PullToRefreshWrapper>
  );
}
