import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Components } from "react-markdown";

interface MarkdownContentProps {
  content: string;
}

// Custom renderers for a professional developer-tool aesthetic
const components: Components = {
  // Headings
  h1: ({ children }) => (
    <h1 className="text-lg font-bold text-gray-900 mt-4 mb-2 first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-base font-semibold text-gray-900 mt-4 mb-2 first:mt-0">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-semibold text-gray-800 mt-3 mb-1.5 first:mt-0">
      {children}
    </h3>
  ),
  // Paragraphs
  p: ({ children }) => (
    <p className="text-sm text-gray-700 leading-relaxed mb-3 last:mb-0">
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
    <li className="text-sm text-gray-700 leading-relaxed">{children}</li>
  ),
  // Inline code
  code: ({ className, children, ...props }) => {
    const isBlock = className?.includes("language-");
    if (isBlock) {
      // Block code — rehype-highlight will add syntax classes
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
        className="inline rounded bg-gray-100 px-1.5 py-0.5 text-xs font-mono text-gray-800 border border-gray-200"
        {...props}
      >
        {children}
      </code>
    );
  },
  // Code blocks (pre wrapper)
  pre: ({ children }) => (
    <pre className="overflow-x-auto rounded-md bg-gray-900 p-4 mb-3 last:mb-0 text-gray-100 text-xs leading-relaxed">
      {children}
    </pre>
  ),
  // Strong / bold
  strong: ({ children }) => (
    <strong className="font-semibold text-gray-900">{children}</strong>
  ),
  // Blockquote
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-gray-300 pl-3 my-2 italic text-gray-600 text-sm">
      {children}
    </blockquote>
  ),
  // Links
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-600 hover:text-blue-800 underline underline-offset-2"
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
    <th className="border border-gray-200 bg-gray-50 px-3 py-2 text-left font-semibold text-gray-700">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border border-gray-200 px-3 py-2 text-gray-700">
      {children}
    </td>
  ),
  // Horizontal rule
  hr: () => <hr className="my-4 border-gray-200" />,
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
