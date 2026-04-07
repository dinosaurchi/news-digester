import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  variant?: 'system' | 'user' | 'agent';
}

export function MarkdownRenderer({ content, className, variant = 'system' }: MarkdownRendererProps) {
  return (
    <div
      className={cn(
        'prose prose-sm max-w-none break-words',
        variant === 'system' && 'prose-slate prose-headings:text-slate-900 prose-p:text-slate-700 prose-strong:text-slate-800 prose-li:text-slate-700',
        variant === 'agent' && 'prose-slate prose-headings:text-slate-900 prose-p:text-slate-700',
        variant === 'user' && 'prose-invert prose-headings:text-white prose-p:text-slate-100',
        className
      )}
    >
      <ReactMarkdown
        components={{
          a: ({ href, children, ...props }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:text-indigo-800 underline decoration-indigo-300 hover:decoration-indigo-500 transition-colors" {...props}>
              {children}
            </a>
          ),
          code: ({ className: codeClassName, children, ...props }) => {
            const isInline = !codeClassName;
            if (isInline) {
              return (
                <code className="bg-slate-100 text-slate-800 px-1.5 py-0.5 rounded text-[13px] font-mono" {...props}>
                  {children}
                </code>
              );
            }
            return (
              <code className={cn('block bg-slate-900 text-slate-100 p-4 rounded-lg text-[13px] font-mono overflow-x-auto', codeClassName)} {...props}>
                {children}
              </code>
            );
          },
          pre: ({ children, ...props }) => (
            <pre className="bg-slate-900 rounded-lg overflow-x-auto my-3" {...props}>
              {children}
            </pre>
          ),
          blockquote: ({ children, ...props }) => (
            <blockquote className="border-l-4 border-indigo-300 bg-indigo-50/50 pl-4 py-1 my-3 italic text-slate-600" {...props}>
              {children}
            </blockquote>
          ),
          table: ({ children, ...props }) => (
            <div className="overflow-x-auto my-3">
              <table className="min-w-full text-sm border border-slate-200" {...props}>
                {children}
              </table>
            </div>
          ),
          th: ({ children, ...props }) => (
            <th className="bg-slate-50 px-3 py-2 text-left font-semibold text-slate-700 border border-slate-200" {...props}>
              {children}
            </th>
          ),
          td: ({ children, ...props }) => (
            <td className="px-3 py-2 text-slate-600 border border-slate-200" {...props}>
              {children}
            </td>
          ),
          h1: ({ children, ...props }) => (
            <h1 className="text-xl font-bold mt-6 mb-3 text-slate-900" {...props}>{children}</h1>
          ),
          h2: ({ children, ...props }) => (
            <h2 className="text-lg font-bold mt-5 mb-2 text-slate-900" {...props}>{children}</h2>
          ),
          h3: ({ children, ...props }) => (
            <h3 className="text-base font-bold mt-4 mb-2 text-slate-800" {...props}>{children}</h3>
          ),
          hr: () => (
            <hr className="my-4 border-slate-200" />
          ),
          ul: ({ children, ...props }) => (
            <ul className="my-2 space-y-1" {...props}>{children}</ul>
          ),
          ol: ({ children, ...props }) => (
            <ol className="my-2 space-y-1" {...props}>{children}</ol>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
