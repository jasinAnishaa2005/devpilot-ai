import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Components } from "react-markdown";

interface MarkdownContentProps {
  content: string;
}

// Custom renderers — wine-palette developer-tool aesthetic
const components: Components = {
  // Headings
  h1: ({ children }) => (
    <h1 className="text-lg font-bold text-[#241A1D] mt-4 mb-2 first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-base font-semibold text-[#241A1D] mt-4 mb-2 first:mt-0">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-semibold text-[#3A0714] mt-3 mb-1.5 first:mt-0">
      {children}
    </h3>
  ),
  // Paragraphs
  p: ({ children }) => (
    <p className="text-sm text-[#4A3036] leading-relaxed mb-3 last:mb-0">
      {children}
    </p>
  ),
  // Lists
  ul: ({ children }) => (
    <ul className="list-disc list-outside pl-4 mb-3 space-y-1 last:mb-0">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-outside pl-4 mb-3 space-y-1 last:mb-0">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="text-sm text-[#4A3036] leading-relaxed">{children}</li>
  ),
  // Inline code
  code: ({ className, children, ...props }) => {
    const isBlock = className?.includes("language-");
    if (isBlock) {
      return (
        <code
          className={[
            "block text-xs font-mono leading-relaxed",
            className,
          ].join(" ")}
          {...props}
        >
          {children}
        </code>
      );
    }
    // Inline code
    return (
      <code
        className="inline rounded bg-[#F7F2EF] px-1.5 py-0.5 text-xs font-mono text-[#3A0714] border border-[#E2DEDC]"
        {...props}
      >
        {children}
      </code>
    );
  },
  // Code blocks (pre wrapper)
  pre: ({ children }) => (
    <pre className="overflow-x-auto rounded-md bg-[#2A0710] p-4 mb-3 last:mb-0 text-[#F7F2EF] text-xs leading-relaxed border border-[#520B1B]/60">
      {children}
    </pre>
  ),
  // Strong / bold
  strong: ({ children }) => (
    <strong className="font-semibold text-[#241A1D]">{children}</strong>
  ),
  // Blockquote
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-[#B85C6E]/50 pl-3 my-2 italic text-[#766A6D] text-sm bg-[#F7F2EF] py-2 pr-2 rounded-r-md">
      {children}
    </blockquote>
  ),
  // Links
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-[#7A1830] hover:text-[#3A0714] underline underline-offset-2 transition-colors"
    >
      {children}
    </a>
  ),
  // Table
  table: ({ children }) => (
    <div className="overflow-x-auto mb-3 last:mb-0">
      <table className="w-full text-xs border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-[#E2DEDC] bg-[#3A0714] px-3 py-2 text-left font-semibold text-white">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border border-[#E2DEDC] px-3 py-2 text-[#241A1D] odd:bg-white even:bg-[#F7F2EF]">
      {children}
    </td>
  ),
  // Horizontal rule
  hr: () => <hr className="my-4 border-[#E2DEDC]" />,
};

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div className="min-w-0">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
