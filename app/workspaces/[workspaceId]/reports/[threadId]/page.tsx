'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams, useRouter } from 'next/navigation';
import { 
  Send, 
  ThumbsUp, 
  ThumbsDown, 
  ChevronLeft, 
  MoreVertical, 
  Copy, 
  RefreshCw, 
  ExternalLink,
  Bot,
  User,
  Info
} from 'lucide-react';
import { formatDate, cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';
import { useState, useRef, useEffect } from 'react';

export default function ReportThreadPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const threadId = params.threadId as string;
  const queryClient = useQueryClient();
  const router = useRouter();
  
  const [feedback, setFeedback] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: messages, isLoading } = useQuery({
    queryKey: ['thread', threadId],
    queryFn: () => api.reports.getThread(threadId)
  });

  const feedbackMutation = useMutation({
    mutationFn: (content: string) => api.reports.sendFeedback(threadId, content),
    onSuccess: () => {
      setFeedback('');
      queryClient.invalidateQueries({ queryKey: ['thread', threadId] });
    }
  });

  const voteMutation = useMutation({
    mutationFn: ({ msgId, vote }: { msgId: string, vote: 'up' | 'down' }) => api.reports.vote(msgId, vote),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['thread', threadId] });
    }
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSendFeedback = (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedback.trim() || feedbackMutation.isPending) return;
    feedbackMutation.mutate(feedback);
  };

  if (isLoading) return <div className="h-[calc(100vh-160px)] flex items-center justify-center"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600" /></div>;

  return (
    <div className="h-[calc(100vh-160px)] flex flex-col bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      {/* Thread Header */}
      <div className="h-14 border-b border-slate-200 px-6 flex items-center justify-between bg-slate-50/50">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.back()}
            className="p-1.5 hover:bg-slate-200 rounded-md text-slate-600 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <h3 className="font-bold text-slate-900">Intelligence Thread</h3>
          <span className="text-xs text-slate-400 font-mono">#{threadId}</span>
        </div>
        <div className="flex items-center gap-2">
          <button className="p-2 hover:bg-slate-200 rounded-md text-slate-600 transition-colors">
            <Copy className="w-4 h-4" />
          </button>
          <button className="p-2 hover:bg-slate-200 rounded-md text-slate-600 transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button className="p-2 hover:bg-slate-200 rounded-md text-slate-600 transition-colors">
            <MoreVertical className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-6 space-y-8 scroll-smooth"
      >
        {messages?.map((msg) => (
          <div 
            key={msg.id} 
            className={cn(
              "flex gap-4 max-w-4xl",
              msg.role === 'user' ? "ml-auto flex-row-reverse" : ""
            )}
          >
            <div className={cn(
              "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-sm",
              msg.role === 'system' ? "bg-indigo-600 text-white" : 
              msg.role === 'agent' ? "bg-emerald-600 text-white" : 
              "bg-slate-700 text-white"
            )}>
              {msg.role === 'system' ? <Bot className="w-6 h-6" /> : 
               msg.role === 'agent' ? <Bot className="w-6 h-6" /> : 
               <User className="w-6 h-6" />}
            </div>

            <div className={cn(
              "space-y-2",
              msg.role === 'user' ? "items-end" : "items-start"
            )}>
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  {msg.role === 'system' ? 'Intelligence Agent' : 
                   msg.role === 'agent' ? 'Intelligence Agent' : 
                   'Admin'}
                </span>
                <span className="text-[10px] text-slate-400 font-medium">
                  {formatDate(msg.createdAt)}
                </span>
              </div>

              <div className={cn(
                "p-5 rounded-2xl shadow-sm border",
                msg.role === 'user' ? "bg-indigo-600 text-white border-indigo-500 rounded-tr-none" : 
                "bg-white border-slate-200 text-slate-800 rounded-tl-none"
              )}>
                <div className={cn(
                  "prose prose-sm max-w-none",
                  msg.role === 'user' ? "prose-invert" : "prose-slate"
                )}>
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              </div>

              {msg.role !== 'user' && (
                <div className="flex items-center gap-4 mt-2">
                  <div className="flex items-center gap-1">
                    <button 
                      onClick={() => voteMutation.mutate({ msgId: msg.id, vote: 'up' })}
                      className={cn(
                        "p-1.5 rounded-md transition-colors",
                        msg.feedback === 'up' ? "bg-emerald-100 text-emerald-600" : "hover:bg-slate-100 text-slate-400"
                      )}
                    >
                      <ThumbsUp className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => voteMutation.mutate({ msgId: msg.id, vote: 'down' })}
                      className={cn(
                        "p-1.5 rounded-md transition-colors",
                        msg.feedback === 'down' ? "bg-red-100 text-red-600" : "hover:bg-slate-100 text-slate-400"
                      )}
                    >
                      <ThumbsDown className="w-4 h-4" />
                    </button>
                  </div>
                  {msg.metadata?.sources && (
                    <button className="flex items-center gap-1.5 text-[10px] font-bold text-indigo-600 uppercase tracking-wider hover:underline">
                      <Info className="w-3 h-3" />
                      View {msg.metadata.sources.length} Sources
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {feedbackMutation.isPending && (
          <div className="flex gap-4 max-w-4xl ml-auto flex-row-reverse">
            <div className="w-10 h-10 rounded-xl bg-slate-700 text-white flex items-center justify-center shrink-0 shadow-sm">
              <User className="w-6 h-6" />
            </div>
            <div className="bg-slate-100 p-4 rounded-2xl rounded-tr-none animate-pulse">
              <div className="h-4 w-32 bg-slate-200 rounded" />
            </div>
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="p-6 border-t border-slate-200 bg-slate-50/50">
        <form onSubmit={handleSendFeedback} className="relative">
          <textarea 
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendFeedback(e);
              }
            }}
            placeholder="Provide feedback or ask for adjustments..."
            className="w-full pl-4 pr-14 py-4 bg-white border border-slate-200 rounded-2xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 shadow-sm resize-none min-h-[60px] max-h-[200px]"
            rows={1}
          />
          <button 
            type="submit"
            disabled={!feedback.trim() || feedbackMutation.isPending}
            className="absolute right-3 bottom-3 p-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:bg-slate-300 transition-all shadow-sm"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
        <p className="text-[10px] text-slate-400 mt-2 text-center font-medium">
          Shift + Enter for new line. Feedback will be used to tune future reports.
        </p>
      </div>
    </div>
  );
}
