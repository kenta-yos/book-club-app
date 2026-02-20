"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase/client";
import type { Book, Vote, User } from "@/lib/types";
import { UserHeader } from "@/components/UserHeader";
import { VotesPageSkeleton } from "@/components/Skeleton";
import { PullToRefreshWrapper } from "@/components/PullToRefreshWrapper";
import { toast } from "sonner";
import { ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

type NominatedEntry = {
  book_id: string;
  user_name: string;
  title: string;
  author: string | null;
  url: string | null;
  total_points: number;
  voters: { user_name: string; icon: string; points: number }[];
};

export default function VotesPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [nominated, setNominated] = useState<NominatedEntry[]>([]);
  const [userIconMap, setUserIconMap] = useState<Record<string, string>>({});

  // ── Optimistic UI 用state ──────────────────────────────────────
  // myVotes を楽観的に先行更新する
  const [myVotes, setMyVotes] = useState<Vote[]>([]);
  // ─────────────────────────────────────────────────────────────

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

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

    try {
      const [usersRes, booksRes, eventsRes, votesRes] = await Promise.all([
        supabase.from("users").select("user_name, icon"),
        supabase.from("books").select("*"),
        supabase.from("events").select("book_id, event_date"),
        supabase.from("votes").select("*"),
      ]);

      const allUsers = usersRes.data || [];
      const allBooks = booksRes.data || [];
      const allEvents = eventsRes.data || [];
      const allVotes = votesRes.data || [];

      const iconMap: Record<string, string> = {};
      allUsers.forEach((u: any) => { iconMap[u.user_name] = u.icon; });
      setUserIconMap(iconMap);

      const usedIds = allEvents.map((e: any) => String(e.book_id));
      const activeVotes = allVotes.filter((v: any) => !usedIds.includes(String(v.book_id)));
      const nominations = activeVotes.filter((v: any) => v.action === "選出");
      const voteOnly = activeVotes.filter((v: any) => v.action === "投票");

      const myVoteList = voteOnly.filter((v: any) => v.user_name === uName);
      setMyVotes(myVoteList);

      const booksMap: Record<string, Book> = {};
      allBooks.forEach((b: any) => { booksMap[String(b.id)] = b; });

      const entries: NominatedEntry[] = nominations.map((nom: any) => {
        const bId = String(nom.book_id);
        const book = booksMap[bId];
        const bookVotes = voteOnly.filter((v: any) => String(v.book_id) === bId);
        const totalPoints = bookVotes.reduce((sum: number, v: any) => sum + (v.points || 0), 0);
        const voters = bookVotes.map((v: any) => ({
          user_name: v.user_name,
          icon: iconMap[v.user_name] || "👤",
          points: v.points || 0,
        }));
        return {
          book_id: bId,
          user_name: nom.user_name,
          title: book?.title || "不明",
          author: book?.author || null,
          url: book?.url || null,
          total_points: totalPoints,
          voters,
        };
      });

      entries.sort((a, b) => b.total_points - a.total_points);
      setNominated(entries);
    } catch {
      toast.error("データの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Optimistic UI: 投票 ────────────────────────────────────────
  async function handleVote(bookId: string, points: 1 | 2) {
    if (!currentUser) return;
    const key = `vote_${bookId}_${points}`;
    setActionLoading(key);

    // 楽観的更新: myVotes に仮エントリを追加 & ランキングのポイントも即時加算
    const optimisticVote: Vote = {
      id: `optimistic_${Date.now()}`,
      created_at: new Date().toISOString(),
      action: "投票",
      book_id: bookId,
      user_name: currentUser.user_name,
      points,
    };
    const prevMyVotes = [...myVotes];
    const prevNominated = [...nominated];

    setMyVotes((prev) => [...prev, optimisticVote]);
    setNominated((prev) =>
      prev
        .map((entry) =>
          entry.book_id === bookId
            ? {
                ...entry,
                total_points: entry.total_points + points,
                voters: [
                  ...entry.voters,
                  { user_name: currentUser.user_name, icon: userIconMap[currentUser.user_name] || "👤", points },
                ],
              }
            : entry
        )
        .sort((a, b) => b.total_points - a.total_points)
    );

    try {
      const { error } = await supabase.from("votes").insert({
        action: "投票",
        book_id: bookId,
        user_name: currentUser.user_name,
        points,
      });
      if (error) throw error;
      toast.success(`${points}点投票しました 🗳️`);
      // バックグラウンドで正確なデータと同期
      loadData();
    } catch {
      // ロールバック
      setMyVotes(prevMyVotes);
      setNominated(prevNominated);
      toast.error("投票に失敗しました。もう一度お試しください");
    } finally {
      setActionLoading(null);
    }
  }

  // ── Optimistic UI: 投票取消 ────────────────────────────────────
  async function handleCancelVote(bookId: string) {
    if (!currentUser) return;
    const key = `del_${bookId}`;
    setActionLoading(key);

    const cancelledVote = myVotes.find((v) => String(v.book_id) === bookId);
    const cancelledPoints = cancelledVote?.points || 0;
    const prevMyVotes = [...myVotes];
    const prevNominated = [...nominated];

    // 楽観的更新
    setMyVotes((prev) => prev.filter((v) => String(v.book_id) !== bookId));
    setNominated((prev) =>
      prev
        .map((entry) =>
          entry.book_id === bookId
            ? {
                ...entry,
                total_points: Math.max(0, entry.total_points - cancelledPoints),
                voters: entry.voters.filter((v) => v.user_name !== currentUser.user_name),
              }
            : entry
        )
        .sort((a, b) => b.total_points - a.total_points)
    );

    try {
      const { error } = await supabase
        .from("votes")
        .delete()
        .eq("user_name", currentUser.user_name)
        .eq("book_id", bookId)
        .eq("action", "投票");
      if (error) throw error;
      toast.success("投票を取り消しました");
      loadData();
    } catch {
      setMyVotes(prevMyVotes);
      setNominated(prevNominated);
      toast.error("取り消しに失敗しました");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleResetAllVotes() {
    if (!currentUser) return;
    setActionLoading("reset");

    const prevMyVotes = [...myVotes];
    const prevNominated = [...nominated];

    // 楽観的更新
    setMyVotes([]);
    setNominated((prev) =>
      prev.map((entry) => ({
        ...entry,
        total_points: entry.voters
          .filter((v) => v.user_name !== currentUser.user_name)
          .reduce((sum, v) => sum + v.points, 0),
        voters: entry.voters.filter((v) => v.user_name !== currentUser.user_name),
      })).sort((a, b) => b.total_points - a.total_points)
    );

    try {
      const { error } = await supabase
        .from("votes")
        .delete()
        .eq("user_name", currentUser.user_name)
        .eq("action", "投票");
      if (error) throw error;
      toast.success("自分の投票をリセットしました 🙋");
      loadData();
    } catch {
      setMyVotes(prevMyVotes);
      setNominated(prevNominated);
      toast.error("リセットに失敗しました");
    } finally {
      setActionLoading(null);
    }
  }

  const handleRefresh = useCallback(async () => { await loadData(); }, [loadData]);

  if (loading) {
    return (
      <div>
        <UserHeader />
        <VotesPageSkeleton />
      </div>
    );
  }

  const maxPoints = nominated.length > 0 ? Math.max(...nominated.map((n) => n.total_points)) : 0;
  const myVotePoints = myVotes.map((v) => v.points);

  return (
    <PullToRefreshWrapper onRefresh={handleRefresh}>
      <UserHeader onRefresh={handleRefresh} />

      {/* Ranking Section */}
      <div className="px-4 pt-4">
        <h2 className="text-lg font-bold text-gray-900 mb-3">🏆 Ranking</h2>

        {nominated.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-4xl mb-3">🗳️</p>
            <p className="text-sm">まだ候補が選ばれていません</p>
          </div>
        ) : (
          <div className="space-y-1 bg-white rounded-2xl border border-gray-100 p-3 shadow-sm">
            {nominated.map((entry, idx) => {
              const isTop = entry.total_points === maxPoints && maxPoints > 0;
              const voterSummary = entry.voters.map((v) => `${v.icon} ${v.points}`).join(" + ");

              return (
                <div key={entry.book_id}>
                  <div className="flex items-center gap-2 py-2">
                    <div className="flex items-center gap-1 flex-1 min-w-0">
                      {isTop && <span className="text-base flex-shrink-0">👑</span>}
                      <span className={cn("font-bold text-sm truncate", isTop ? "text-orange-700" : "text-gray-800")}>
                        {entry.title}
                      </span>
                    </div>
                    <div className="flex items-baseline gap-0.5 flex-shrink-0">
                      <span className={cn("text-xl font-bold transition-all duration-300", isTop ? "text-orange-600" : "text-blue-600")}>
                        {entry.total_points}
                      </span>
                      <span className="text-xs text-gray-400">pts</span>
                    </div>
                  </div>
                  {voterSummary && (
                    <p className="text-xs text-gray-400 pb-1 pl-1">...{voterSummary}</p>
                  )}
                  {idx < nominated.length - 1 && <hr className="border-gray-100" />}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Vote Section */}
      {nominated.length > 0 && (
        <div className="px-4 mt-6">
          <h2 className="text-lg font-bold text-gray-900 mb-3">🗳️ 投票</h2>
          <div className="space-y-3">
            {nominated.map((entry) => {
              const myVoteForThis = myVotes.find((v) => String(v.book_id) === entry.book_id);
              const currentPoints = myVoteForThis?.points || 0;
              const isMyNomination = entry.user_name === currentUser?.user_name;
              const hasUrl = entry.url && entry.url.startsWith("http");
              const nominatorIcon = userIconMap[entry.user_name] || "👤";
              const canVote1 = !isMyNomination && !myVotePoints.includes(1) && currentPoints === 0;
              const canVote2 = !isMyNomination && !myVotePoints.includes(2) && currentPoints === 0;

              return (
                <div key={entry.book_id}
                  className={cn(
                    "bg-white rounded-2xl border p-4 shadow-sm transition-all duration-200",
                    currentPoints > 0 ? "border-blue-100 bg-blue-50/20" : "border-gray-100"
                  )}>
                  {/* Book info */}
                  <div className="mb-3">
                    {hasUrl ? (
                      <a href={entry.url!} target="_blank" rel="noopener noreferrer"
                        className="flex items-start gap-1 text-blue-600 font-bold text-base leading-snug hover:opacity-80">
                        <span className="flex-1">{entry.title}</span>
                        <ExternalLink size={14} className="flex-shrink-0 mt-0.5 opacity-60" />
                      </a>
                    ) : (
                      <p className="font-bold text-base text-gray-900 leading-snug">{entry.title}</p>
                    )}
                    {entry.author && <p className="text-xs text-gray-400 mt-0.5">{entry.author}</p>}
                    <div className="mt-2">
                      <span className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 text-xs font-medium px-2 py-0.5 rounded-full border border-blue-100">
                        推薦: {nominatorIcon} {entry.user_name}
                      </span>
                    </div>
                  </div>

                  {/* Vote buttons */}
                  {isMyNomination ? (
                    <div className="text-center py-2 text-xs text-gray-400 bg-gray-50 rounded-xl">
                      自分が選出した本には投票できません
                    </div>
                  ) : currentPoints > 0 ? (
                    <div className="flex items-center gap-2">
                      <div className="flex-1 text-center py-2 bg-blue-100 text-blue-700 text-sm font-bold rounded-xl border border-blue-200 transition-all duration-200">
                        +{currentPoints} 点投票済み ✓
                      </div>
                      <button
                        onClick={() => handleCancelVote(entry.book_id)}
                        disabled={actionLoading === `del_${entry.book_id}`}
                        className="px-3 py-2 text-xs text-red-500 border border-red-200 rounded-xl hover:bg-red-50 transition-colors disabled:opacity-50">
                        {actionLoading === `del_${entry.book_id}` ? "..." : "取消"}
                      </button>
                    </div>
                  ) : (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleVote(entry.book_id, 1)}
                        disabled={!canVote1 || actionLoading !== null}
                        className={cn(
                          "flex-1 py-2 rounded-xl text-sm font-medium transition-all active:scale-[0.97]",
                          canVote1
                            ? "bg-white border-2 border-blue-400 text-blue-600 hover:bg-blue-50"
                            : "bg-gray-100 text-gray-300 cursor-not-allowed"
                        )}>
                        {actionLoading === `vote_${entry.book_id}_1` ? "..." : "+1"}
                      </button>
                      <button
                        onClick={() => handleVote(entry.book_id, 2)}
                        disabled={!canVote2 || actionLoading !== null}
                        className={cn(
                          "flex-1 py-2 rounded-xl text-sm font-bold transition-all active:scale-[0.97]",
                          canVote2
                            ? "bg-blue-600 text-white hover:bg-blue-700"
                            : "bg-gray-100 text-gray-300 cursor-not-allowed"
                        )}>
                        {actionLoading === `vote_${entry.book_id}_2` ? "..." : "+2"}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Reset all my votes */}
          <div className="mt-4 pb-2">
            <hr className="border-gray-200 mb-4" />
            <button
              onClick={handleResetAllVotes}
              disabled={actionLoading === "reset" || myVotes.length === 0}
              className="w-full py-2.5 text-sm text-gray-500 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
              {actionLoading === "reset" ? "リセット中..." : "自分の投票をすべてリセット"}
            </button>
          </div>
        </div>
      )}
    </PullToRefreshWrapper>
  );
}
