"use client";

import type { EventWithBook } from "@/lib/types";

interface NextEventBannerProps {
  event: EventWithBook | null;
}

export function NextEventBanner({ event }: NextEventBannerProps) {
  if (!event) {
    return (
      <div className="mx-4 mt-3 mb-1 p-3 bg-blue-50 border border-blue-100 rounded-xl">
        <p className="text-sm text-blue-600">📅 次回の開催は未定です。</p>
      </div>
    );
  }

  const book = event.books;
  const dateStr = event.event_date.replace(/-/g, "/");
  const hasUrl = book?.url && book.url.startsWith("http");

  return (
    <div className="mx-4 mt-3 mb-1 p-3 bg-blue-50 border border-blue-100 rounded-xl">
      <p className="text-xs text-blue-500 font-medium mb-1">
        📅 次回の開催: {dateStr}
      </p>
      {book ? (
        <p className="text-sm font-semibold text-blue-800">
          📖 課題本:{" "}
          {hasUrl ? (
            <a
              href={book.url!}
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:opacity-80"
            >
              {book.title}
            </a>
          ) : (
            book.title
          )}
        </p>
      ) : (
        <p className="text-sm text-blue-600">課題本: 未定</p>
      )}
    </div>
  );
}
