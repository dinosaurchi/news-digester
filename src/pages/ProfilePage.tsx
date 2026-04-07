import { useEffect, useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams, useBlocker } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { profileSchema, type ProfileFormValues } from '@/lib/schemas/profile';
import { PageHeader } from '@/components/ui/page-header';
import { ListEditor } from '@/components/ui/list-editor';
import { Skeleton } from '@/components/ui/loading-skeleton';
import { toast } from '@/components/ui/toast';
import { Save, Loader2, AlertTriangle } from 'lucide-react';

export default function ProfilePage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const queryClient = useQueryClient();
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false);

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile', workspaceId],
    queryFn: () => api.profile.get(workspaceId),
  });

  const mutation = useMutation({
    mutationFn: (values: ProfileFormValues) => api.profile.update(workspaceId, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile', workspaceId] });
      toast.success('Profile saved successfully!');
    },
    onError: () => {
      toast.error('Failed to save profile. Please try again.');
    },
  });

  const { register, handleSubmit, setValue, watch, reset, formState: { errors, isDirty } } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema) as any,
    defaultValues: {
      businessName: '',
      description: '',
      products: [],
      competitors: [],
      priorityThemes: [],
      excludedTopics: [],
      notes: '',
    },
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

  // Block navigation when form is dirty
  const blocker = useBlocker(
    useCallback(() => isDirty, [isDirty])
  );

  const handleBlockerProceed = () => {
    if (blocker.location) {
      setShowUnsavedDialog(false);
      blocker.proceed?.();
    }
  };

  const handleBlockerAbort = () => {
    setShowUnsavedDialog(false);
    blocker.reset?.();
  };

  // Sync blocker dialog state
  useEffect(() => {
    if (blocker.state === 'blocked') {
      setShowUnsavedDialog(true);
    }
  }, [blocker.state]);

  const onSubmit = (values: ProfileFormValues) => {
    mutation.mutate(values);
  };

  const inputClass = (hasError: boolean) =>
    `w-full px-4 py-2.5 border rounded-lg outline-none transition-all text-sm ${
      hasError
        ? 'border-red-300 focus:ring-2 focus:ring-red-500/10 focus:border-red-500'
        : 'border-slate-200 focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500'
    }`;

  if (isLoading) {
    return (
      <div className="max-w-4xl space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-72" />
        <div className="bg-white border border-slate-200 rounded-xl p-8 space-y-6">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-24 w-full" />
          <div className="grid grid-cols-2 gap-6">
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </div>
          <Skeleton className="h-20 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-8">
      <PageHeader
        title="Business Profile"
        description="Define the context for your intelligence reports."
        actions={
          <button
            onClick={handleSubmit(onSubmit as any)}
            disabled={!isDirty || mutation.isPending}
            className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg font-medium transition-all shadow-sm disabled:cursor-not-allowed"
          >
            {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save Changes
          </button>
        }
      />

      <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-6">
        {/* Business Identity */}
        <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
          <div>
            <h3 className="text-base font-bold text-slate-900">Business Identity</h3>
            <p className="text-sm text-slate-500 mt-0.5">Basic information about your business.</p>
          </div>
          <div className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700">Business Name</label>
              <input
                {...register('businessName')}
                placeholder="e.g. TechCorp Inc."
                className={inputClass(!!errors.businessName)}
              />
              {errors.businessName && <p className="text-xs text-red-500 font-medium">{errors.businessName.message}</p>}
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700">Business Description</label>
              <textarea
                {...register('description')}
                rows={3}
                placeholder="Describe what your business does, your industry, target market, and key differentiators..."
                className={`${inputClass(!!errors.description)} resize-none`}
              />
              {errors.description && <p className="text-xs text-red-500 font-medium">{errors.description.message}</p>}
            </div>
          </div>
        </section>

        {/* Products / Services & Competitors */}
        <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
          <div>
            <h3 className="text-base font-bold text-slate-900">Products & Competitors</h3>
            <p className="text-sm text-slate-500 mt-0.5">Define your key offerings and competitive landscape.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            <ListEditor
              label="Products & Services"
              description="Your main products, services, or offerings."
              items={watch('products') || []}
              onChange={(items) => setValue('products', items, { shouldDirty: true })}
              placeholder="e.g. CloudStack Pro"
            />
            <ListEditor
              label="Competitors"
              description="Companies you want to monitor competitively."
              items={watch('competitors') || []}
              onChange={(items) => setValue('competitors', items, { shouldDirty: true })}
              placeholder="e.g. CloudGiant"
            />
          </div>
        </section>

        {/* Themes & Topics */}
        <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
          <div>
            <h3 className="text-base font-bold text-slate-900">Themes & Topics</h3>
            <p className="text-sm text-slate-500 mt-0.5">Control what the AI focuses on and filters out.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            <ListEditor
              label="Priority Themes / Topics"
              description="Topics the AI should prioritize in intelligence gathering."
              items={watch('priorityThemes') || []}
              onChange={(items) => setValue('priorityThemes', items, { shouldDirty: true })}
              placeholder="e.g. Generative AI"
            />
            <ListEditor
              label="Excluded Topics"
              description="Topics to filter out from intelligence reports."
              items={watch('excludedTopics') || []}
              onChange={(items) => setValue('excludedTopics', items, { shouldDirty: true })}
              placeholder="e.g. Consumer hardware"
            />
          </div>
        </section>

        {/* Notes */}
        <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
          <div>
            <h3 className="text-base font-bold text-slate-900">Additional Notes</h3>
            <p className="text-sm text-slate-500 mt-0.5">Notes for report relevance and special instructions for the AI agent.</p>
          </div>
          <div className="pt-2">
            <textarea
              {...register('notes')}
              rows={4}
              placeholder="Any specific instructions for the AI agent, e.g., focus on enterprise trends, regulatory changes in specific regions..."
              className={`${inputClass(!!errors.notes)} resize-none`}
            />
            {errors.notes && <p className="text-xs text-red-500 font-medium">{errors.notes.message}</p>}
          </div>
        </section>

        {/* Sticky Save Footer */}
        {isDirty && (
          <div className="sticky bottom-0 -mx-6 -mb-8 px-6 pb-6 pt-4 bg-gradient-to-t from-slate-50 via-slate-50 to-transparent">
            <div className="flex items-center justify-between p-4 bg-white border border-slate-200 rounded-xl shadow-lg">
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                You have unsaved changes
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    if (profile) reset({
                      businessName: profile.businessName,
                      description: profile.description,
                      products: profile.products,
                      competitors: profile.competitors,
                      priorityThemes: profile.priorityThemes,
                      excludedTopics: profile.excludedTopics,
                      notes: profile.notes,
                    });
                  }}
                  className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Discard
                </button>
                <button
                  type="submit"
                  disabled={mutation.isPending}
                  className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg font-medium transition-all shadow-sm"
                >
                  {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        )}
      </form>

      {/* Unsaved Changes Dialog */}
      {showUnsavedDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={handleBlockerAbort} />
          <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center gap-3 text-amber-600">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-slate-900">Unsaved Changes</h3>
            </div>
            <p className="text-sm text-slate-600">
              You have unsaved changes to your business profile. If you leave, your changes will be lost.
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={handleBlockerAbort}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Stay Here
              </button>
              <button
                onClick={handleBlockerProceed}
                className="px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                Leave Without Saving
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
