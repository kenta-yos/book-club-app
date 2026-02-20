import { BottomNav } from "@/components/BottomNav";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // h-screen + overflow-hidden でページ全体の高さを固定し、
    // 各ページ内の PullToRefreshWrapper が独立してスクロールできるようにする
    <div className="h-screen bg-gray-50 flex flex-col overflow-hidden">
      <main className="flex-1 overflow-hidden pb-20">
        {children}
      </main>
      <BottomNav />
    </div>
  );
}
