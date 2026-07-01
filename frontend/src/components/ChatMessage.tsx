'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Database, Download, AlertCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message } from '@/types';
import { ChartRenderer } from './ChartRenderer';
import { ExportMenu } from './ExportMenu';
import { clsx } from 'clsx';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const [sqlExpanded, setSqlExpanded] = useState(false);
  const isUser = message.role === 'user';

  return (
    <div
      className={clsx(
        'animate-fade-in-up',
        isUser ? 'flex justify-end' : 'flex justify-start'
      )}
    >
      <div
        className={clsx(
          'max-w-[85%] rounded-2xl px-4 py-3',
          isUser
            ? 'bg-user-bubble dark:bg-user-bubble-dark text-gray-900 dark:text-gray-100'
            : 'bg-assistant-bubble dark:bg-assistant-bubble-dark',
          message.isError && 'border border-red-200 dark:border-red-800'
        )}
      >
        {/* Error icon */}
        {message.isError && (
          <div className="flex items-center gap-2 mb-2 text-red-500 dark:text-red-400">
            <AlertCircle className="w-4 h-4" />
            <span className="text-xs font-medium">Error</span>
          </div>
        )}

        {/* Message content */}
        <div className="prose prose-sm dark:prose-invert max-w-none break-words">
          {isUser ? (
            <p className="m-0 whitespace-pre-wrap">{message.content}</p>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                table: ({ children }) => (
                  <div className="overflow-x-auto my-3 rounded-lg border border-gray-200 dark:border-gray-700">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children }) => (
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    {children}
                  </thead>
                ),
                th: ({ children }) => (
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                    {children}
                  </td>
                ),
                tr: ({ children }) => (
                  <tr className="border-b border-gray-100 dark:border-gray-700 even:bg-gray-50 dark:even:bg-gray-800/50">
                    {children}
                  </tr>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* SQL Accordion */}
        {message.sql && (
          <div className="mt-3 border-t border-gray-200 dark:border-gray-700 pt-2">
            <button
              onClick={() => setSqlExpanded(!sqlExpanded)}
              className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
              aria-expanded={sqlExpanded}
            >
              {sqlExpanded ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5" />
              )}
              <Database className="w-3.5 h-3.5" />
              <span>View SQL Query</span>
            </button>
            {sqlExpanded && (
              <pre className="mt-2 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs overflow-x-auto">
                <code>{message.sql}</code>
              </pre>
            )}
          </div>
        )}

        {/* Chart */}
        {message.rawData && message.suggestedChartType && message.chartConfig && (
          <div className="mt-3">
            <ChartRenderer
              rawData={message.rawData}
              suggestedChartType={message.suggestedChartType}
              chartConfig={message.chartConfig}
            />
          </div>
        )}

        {/* Export + metadata */}
        {!isUser && !message.isError && (
          <div className="mt-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {message.domain && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
                  {message.domain}
                </span>
              )}
              {message.rowCount != null && message.rowCount > 0 && (
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {message.rowCount} row{message.rowCount !== 1 ? 's' : ''}
                </span>
              )}
            </div>
            <ExportMenu message={message} />
          </div>
        )}
      </div>
    </div>
  );
}
