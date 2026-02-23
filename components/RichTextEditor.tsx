"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { Bold, Italic, List, ListOrdered, Heading2, Quote, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface RichTextEditorProps {
  content: string;
  onChange: (html: string) => void;
  placeholder?: string;
  minHeight?: number;
}

export function RichTextEditor({
  content,
  onChange,
  placeholder = "感想・気づき・読む前の期待など、自由に書こう...",
  minHeight = 180,
}: RichTextEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder }),
    ],
    content,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class: "tiptap-editor",
        style: `min-height: ${minHeight}px`,
      },
    },
    immediatelyRender: false,
  });

  if (!editor) return null;

  return (
    <div className="border border-gray-200 rounded-2xl overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 bg-white transition-shadow">
      {/* Toolbar */}
      <div className="flex items-center gap-0.5 px-2 py-2 border-b border-gray-100 bg-gray-50/80">
        <ToolBtn
          onClick={() => editor.chain().focus().toggleBold().run()}
          active={editor.isActive("bold")}
          title="太字"
        >
          <Bold size={15} strokeWidth={2.5} />
        </ToolBtn>
        <ToolBtn
          onClick={() => editor.chain().focus().toggleItalic().run()}
          active={editor.isActive("italic")}
          title="斜体"
        >
          <Italic size={15} />
        </ToolBtn>
        <ToolBtn
          onClick={() => editor.chain().focus().toggleStrike().run()}
          active={editor.isActive("strike")}
          title="打ち消し線"
        >
          <Minus size={15} />
        </ToolBtn>

        <div className="w-px h-4 bg-gray-200 mx-1 flex-shrink-0" />

        <ToolBtn
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          active={editor.isActive("heading", { level: 2 })}
          title="見出し"
        >
          <Heading2 size={15} />
        </ToolBtn>
        <ToolBtn
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          active={editor.isActive("blockquote")}
          title="引用"
        >
          <Quote size={15} />
        </ToolBtn>

        <div className="w-px h-4 bg-gray-200 mx-1 flex-shrink-0" />

        <ToolBtn
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          active={editor.isActive("bulletList")}
          title="箇条書き"
        >
          <List size={15} />
        </ToolBtn>
        <ToolBtn
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          active={editor.isActive("orderedList")}
          title="番号付きリスト"
        >
          <ListOrdered size={15} />
        </ToolBtn>
      </div>

      {/* Editor area */}
      <EditorContent editor={editor} />
    </div>
  );
}

function ToolBtn({
  onClick,
  active,
  title,
  children,
}: {
  onClick: () => void;
  active: boolean;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onMouseDown={(e) => {
        e.preventDefault(); // フォーカスを維持
        onClick();
      }}
      title={title}
      className={cn(
        "w-9 h-9 flex items-center justify-center rounded-lg transition-colors touch-manipulation",
        active
          ? "bg-blue-100 text-blue-700"
          : "text-gray-500 hover:bg-gray-200 active:bg-gray-300"
      )}
    >
      {children}
    </button>
  );
}

/** リッチテキスト（HTML）の読み取り専用表示 */
export function RichTextViewer({
  html,
  className,
}: {
  html: string;
  className?: string;
}) {
  // プレーンテキスト（タグなし）の後方互換処理
  const content = html.startsWith("<") ? html : html.replace(/\n/g, "<br>");
  return (
    <div
      className={cn("prose-memo text-sm text-gray-800", className)}
      dangerouslySetInnerHTML={{ __html: content }}
    />
  );
}
