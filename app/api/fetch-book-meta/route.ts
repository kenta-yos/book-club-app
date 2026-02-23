import { NextRequest, NextResponse } from "next/server";

/** URLまたは文字列からISBN-13を抽出（ハイフンありなし両対応） */
function extractISBN(text: string): string | null {
  const clean = text.replace(/-/g, "");
  const match = clean.match(/(?:978|979)\d{10}/);
  return match ? match[0] : null;
}

/** 版元ドットコム API でISBNから書籍情報を取得 */
async function fetchFromHanmoto(
  isbn: string
): Promise<{ title: string; author: string } | null> {
  try {
    const res = await fetch(
      `https://api.hanmoto.com/books/isbn/${isbn}.json`,
      { next: { revalidate: 3600 } }
    );
    if (!res.ok) return null;
    const data = await res.json();

    // トップレベルフィールドを優先、次にONIX構造を参照
    let title: string = data.title ?? "";
    let author: string = data.author ?? "";

    if (!title) {
      title =
        data.onix?.DescriptiveDetail?.TitleDetail?.TitleElement?.TitleText
          ?.content ?? "";
    }

    if (!author) {
      const raw = data.onix?.DescriptiveDetail?.Contributor;
      if (raw) {
        const arr: any[] = Array.isArray(raw) ? raw : [raw];
        author = arr
          .map((c) => c.PersonName?.content ?? c.PersonName ?? "")
          .filter(Boolean)
          .join(", ");
      }
    }

    if (!title) return null;
    return { title, author };
  } catch {
    return null;
  }
}

/** OGP / meta タグから書籍情報を取得（フォールバック） */
async function fetchFromOGP(
  url: string
): Promise<{ title: string; author: string } | null> {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 6000);

    const res = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; BookClubApp/1.0)" },
      signal: controller.signal,
    });
    clearTimeout(timer);

    if (!res.ok) return null;
    const html = await res.text();

    // og:title（属性順序が異なる2パターンに対応）
    const ogTitle =
      html.match(
        /<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']/i
      )?.[1] ??
      html.match(
        /<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:title["']/i
      )?.[1];

    const pageTitle = html.match(/<title[^>]*>([^<]+)<\/title>/i)?.[1];

    // pageTitle は「書名 - 出版社名」「書名｜出版社名」形式が多いので末尾のサフィックスを除去
    // og:title はクリーンなことが多いためそちらを優先し、pageTitle のみ除去を適用
    const cleanPageTitle = pageTitle?.trim()
      ? (pageTitle.trim().replace(/\s*[-|｜]\s*[^-|｜]+$/, "").trim() ||
          pageTitle.trim())
      : undefined;

    const title = (ogTitle?.trim() ?? cleanPageTitle ?? "").trim();
    if (!title) return null;

    // 著者: <meta name="author">
    const authorMeta =
      html.match(
        /<meta[^>]+name=["']author["'][^>]+content=["']([^"']+)["']/i
      )?.[1] ??
      html.match(
        /<meta[^>]+content=["']([^"']+)["'][^>]+name=["']author["']/i
      )?.[1];

    // 著者: JSON-LD (@type: "Book") — 多くのサイトはこちらに著者情報を持つ
    let authorFromJsonLd = "";
    const jsonLdBlocks = [
      ...html.matchAll(
        /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi
      ),
    ];
    for (const match of jsonLdBlocks) {
      try {
        const data = JSON.parse(match[1]);
        const items: any[] = Array.isArray(data) ? data : [data];
        for (const item of items) {
          if (item["@type"] === "Book" && item.author) {
            const a = item.author;
            if (typeof a === "string") {
              authorFromJsonLd = a;
            } else if (Array.isArray(a)) {
              authorFromJsonLd = a
                .map((x: any) => x?.name ?? x ?? "")
                .filter(Boolean)
                .join(", ");
            } else if (a?.name) {
              authorFromJsonLd = a.name;
            }
            if (authorFromJsonLd) break;
          }
        }
        if (authorFromJsonLd) break;
      } catch {
        // JSON パースエラーは無視
      }
    }

    const author = (authorFromJsonLd || authorMeta || "").trim();

    return { title, author };
  } catch {
    return null;
  }
}

export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get("url");
  if (!url) {
    return NextResponse.json({ error: "URLが必要です" }, { status: 400 });
  }

  // ① URLからISBNを取り出して版元ドットコムAPIを試みる
  const isbn = extractISBN(url);
  if (isbn) {
    const result = await fetchFromHanmoto(isbn);
    if (result) return NextResponse.json(result);
  }

  // ② フォールバック: OGP/メタタグをスクレイピング
  const result = await fetchFromOGP(url);
  if (result) return NextResponse.json(result);

  return NextResponse.json(
    { error: "書籍情報を取得できませんでした" },
    { status: 404 }
  );
}
