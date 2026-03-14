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

/** タイトルから末尾の出版社サフィックスを除去 */
function cleanTitleSuffix(raw: string): string {
  // 「書名 - 出版社」「書名 | 出版社」「書名｜出版社」「書名 — 出版社」
  // 「書名 -- 出版社」「書名：出版社」「書名 : 出版社」 などの形式に対応
  const cleaned = raw
    .replace(/\s*(?:--|—|－)\s*[^-—－]+$/, "")
    .replace(/\s*[|｜]\s*[^|｜]+$/, "")
    .replace(/\s*[：:]\s*[^：:]+$/, "")
    .replace(/\s*-\s+[^-]+$/, "")
    .trim();
  return cleaned || raw.trim();
}

/** author オブジェクトから著者名を文字列化 */
function resolveAuthor(a: any): string {
  if (typeof a === "string") return a;
  if (Array.isArray(a)) {
    return a
      .map((x: any) => x?.name ?? x ?? "")
      .filter(Boolean)
      .join(", ");
  }
  if (a?.name) return a.name;
  return "";
}

/** JSON-LD から著者情報を抽出（Book / Product 両対応、review.author にも対応） */
function extractAuthorFromJsonLd(html: string): string {
  const jsonLdBlocks = [
    ...html.matchAll(
      /<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi
    ),
  ];
  for (const match of jsonLdBlocks) {
    try {
      const data = JSON.parse(match[1]);
      const items: any[] = Array.isArray(data) ? data : [data];
      // @graph の中身も展開
      for (const item of items) {
        if (item["@graph"]) {
          items.push(
            ...(Array.isArray(item["@graph"])
              ? item["@graph"]
              : [item["@graph"]])
          );
        }
      }
      for (const item of items) {
        const type = item["@type"];
        const isBookLike =
          type === "Book" ||
          type === "Product" ||
          (Array.isArray(type) &&
            (type.includes("Book") || type.includes("Product")));
        if (!isBookLike) continue;

        // 直接の author フィールド
        if (item.author) {
          const result = resolveAuthor(item.author);
          if (result) return result;
        }

        // 勁草書房・岩波書店など: review.author に著者情報が入っている場合
        const reviewAuthor = item.review?.author;
        if (reviewAuthor) {
          const result = resolveAuthor(reviewAuthor);
          if (result) return result;
        }
      }
    } catch {
      // JSON パースエラーは無視
    }
  }
  return "";
}

/** HTML からサイト固有の著者情報を抽出 */
function extractAuthorFromHtml(html: string): string {
  // Amazon: <span class="author"> 内のリンクテキスト
  const amazonAuthor = html.match(
    /<span[^>]+class=["'][^"']*author[^"']*["'][^>]*>[\s\S]*?<a[^>]*>([^<]+)</i
  )?.[1];
  if (amazonAuthor?.trim()) return amazonAuthor.trim();

  // Amazon: #bylineInfo 内の .author a
  const bylineAuthor = html.match(
    /id=["']bylineInfo["'][\s\S]*?class=["'][^"']*author[^"']*["'][\s\S]*?<a[^>]*>([^<]+)</i
  )?.[1];
  if (bylineAuthor?.trim()) return bylineAuthor.trim();

  // Amazon: contributorNameID
  const contributorName = html.match(
    /id=["']contributorNameID["'][^>]*>([^<]+)</i
  )?.[1];
  if (contributorName?.trim()) return contributorName.trim();

  // 一般的な book-authors クラス
  const bookAuthors = html.match(
    /class=["'][^"']*book-authors?[^"']*["'][^>]*>([^<]+)</i
  )?.[1];
  if (bookAuthors?.trim()) return bookAuthors.trim();

  // 学術出版社共通: <a href="/author/...">著者名</a> 著 / 編著 / ／著 などのパターン
  // 有斐閣、勁草書房、明石書店、岩波書店、新潮社などに対応
  const publisherAuthorLinks = [
    ...html.matchAll(
      /<a[^>]+href=["'][^"']*(?:\/author\/|\/writers?\/|\/bd\/search\/author\/)[^"']*["'][^>]*>([^<]+)<\/a>/gi
    ),
  ];
  if (publisherAuthorLinks.length > 0) {
    const names = publisherAuthorLinks
      .map((m) => m[1].replace(/^\[|\]$/g, "").trim())
      .filter(Boolean);
    if (names.length > 0) return names.join(", ");
  }

  // 青土社: ［著者］著者名（ふりがな）
  const seidoshaAuthor = html.match(
    /［著者］\s*([^（\n]+)/
  )?.[1];
  if (seidoshaAuthor?.trim()) return seidoshaAuthor.trim();

  return "";
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

    // og:title / pageTitle の両方にサフィックス除去を適用
    const cleanOgTitle = ogTitle?.trim()
      ? cleanTitleSuffix(ogTitle.trim())
      : undefined;
    const cleanPageTitle = pageTitle?.trim()
      ? cleanTitleSuffix(pageTitle.trim())
      : undefined;

    const title = (cleanOgTitle ?? cleanPageTitle ?? "").trim();
    if (!title) return null;

    // 著者: <meta name="author">
    const authorMeta =
      html.match(
        /<meta[^>]+name=["']author["'][^>]+content=["']([^"']+)["']/i
      )?.[1] ??
      html.match(
        /<meta[^>]+content=["']([^"']+)["'][^>]+name=["']author["']/i
      )?.[1];

    // 著者: JSON-LD（Book / Product 対応）
    const authorFromJsonLd = extractAuthorFromJsonLd(html);

    // 著者: HTML構造から抽出（Amazon等のサイト固有対応）
    const authorFromHtml = extractAuthorFromHtml(html);

    const author = (
      authorFromJsonLd ||
      authorMeta ||
      authorFromHtml ||
      ""
    ).trim();

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
