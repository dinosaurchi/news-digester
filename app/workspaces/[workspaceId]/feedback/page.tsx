'use client';

import { ThumbsUp, ThumbsDown, MessageSquare, TrendingUp, TrendingDown, Target, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function FeedbackPage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Feedback & Preferences</h2>
          <p className="text-slate-500 mt-1">Analyze captured feedback and how it influences intelligence tuning.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-medium text-slate-500">Positive Feedback</p>
            <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
              <ThumbsUp className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-bold text-slate-900">84%</p>
          <div className="mt-2 flex items-center gap-1 text-xs text-emerald-600 font-medium">
            <TrendingUp className="w-3 h-3" />
            +12% from last month
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-medium text-slate-500">Negative Feedback</p>
            <div className="p-2 bg-red-50 text-red-600 rounded-lg">
              <ThumbsDown className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-bold text-slate-900">16%</p>
          <div className="mt-2 flex items-center gap-1 text-xs text-red-600 font-medium">
            <TrendingDown className="w-3 h-3" />
            -4% from last month
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-medium text-slate-500">Tuning Events</p>
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <Target className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-bold text-slate-900">42</p>
          <p className="mt-2 text-xs text-slate-500 font-medium">Preference adjustments made</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
          <h3 className="text-lg font-bold text-slate-900">Topic Preferences</h3>
          <div className="space-y-4">
            <PreferenceItem label="Generative AI" score={95} status="boosted" />
            <PreferenceItem label="EU Regulations" score={88} status="boosted" />
            <PreferenceItem label="Cloud Infrastructure" score={72} status="neutral" />
            <PreferenceItem label="Consumer Hardware" score={15} status="suppressed" />
            <PreferenceItem label="Cryptocurrency" score={5} status="suppressed" />
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
          <h3 className="text-lg font-bold text-slate-900">Recent Feedback Events</h3>
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="flex gap-4 p-4 bg-slate-50 rounded-lg border border-slate-100">
                <div className="w-8 h-8 bg-white border border-slate-200 rounded flex items-center justify-center shrink-0">
                  <MessageSquare className="w-4 h-4 text-slate-400" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-slate-800 font-medium">&quot;Focus more on the competitive landscape for CloudStack.&quot;</p>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">March 18, 2024 • Intelligence Report #121</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function PreferenceItem({ label, score, status }: { label: string, score: number, status: 'boosted' | 'suppressed' | 'neutral' }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        <span className={cn(
          "text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded",
          status === 'boosted' ? "bg-emerald-50 text-emerald-700" : 
          status === 'suppressed' ? "bg-red-50 text-red-700" : 
          "bg-slate-100 text-slate-600"
        )}>
          {status}
        </span>
      </div>
      <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
        <div 
          className={cn(
            "h-full transition-all duration-500",
            status === 'boosted' ? "bg-emerald-500" : 
            status === 'suppressed' ? "bg-red-500" : 
            "bg-slate-400"
          )} 
          style={{ width: `${score}%` }} 
        />
      </div>
    </div>
  );
}
