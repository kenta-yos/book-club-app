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

    const authorMeta =
      html.match(
        /<meta[^>]+name=["']author["'][^>]+content=["']([^"']+)["']/i
      )?.[1] ??
      html.match(
        /<meta[^>]+content=["']([^"']+)["'][^>]+name=["']author["']/i
      )?.[1];

    const title = (ogTitle ?? pageTitle ?? "").trim();
    if (!title) return null;

    return { title, author: (authorMeta ?? "").trim() };
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
