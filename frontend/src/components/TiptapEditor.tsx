"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Highlight from "@tiptap/extension-highlight";
import Underline from "@tiptap/extension-underline";

interface TiptapEditorProps {
  content: string;
  onChange: (content: string) => void;
  placeholder?: string;
}

export default function TiptapEditor({
  content,
  onChange,
  placeholder = "在此粘贴或输入课文内容...",
}: TiptapEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder }),
      Highlight,
      Underline,
    ],
    content,
    onUpdate: ({ editor }) => {
      onChange(editor.getText());
    },
    editorProps: {
      attributes: {
        class:
          "prose prose-sm sm:prose-base max-w-none focus:outline-none min-h-[200px] px-4 py-3",
      },
    },
  });

  return (
    <div className="border border-gray-300 rounded-lg bg-white overflow-hidden">
      {editor && (
        <div className="flex items-center gap-1 px-3 py-2 border-b border-gray-200 bg-gray-50">
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleBold().run()}
            active={editor.isActive("bold")}
            title="粗体"
          >
            B
          </ToolbarBtn>
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleItalic().run()}
            active={editor.isActive("italic")}
            title="斜体"
          >
            <em>I</em>
          </ToolbarBtn>
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleUnderline().run()}
            active={editor.isActive("underline")}
            title="下划线"
          >
            <u>U</u>
          </ToolbarBtn>
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleHighlight().run()}
            active={editor.isActive("highlight")}
            title="高亮"
          >
            <span className="bg-yellow-200 px-1">H</span>
          </ToolbarBtn>
          <div className="w-px h-5 bg-gray-300 mx-1" />
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            active={editor.isActive("heading", { level: 2 })}
            title="标题"
          >
            H2
          </ToolbarBtn>
          <ToolbarBtn
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            active={editor.isActive("bulletList")}
            title="列表"
          >
            •
          </ToolbarBtn>
          <div className="ml-auto text-xs text-gray-400">
            {(() => {
              const t = editor.getText().trim();
              if (!t) return 0;
              const en = t.split(/\s+/).filter(Boolean).length;
              const zh = (t.match(/[一-鿿]/g) || []).length;
              return en + Math.ceil(zh * 0.67);
            })()} 词
          </div>
        </div>
      )}
      <EditorContent editor={editor} />
    </div>
  );
}

function ToolbarBtn({
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
      onClick={onClick}
      title={title}
      className={`px-2 py-1 text-sm rounded font-medium transition-colors ${
        active
          ? "bg-primary text-white"
          : "text-gray-600 hover:bg-gray-200"
      }`}
    >
      {children}
    </button>
  );
}
