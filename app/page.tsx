"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase/client";
import type { User } from "@/lib/types";
import { toast } from "sonner";

export default function LoginPage() {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [loggingIn, setLoggingIn] = useState<string | null>(null);

  useEffect(() => {
    // Check if already logged in
    const stored = sessionStorage.getItem("bookclub_user");
    if (stored) {
      router.replace("/books");
      return;
    }
    fetchUsers();
  }, [router]);

  async function fetchUsers() {
    const { data, error } = await supabase
      .from("users")
      .select("user_name, icon")
      .order("user_name");

    if (error) {
      toast.error("ユーザー取得に失敗しました");
    } else {
      setUsers(data || []);
    }
    setLoading(false);
  }

  async function handleLogin(user: User) {
    setLoggingIn(user.user_name);
    try {
      // Log access
      await supabase
        .from("access_logs")
        .insert({ user_name: user.user_name })
        .then(() => {}); // ignore errors

      // Store user in sessionStorage
      sessionStorage.setItem("bookclub_user", JSON.stringify(user));

      toast.success(`${user.icon} ${user.user_name} さん、こんにちは！`);
      router.push("/books");
    } catch {
      toast.error("ログインに失敗しました");
      setLoggingIn(null);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-50 to-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-500 text-sm">読み込み中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex flex-col">
      {/* Header */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
        <div className="mb-8 text-center">
          <div className="text-6xl mb-4">📚</div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Book Club</h1>
          <p className="text-gray-500 text-sm">メンバーを選んでください</p>
        </div>

        {/* User grid */}
        <div className="w-full max-w-sm grid grid-cols-3 gap-3">
          {users.map((user) => (
            <button
              key={user.user_name}
              onClick={() => handleLogin(user)}
              disabled={loggingIn !== null}
              className="flex flex-col items-center justify-center gap-2 p-4 bg-white rounded-2xl shadow-sm border border-gray-100 hover:border-blue-300 hover:shadow-md active:scale-95 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loggingIn === user.user_name ? (
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              ) : (
                <span className="text-3xl leading-none">{user.icon}</span>
              )}
              <span className="text-xs font-medium text-gray-700 text-center leading-tight break-all">
                {user.user_name}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="text-center pb-8 text-xs text-gray-400">
        Book Club App
      </div>
    </div>
  );
}
