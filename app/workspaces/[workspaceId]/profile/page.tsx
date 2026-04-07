'use client';

import React, { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Save, Loader2, Plus, X } from 'lucide-react';

const profileSchema = z.object({
  businessName: z.string().min(2, 'Business name is required'),
  description: z.string().min(10, 'Description is too short'),
  products: z.array(z.string()),
  competitors: z.array(z.string()),
  priorityThemes: z.array(z.string()),
  excludedTopics: z.array(z.string()),
  notes: z.string(),
});

type ProfileFormValues = z.infer<typeof profileSchema>;

export default function ProfilePage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const queryClient = useQueryClient();

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile', workspaceId],
    queryFn: () => api.profile.get(workspaceId)
  });

  const mutation = useMutation({
    mutationFn: (values: ProfileFormValues) => api.profile.update(workspaceId, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile', workspaceId] });
    }
  });

  const { register, handleSubmit, setValue, watch, reset, formState: { errors, isDirty } } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      products: [],
      competitors: [],
      priorityThemes: [],
      excludedTopics: [],
    }
  });

  useEffect(() => {
    if (profile) {
      reset({
        businessName: profile.businessName,
        description: profile.description,
        products: profile.products,
        competitors: profile.competitors,
        priorityThemes: profile.priorityThemes,
        excludedTopics: profile.excludedTopics,
        notes: profile.notes,
      });
    }
  }, [profile, reset]);

  const onSubmit = (values: ProfileFormValues) => {
    mutation.mutate(values);
  };

  const addItem = (field: keyof ProfileFormValues, value: string) => {
    if (!value) return;
    const current = watch(field) as string[];
    if (!current.includes(value)) {
      setValue(field, [...current, value], { shouldDirty: true });
    }
  };

  const removeItem = (field: keyof ProfileFormValues, index: number) => {
    const current = watch(field) as string[];
    setValue(field, current.filter((_, i) => i !== index), { shouldDirty: true });
  };

  if (isLoading) return <div className="animate-pulse space-y-6"><div className="h-10 w-48 bg-slate-200 rounded" /><div className="h-96 bg-white rounded-xl" /></div>;

  return (
    <div className="max-w-4xl space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Business Profile</h2>
          <p className="text-slate-500 mt-1">Define the context for your intelligence reports.</p>
        </div>
        <button 
          onClick={handleSubmit(onSubmit)}
          disabled={!isDirty || mutation.isPending}
          className="flex items-center gap-2 px-6 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg font-medium transition-all shadow-sm"
        >
          {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save Changes
        </button>
      </div>

      <form className="space-y-8 bg-white border border-slate-200 rounded-xl p-8 shadow-sm">
        <div className="grid grid-cols-1 gap-6">
          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-700">Business Name</label>
            <input 
              {...register('businessName')}
              className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
              placeholder="e.g. TechCorp Inc."
            />
            {errors.businessName && <p className="text-xs text-red-500">{errors.businessName.message}</p>}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-700">Description</label>
            <textarea 
              {...register('description')}
              rows={3}
              className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all resize-none"
              placeholder="What does this business do?"
            />
            {errors.description && <p className="text-xs text-red-500">{errors.description.message}</p>}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <ListInput 
              label="Products & Services" 
              items={watch('products')} 
              onAdd={(v) => addItem('products', v)} 
              onRemove={(i) => removeItem('products', i)} 
            />
            <ListInput 
              label="Competitors" 
              items={watch('competitors')} 
              onAdd={(v) => addItem('competitors', v)} 
              onRemove={(i) => removeItem('competitors', i)} 
            />
            <ListInput 
              label="Priority Themes" 
              items={watch('priorityThemes')} 
              onAdd={(v) => addItem('priorityThemes', v)} 
              onRemove={(i) => removeItem('priorityThemes', i)} 
            />
            <ListInput 
              label="Excluded Topics" 
              items={watch('excludedTopics')} 
              onAdd={(v) => addItem('excludedTopics', v)} 
              onRemove={(i) => removeItem('excludedTopics', i)} 
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-700">Additional Notes</label>
            <textarea 
              {...register('notes')}
              rows={4}
              className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all resize-none"
              placeholder="Any other specific instructions for the AI agent..."
            />
          </div>
        </div>
      </form>
    </div>
  );
}

function ListInput({ label, items, onAdd, onRemove }: { label: string, items: string[], onAdd: (v: string) => void, onRemove: (i: number) => void }) {
  const [val, setVal] = useState('');

  return (
    <div className="space-y-3">
      <label className="text-sm font-semibold text-slate-700">{label}</label>
      <div className="flex gap-2">
        <input 
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); onAdd(val); setVal(''); } }}
          className="flex-1 px-3 py-1.5 border border-slate-200 rounded-lg text-sm focus:border-indigo-500 outline-none"
          placeholder="Add item..."
        />
        <button 
          type="button"
          onClick={() => { onAdd(val); setVal(''); }}
          className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {items.map((item, i) => (
          <span key={i} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-md text-xs font-medium border border-indigo-100">
            {item}
            <button type="button" onClick={() => onRemove(i)} className="hover:text-indigo-900">
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}
