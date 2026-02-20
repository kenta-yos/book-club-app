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
import { Plus, X, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

export default function BooksPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [usedBookIds, setUsedBookIds] = useState<string[]>([]);

  // ── Optimistic UI 用state ──────────────────────────────────────
  // null = 未選出, string = 選出済みbook_id (楽観的に先行更新)
  const [myNominationBookId, setMyNominationBookId] = useState<string | null>(null);
  const [nominatedBookIds, setNominatedBookIds] = useState<string[]>([]);
  // ─────────────────────────────────────────────────────────────

  const [nextEvent, setNextEvent] = useState<EventWithBook | null>(null);
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

  // ユーザー名をrefで保持（loadData内で参照するため）
  const userNameRef = useRef<string>("");

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

    // 初回のみローディング表示（リフレッシュ時は表示しない）
    setLoading((prev) => prev);

    try {
      const [booksRes, catsRes, eventsRes, votesRes] = await Promise.all([
        supabase.from("books").select("*"),
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

      setBooks(allBooks);
      setCategories(allCats);
      if (allCats.length > 0 && !newCat) setNewCat(allCats[0]);
    } catch {
      toast.error("データの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, [newCat]);

  // ── Optimistic UI: 選出 ────────────────────────────────────────
  async function handleNominate(book: Book) {
    if (!currentUser) return;
    const bId = String(book.id);

    // 1. 先にUIを更新（楽観的）
    const prevNomId = myNominationBookId;
    const prevNomIds = [...nominatedBookIds];
    setMyNominationBookId(bId);
    setNominatedBookIds((ids) => [...ids, bId]);
    setActionLoading(bId);

    try {
      const { error } = await supabase.from("votes").insert({
        action: "選出",
        book_id: bId,
        user_name: currentUser.user_name,
      });
      if (error) throw error;
      toast.success(`「${book.title}」を選出したよ 👍`);
      // バックグラウンドで同期（UIはすでに更新済み）
      loadData();
    } catch {
      // 2. 失敗したらロールバック
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

    // 1. 先にUIを更新
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
      // ロールバック
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

  const displayBooks = books.filter((b) => !usedBookIds.includes(String(b.id)));
  const filteredBooks = selectedCat === "すべて"
    ? displayBooks
    : displayBooks.filter((b) => b.category === selectedCat);
  const availableCats = Array.from(
    new Set(displayBooks.map((b) => b.category).filter(Boolean) as string[])
  ).sort();
  const filterOptions = ["すべて", ...availableCats];

  // Pull to Refresh 用コールバック
  const handleRefresh = useCallback(async () => {
    await loadData();
  }, [loadData]);

  // ── 初回ローディング: スケルトン表示 ──────────────────────────
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

      {/* Manual link */}
      <div className="flex justify-end px-4 mt-2">
        <a
          href="https://embed.app.guidde.com/playbooks/3mLXzjBGrBBuNNJZ66rV9D?mode=docOnly"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-gray-400 border border-gray-200 px-3 py-1 rounded-full bg-white hover:bg-gray-50 flex items-center gap-1"
        >
          ❔ 本の選出・投票の方法
        </a>
      </div>

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
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
              )}>
              {opt}
            </button>
          ))}
        </div>
      </div>

      {/* Book list */}
      <div className="px-4 mt-2 pb-4 space-y-4">
        {filteredBooks.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-4xl mb-3">📭</p>
            <p className="text-sm">該当する本がありません</p>
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

                    return (
                      <div key={bId}
                        className={cn(
                          "bg-white rounded-2xl border p-4 shadow-sm book-card transition-all duration-200",
                          isMyNom ? "border-green-200 bg-green-50/30" : "border-gray-100"
                        )}>
                        {/* Title */}
                        <div className="mb-3">
                          {hasUrl ? (
                            <a href={book.url!} target="_blank" rel="noopener noreferrer"
                              className="flex items-start gap-1 text-blue-600 font-bold text-base leading-snug hover:opacity-80 active:opacity-60">
                              <span className="flex-1">{book.title}</span>
                              <ExternalLink size={14} className="flex-shrink-0 mt-0.5 opacity-60" />
                            </a>
                          ) : (
                            <p className="font-bold text-base text-gray-900 leading-snug">{book.title}</p>
                          )}
                          {book.author && (
                            <p className="text-xs text-gray-400 mt-1">{book.author}</p>
                          )}
                        </div>

                        {/* Nomination button */}
                        {isMyNom ? (
                          <div className="w-full text-center py-2 bg-green-100 text-green-700 text-sm font-medium rounded-xl border border-green-200">
                            ✅ これを選んでるよ
                          </div>
                        ) : isOthersNom ? (
                          <div className="w-full text-center py-2 bg-gray-50 text-gray-400 text-sm rounded-xl border border-gray-100">
                            🙅 他の人が選んでるよ
                          </div>
                        ) : (
                          <button
                            onClick={() => handleNominate(book)}
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
    </PullToRefreshWrapper>
  );
}
