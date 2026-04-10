import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { ApiError } from '@/lib/api-client';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import {
  Send,
  ThumbsUp,
  ThumbsDown,
  ChevronLeft,
  Copy,
  Check,
  RefreshCw,
  Bot,
  User,
  BookOpen,
  X,
  ExternalLink,
  PanelRightClose,
  PanelRightOpen,
  Clock,
  Hash,
  AlertCircle,
} from 'lucide-react';
import { formatDateRange, formatMessageTime, cn } from '@/lib/utils';
import { StatusBadge } from '@/components/ui/status-badge';
import { MarkdownRenderer } from '@/components/ui/markdown-renderer';
import { TypingIndicator } from '@/components/ui/typing-indicator';
import type { ReportMessage, ContentItem } from '@/types';

export default function ReportThreadPage() {
  const params = useParams();
  const threadId = params.threadId as string;
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Local state
  const [feedback, setFeedback] = useState('');
  const [pendingMessages, setPendingMessages] = useState<ReportMessage[]>([]);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedSourceMsgId, setSelectedSourceMsgId] = useState<string | null>(null);
  const [sourcePanelOpen, setSourcePanelOpen] = useState(false);
  const [assistantError, setAssistantError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Fetch thread metadata
  const { data: threadMeta, isLoading: metaLoading } = useQuery({
    queryKey: ['thread-meta', threadId],
    queryFn: () => api.reports.getThreadMeta(threadId),
  });

  // Fetch messages
  const { data: serverMessages, isLoading: messagesLoading } = useQuery({
    queryKey: ['thread-messages', threadId],
    queryFn: () => api.reports.getMessages(threadId),
  });

  // Fetch sources for the inspected message
  const { data: sourceItems, isLoading: sourcesLoading } = useQuery({
    queryKey: ['message-sources', selectedSourceMsgId],
    queryFn: async () => {
      const msg = allMessages.find((m) => m.id === selectedSourceMsgId);
      if (!msg?.metadata?.sources) return [];
      return api.content.getByIds(msg.metadata.sources);
    },
    enabled: !!selectedSourceMsgId && sourcePanelOpen,
  });

  // Combine server + pending messages
  const allMessages = useMemo(() => {
    const base = serverMessages || [];
    const pending = pendingMessages.filter(
      (pm) => !base.some((sm) => sm.id === pm.id)
    );
    return [...base, ...pending];
  }, [serverMessages, pendingMessages]);

  // Regenerate is thread-scoped; show it on the latest generated response.
  const lastGeneratedMessageId = useMemo(() => {
    for (let i = allMessages.length - 1; i >= 0; i--) {
      if (allMessages[i].role === 'agent' || allMessages[i].role === 'system') {
        return allMessages[i].id;
      }
    }
    return null;
  }, [allMessages]);

  // Clear pending messages when server data refreshes with new messages
  useEffect(() => {
    if (serverMessages && pendingMessages.length > 0) {
      setPendingMessages([]);
    }
    // Only react to serverMessages changes, not pendingMessages
  }, [serverMessages]);

  // Feedback mutation
  const feedbackMutation = useMutation({
    mutationFn: (content: string) => api.reports.sendFeedback(threadId, content),
    onMutate: () => {
      setAssistantError(null);
    },
    onSuccess: ([, agentMsg]) => {
      if (agentMsg) setPendingMessages([agentMsg]);
      setFeedback('');
      setAssistantError(null);
      queryClient.invalidateQueries({ queryKey: ['thread-messages', threadId] });
      queryClient.invalidateQueries({ queryKey: ['thread-meta', threadId] });
    },
    onError: (err) => {
      setPendingMessages([]);
      setAssistantError(chatErrorMessage(err));
      queryClient.invalidateQueries({ queryKey: ['thread-messages', threadId] });
      queryClient.invalidateQueries({ queryKey: ['thread-meta', threadId] });
    },
  });

  // Vote mutation
  const voteMutation = useMutation({
    mutationFn: ({ msgId, vote }: { msgId: string; vote: 'up' | 'down' }) =>
      api.reports.vote(msgId, vote),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['thread-messages', threadId] });
    },
  });

  // Regenerate mutation (uses thread/report ID, not message ID)
  const regenerateMutation = useMutation({
    mutationFn: () => api.reports.regenerate(threadId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['thread-messages', threadId] });
    },
    onError: (err) => {
      setAssistantError(
        err instanceof ApiError && typeof err.detail === 'string'
          ? err.detail
          : 'Report regeneration failed. The assistant could not generate a new response.',
      );
    },
  });

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [allMessages.length, feedbackMutation.isPending]);

  // Handlers
  const handleSend = useCallback(
    (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!feedback.trim() || feedbackMutation.isPending) return;

      const userMsg: ReportMessage = {
        id: `pending-${Date.now()}`,
        threadId,
        role: 'user',
        content: feedback.trim(),
        createdAt: new Date().toISOString(),
      };

      setPendingMessages([userMsg]);
      setFeedback('');
      feedbackMutation.mutate(feedback.trim());

      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    },
    [feedback, feedbackMutation, threadId]
  );

  const handleCopy = useCallback(async (content: string, msgId: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(msgId);
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      copyTimerRef.current = setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Fallback: no-op
    }
  }, []);

  const handleInspectSources = useCallback(
    (msgId: string) => {
      if (selectedSourceMsgId === msgId && sourcePanelOpen) {
        setSourcePanelOpen(false);
        setSelectedSourceMsgId(null);
      } else {
        setSelectedSourceMsgId(msgId);
        setSourcePanelOpen(true);
      }
    },
    [selectedSourceMsgId, sourcePanelOpen]
  );

  const closeSourcePanel = useCallback(() => {
    setSourcePanelOpen(false);
    setSelectedSourceMsgId(null);
  }, []);

  // Auto-resize textarea
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setFeedback(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Loading state
  if (metaLoading && messagesLoading) {
    return (
      <div className="h-[calc(100vh-160px)] flex items-center justify-center bg-white border border-slate-200 rounded-xl">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
      </div>
    );
  }

  const showTyping = feedbackMutation.isPending;

  return (
    <div className="h-[calc(100vh-160px)] flex bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      {/* Main conversation area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Thread Header */}
        <div className="border-b border-slate-200 bg-slate-50/70 px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 min-w-0">
              <button
                onClick={() => navigate(-1)}
                className="p-1.5 hover:bg-slate-200 rounded-lg text-slate-500 transition-colors mt-0.5"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <div className="min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <h2 className="text-lg font-bold text-slate-900 truncate">
                    {threadMeta?.title || 'Intelligence Thread'}
                  </h2>
                  {threadMeta?.status && <StatusBadge status={threadMeta.status} size="md" />}
                </div>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                  {threadMeta?.periodStart && threadMeta?.periodEnd && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      {formatDateRange(threadMeta.periodStart, threadMeta.periodEnd)}
                    </span>
                  )}
                  {threadMeta?.runId && (
                    <span className="flex items-center gap-1 font-mono text-slate-400">
                      <Hash className="w-3.5 h-3.5" />
                      {threadMeta.runId}
                    </span>
                  )}
                  {threadMeta?.updatedAt && (
                    <span className="text-slate-400">
                      Updated {formatMessageTime(threadMeta.updatedAt)}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={() => setSourcePanelOpen(!sourcePanelOpen)}
              className={cn(
                'p-2 rounded-lg transition-colors shrink-0',
                sourcePanelOpen
                  ? 'bg-indigo-100 text-indigo-600'
                  : 'hover:bg-slate-200 text-slate-500'
              )}
              title={sourcePanelOpen ? 'Close sources panel' : 'Open sources panel'}
            >
              {sourcePanelOpen ? (
                <PanelRightClose className="w-5 h-5" />
              ) : (
                <PanelRightOpen className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>

        {/* Message Stream */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto scroll-smooth"
        >
          <div className="max-w-3xl mx-auto py-6 px-4 sm:px-6 space-y-6">
            {/* Messages */}
            {allMessages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                copiedId={copiedId}
                isRegenerating={regenerateMutation.isPending}
                onVote={(vote) => voteMutation.mutate({ msgId: msg.id, vote })}
                onCopy={() => handleCopy(msg.content, msg.id)}
                onRegenerate={
                  (msg.role === 'agent' || msg.role === 'system') &&
                  !msg.id.startsWith('pending-') &&
                  msg.id === lastGeneratedMessageId
                    ? () => regenerateMutation.mutate()
                    : undefined
                }
                onInspectSources={() => handleInspectSources(msg.id)}
                activeSourceMsgId={selectedSourceMsgId}
              />
            ))}

            {/* Typing Indicator */}
            <AnimatePresence>
              {showTyping && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  transition={{ duration: 0.2 }}
                  className="flex items-start gap-3"
                >
                  <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-4 h-4 text-emerald-600" />
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3">
                    <TypingIndicator />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Empty state */}
            {allMessages.length === 0 && !showTyping && !messagesLoading && (
              <div className="text-center py-16">
                <div className="w-14 h-14 bg-slate-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <MessageSquare className="w-7 h-7 text-slate-400" />
                </div>
                <h3 className="text-base font-semibold text-slate-900 mb-1">No messages yet</h3>
                <p className="text-sm text-slate-500">
                  Start a conversation by sending feedback or a question below.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Composer */}
        <div className="border-t border-slate-200 bg-white px-4 sm:px-6 py-4">
          <div className="max-w-3xl mx-auto">
            <form onSubmit={handleSend} className="relative">
              <textarea
                ref={textareaRef}
                value={feedback}
                onChange={handleTextareaChange}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question, provide feedback, or request changes..."
                disabled={showTyping}
                className="w-full pl-4 pr-14 py-3.5 bg-slate-50 border border-slate-200 rounded-2xl text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 focus:bg-white disabled:opacity-50 resize-none min-h-[48px] max-h-[200px] transition-all"
                rows={1}
              />
              <button
                type="submit"
                disabled={!feedback.trim() || showTyping}
                className={cn(
                  'absolute right-2.5 bottom-2.5 p-2 rounded-xl transition-all shadow-sm',
                  feedback.trim() && !showTyping
                    ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                    : 'bg-slate-200 text-slate-400'
                )}
              >
                {showTyping ? (
                  <div className="w-5 h-5 border-2 border-slate-300 border-t-indigo-500 rounded-full animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </form>
            {assistantError && (
              <div
                role="alert"
                className="mt-3 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                <span>{assistantError}</span>
              </div>
            )}
            <p className="text-[10px] text-slate-400 mt-2 text-center font-medium">
              Shift + Enter for new line · Feedback helps improve future reports
            </p>
          </div>
        </div>
      </div>

      {/* Source Inspection Panel */}
      <AnimatePresence>
        {sourcePanelOpen && selectedSourceMsgId && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 400, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="border-l border-slate-200 bg-slate-50 overflow-hidden shrink-0"
          >
            <div className="h-full flex flex-col w-[400px]">
              {/* Panel Header */}
              <div className="px-5 py-4 border-b border-slate-200 bg-white flex items-center justify-between shrink-0">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-indigo-500" />
                    Sources
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {sourceItems?.length || 0} source{sourceItems?.length !== 1 ? 's' : ''} referenced
                  </p>
                </div>
                <button
                  onClick={closeSourcePanel}
                  className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Panel Content */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {sourcesLoading ? (
                  <div className="space-y-3">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="bg-white rounded-lg p-4 space-y-2 animate-pulse">
                        <div className="h-4 w-3/4 bg-slate-200 rounded" />
                        <div className="h-3 w-1/2 bg-slate-200 rounded" />
                        <div className="h-3 w-full bg-slate-100 rounded" />
                      </div>
                    ))}
                  </div>
                ) : sourceItems && sourceItems.length > 0 ? (
                  sourceItems.map((source) => (
                    <SourceCard key={source.id} source={source} />
                  ))
                ) : (
                  <div className="text-center py-8">
                    <BookOpen className="w-8 h-8 text-slate-300 mx-auto mb-3" />
                    <p className="text-sm text-slate-500">No sources referenced</p>
                    <p className="text-xs text-slate-400 mt-1">
                      This message doesn&apos;t cite specific sources.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function chatErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 503) {
      return typeof err.detail === 'string'
        ? err.detail
        : 'Report chat assistant is not available';
    }
    if (err.status === 504) {
      return typeof err.detail === 'string'
        ? err.detail
        : 'Report chat assistant timed out';
    }
    if (err.status === 502) {
      return typeof err.detail === 'string'
        ? err.detail
        : 'Report chat assistant returned an error';
    }
    if (typeof err.detail === 'string') {
      return err.detail;
    }
  }
  return 'The report chat assistant failed. Your message was saved.';
}

// ─────────────────────────────────────────────────────────────────
// MessageBubble Component
// ─────────────────────────────────────────────────────────────────

interface MessageBubbleProps {
  message: ReportMessage;
  copiedId: string | null;
  isRegenerating: boolean;
  onVote: (vote: 'up' | 'down') => void;
  onCopy: () => void;
  onRegenerate?: () => void;
  onInspectSources: () => void;
  activeSourceMsgId: string | null;
}

function MessageBubble({
  message,
  copiedId,
  isRegenerating,
  onVote,
  onCopy,
  onRegenerate,
  onInspectSources,
  activeSourceMsgId,
}: MessageBubbleProps) {
  const [showActions, setShowActions] = useState(false);
  const isUser = message.role === 'user';
  const isAgent = message.role === 'agent';
  const isSystem = message.role === 'system';
  const hasSources = (message.metadata?.sources?.length ?? 0) > 0;
  const isSourceActive = activeSourceMsgId === message.id;
  const isCopied = copiedId === message.id;

  const roleLabel = isSystem ? 'System Report' : isAgent ? 'Agent' : 'You';
  const roleTime = formatMessageTime(message.createdAt);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={cn('flex items-start gap-3 group', isUser && 'flex-row-reverse')}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5',
          isSystem && 'bg-indigo-100',
          isAgent && 'bg-emerald-100',
          isUser && 'bg-indigo-600'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot
            className={cn(
              'w-4 h-4',
              isSystem ? 'text-indigo-600' : 'text-emerald-600'
            )}
          />
        )}
      </div>

      {/* Message content */}
      <div className={cn('flex-1 min-w-0 max-w-[85%]', isUser && 'flex flex-col items-end')}>
        {/* Metadata */}
        <div
          className={cn(
            'flex items-center gap-2 mb-1.5 px-1',
            isUser && 'flex-row-reverse'
          )}
        >
          <span className="text-xs font-semibold text-slate-700">{roleLabel}</span>
          <span className="text-[11px] text-slate-400">{roleTime}</span>
          {isAgent && message.metadata?.model && (
            <span className="text-[10px] text-slate-400 font-mono bg-slate-100 px-1.5 py-0.5 rounded">
              {message.metadata.model}
            </span>
          )}
          {message.metadata?.regenerated && (
            <span className="text-[10px] text-amber-600 font-medium bg-amber-50 px-1.5 py-0.5 rounded flex items-center gap-0.5">
              <RefreshCw className="w-2.5 h-2.5" />
              Regenerated
            </span>
          )}
        </div>

        {/* Bubble */}
        <div
          className={cn(
            'rounded-2xl border',
            isUser && 'bg-indigo-600 text-white border-indigo-500 rounded-tr-sm',
            isSystem &&
              'bg-white border-slate-200 border-l-4 border-l-indigo-400 rounded-tl-sm',
            isAgent &&
              'bg-emerald-50/70 border-emerald-200/60 border-l-4 border-l-emerald-400 rounded-tl-sm'
          )}
        >
          {isRegenerating ? (
            <div className="p-5 flex items-center gap-3 text-slate-500">
              <div className="w-5 h-5 border-2 border-slate-300 border-t-indigo-500 rounded-full animate-spin" />
              <span className="text-sm">Regenerating response...</span>
            </div>
          ) : (
            <div className="p-5">
              <MarkdownRenderer
                content={message.content}
                variant={isUser ? 'user' : isSystem ? 'system' : 'agent'}
              />
            </div>
          )}
        </div>

        {/* Actions */}
        {!isUser && (
          <div
            className={cn(
              'flex items-center gap-1 mt-1.5 px-1 transition-opacity',
              showActions || isCopied || isSourceActive
                ? 'opacity-100'
                : 'opacity-0'
            )}
          >
            {/* Thumb up */}
            <button
              onClick={() => onVote('up')}
              className={cn(
                'p-1.5 rounded-lg transition-colors',
                message.feedback === 'up'
                  ? 'bg-blue-100 text-blue-600'
                  : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'
              )}
              title="Helpful"
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>

            {/* Thumb down */}
            <button
              onClick={() => onVote('down')}
              className={cn(
                'p-1.5 rounded-lg transition-colors',
                message.feedback === 'down'
                  ? 'bg-red-100 text-red-600'
                  : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'
              )}
              title="Not helpful"
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </button>

            {/* Copy */}
            <button
              onClick={onCopy}
              className={cn(
                'p-1.5 rounded-lg transition-colors',
                isCopied
                  ? 'bg-emerald-100 text-emerald-600'
                  : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'
              )}
              title={isCopied ? 'Copied!' : 'Copy content'}
            >
              {isCopied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>

            {/* Regenerate (latest generated report/agent response only) */}
            {onRegenerate && (
              <button
                onClick={onRegenerate}
                disabled={isRegenerating}
                className={cn(
                  'p-1.5 rounded-lg transition-colors',
                  isRegenerating
                    ? 'text-indigo-400'
                    : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'
                )}
                title="Regenerate thread response"
              >
                <RefreshCw className={cn('w-3.5 h-3.5', isRegenerating && 'animate-spin')} />
              </button>
            )}

            {/* Inspect Sources */}
            {hasSources && (
              <button
                onClick={onInspectSources}
                className={cn(
                  'p-1.5 rounded-lg transition-colors flex items-center gap-1',
                  isSourceActive
                    ? 'bg-indigo-100 text-indigo-600'
                    : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'
                )}
                title="Inspect sources"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span className="text-[10px] font-medium">
                  {message.metadata?.sources?.length}
                </span>
              </button>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────
// SourceCard Component
// ─────────────────────────────────────────────────────────────────

function SourceCard({ source }: { source: ContentItem }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className="text-sm font-semibold text-slate-900 leading-snug line-clamp-2">
          {source.title}
        </h4>
        <span className="text-[10px] font-bold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded shrink-0">
          {(source.finalScore * 100).toFixed(0)}
        </span>
      </div>
      <div className="flex items-center gap-2 text-xs text-slate-500 mb-2">
        <span className="font-medium">{source.source}</span>
        <span className="text-slate-300">·</span>
        <span>{source.type}</span>
      </div>
      <p className="text-xs text-slate-600 leading-relaxed line-clamp-3 mb-3">
        {source.snippet}
      </p>
      {source.sourceUrl && (
        <a
          href={source.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
        >
          View original
          <ExternalLink className="w-3 h-3" />
        </a>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Helper: MessageSquare icon alias for empty state
// ─────────────────────────────────────────────────────────────────
function MessageSquare(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
