import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useParams, useBlocker } from 'react-router-dom';
import { useForm, Controller, type Resolver } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { settingsSchema, type SettingsFormValues } from '@/lib/schemas/settings';
import { PageHeader } from '@/components/ui/page-header';
import { ListEditor } from '@/components/ui/list-editor';
import { Skeleton } from '@/components/ui/loading-skeleton';
import { toast } from '@/components/ui/toast';
import {
  Save,
  Clock,
  FileText,
  Database,
  Mail,
  Archive,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';

const TIMEZONES = [
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)' },
  { value: 'America/New_York', label: 'EST (Eastern Standard Time)' },
  { value: 'America/Chicago', label: 'CST (Central Standard Time)' },
  { value: 'America/Denver', label: 'MST (Mountain Standard Time)' },
  { value: 'America/Los_Angeles', label: 'PST (Pacific Standard Time)' },
  { value: 'Europe/London', label: 'GMT (Greenwich Mean Time)' },
  { value: 'Europe/Berlin', label: 'CET (Central European Time)' },
  { value: 'Europe/Paris', label: 'CET (Paris)' },
  { value: 'Asia/Tokyo', label: 'JST (Japan Standard Time)' },
  { value: 'Asia/Shanghai', label: 'CST (China Standard Time)' },
  { value: 'Asia/Kolkata', label: 'IST (India Standard Time)' },
  { value: 'Australia/Sydney', label: 'AEST (Australian Eastern)' },
];

const TIME_OPTIONS = Array.from({ length: 24 }, (_, i) => {
  const h = i.toString().padStart(2, '0');
  return { value: `${h}:00`, label: `${h}:00` };
});

export default function SettingsPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const queryClient = useQueryClient();
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false);

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings', workspaceId],
    queryFn: () => api.settings.get(workspaceId),
  });

  const mutation = useMutation({
    mutationFn: (values: SettingsFormValues) => api.settings.update(workspaceId, values as unknown as Parameters<typeof api.settings.update>[1]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', workspaceId] });
      toast.success('Settings saved successfully!');
    },
    onError: () => {
      toast.error('Failed to save settings. Please try again.');
    },
  });

  const { register, handleSubmit, control, reset, watch, setValue, formState: { errors, isDirty } } = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsSchema) as Resolver<SettingsFormValues>,
    defaultValues: {
      schedule: { enabled: false, frequency: 'daily', timeOfDay: '08:00', timezone: 'UTC' },
      reportStyle: 'detailed',
      thresholds: { minRelevanceScore: 65, minFinalScore: 70, maxArticlesPerReport: 15 },
      retention: { contentDays: 90, reportDays: 365, runHistoryDays: 180 },
      emailDelivery: { enabled: false, recipients: [], subjectPrefix: '' },
    },
  });

  useEffect(() => {
    if (settings) {
      reset({
        schedule: settings.schedule,
        reportStyle: settings.reportStyle,
        thresholds: {
          minRelevanceScore: Math.round(settings.thresholds.minRelevanceScore * 100),
          minFinalScore: Math.round(settings.thresholds.minFinalScore * 100),
          maxArticlesPerReport: settings.thresholds.maxArticlesPerReport,
        },
        retention: settings.retention,
        emailDelivery: settings.emailDelivery,
      });
    }
  }, [settings, reset]);

  // Block navigation when form is dirty
  const blocker = useBlocker(
    useCallback(() => isDirty, [isDirty])
  );

  useEffect(() => {
    if (blocker.state === 'blocked') {
      setShowUnsavedDialog(true);
    }
  }, [blocker.state]);

  const handleBlockerProceed = () => {
    setShowUnsavedDialog(false);
    blocker.proceed?.();
  };

  const handleBlockerAbort = () => {
    setShowUnsavedDialog(false);
    blocker.reset?.();
  };

  const onSubmit = (values: SettingsFormValues) => {
    // Convert percentage scores back to 0-1 range
    const payload = {
      ...values,
      thresholds: {
        ...values.thresholds,
        minRelevanceScore: values.thresholds.minRelevanceScore / 100,
        minFinalScore: values.thresholds.minFinalScore / 100,
      },
    };
    mutation.mutate(payload);
  };

  const inputClass = (hasError: boolean) =>
    `w-full px-4 py-2.5 border rounded-lg outline-none transition-all text-sm ${
      hasError
        ? 'border-red-300 focus:ring-2 focus:ring-red-500/10'
        : 'border-slate-200 focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500'
    }`;

  if (isLoading) {
    return (
      <div className="max-w-4xl space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-72" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-48 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-8">
      <PageHeader
        title="Workspace Settings"
        description="Configure operational parameters and system behavior."
        actions={
          <button
            onClick={handleSubmit(onSubmit as (data: SettingsFormValues) => void)}
            disabled={!isDirty || mutation.isPending}
            className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg font-medium transition-all shadow-sm disabled:cursor-not-allowed"
          >
            {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save Settings
          </button>
        }
      />

      <form onSubmit={handleSubmit(onSubmit as (data: SettingsFormValues) => void)} className="space-y-6">
        {/* Section 1: Schedule Configuration */}
        <SettingsSection
          title="Schedule Configuration"
          description="Control when the intelligence cycle runs automatically."
          icon={Clock}
        >
          <div className="space-y-5">
            {/* Enable/Disable */}
            <Controller
              name="schedule.enabled"
              control={control}
              render={({ field }) => (
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-700">Enable Scheduled Runs</p>
                    <p className="text-xs text-slate-500">Automatically fetch feeds and generate reports on a schedule.</p>
                  </div>
                  <ToggleSwitch checked={field.value} onChange={field.onChange} />
                </div>
              )}
            />

            {watch('schedule.enabled') && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 border-t border-slate-100">
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700">Frequency</label>
                  <select
                    {...register('schedule.frequency')}
                    className={cn(inputClass(!!errors.schedule?.frequency), 'bg-white')}
                  >
                    <option value="daily">Daily</option>
                    <option value="twice_daily">Twice Daily</option>
                    <option value="weekly">Weekly</option>
                  </select>
                  {errors.schedule?.frequency && (
                    <p className="text-xs text-red-500 font-medium">{errors.schedule.frequency.message}</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700">Time of Day</label>
                  <select
                    {...register('schedule.timeOfDay')}
                    className={cn(inputClass(!!errors.schedule?.timeOfDay), 'bg-white')}
                  >
                    {TIME_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  {errors.schedule?.timeOfDay && (
                    <p className="text-xs text-red-500 font-medium">{errors.schedule.timeOfDay.message}</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700">Timezone</label>
                  <select
                    {...register('schedule.timezone')}
                    className={cn(inputClass(!!errors.schedule?.timezone), 'bg-white')}
                  >
                    {TIMEZONES.map((tz) => (
                      <option key={tz.value} value={tz.value}>{tz.label}</option>
                    ))}
                  </select>
                  {errors.schedule?.timezone && (
                    <p className="text-xs text-red-500 font-medium">{errors.schedule.timezone.message}</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </SettingsSection>

        {/* Section 2: Report Generation */}
        <SettingsSection
          title="Report Generation"
          description="Configure how reports are drafted and scored."
          icon={FileText}
        >
          <div className="space-y-6">
            {/* Report Style */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-700">Report Style</p>
                <p className="text-xs text-slate-500">The verbosity and format of the generated intelligence.</p>
              </div>
              <div className="flex items-center gap-2">
                {(['concise', 'detailed', 'bulleted'] as const).map((style) => (
                  <button
                    key={style}
                    type="button"
                    onClick={() => setValue('reportStyle', style, { shouldDirty: true })}
                    className={cn(
                      'px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors capitalize',
                      watch('reportStyle') === style
                        ? 'bg-indigo-50 border-indigo-200 text-indigo-700'
                        : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
                    )}
                  >
                    {style === 'bulleted' ? 'Bullet Points' : style.charAt(0).toUpperCase() + style.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* Min Relevance Score */}
            <Controller
              name="thresholds.minRelevanceScore"
              control={control}
              render={({ field }) => (
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-700">Min Relevance Score</p>
                    <p className="text-xs text-slate-500">Only articles above this score will be considered for reports.</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={field.value}
                      onChange={(e) => field.onChange(Number(e.target.value))}
                      className="w-32 accent-indigo-600"
                    />
                    <span className="text-sm font-bold text-slate-900 w-10 text-right">{field.value}%</span>
                  </div>
                </div>
              )}
            />

            {/* Min Final Score */}
            <Controller
              name="thresholds.minFinalScore"
              control={control}
              render={({ field }) => (
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-700">Min Final Score</p>
                    <p className="text-xs text-slate-500">Only articles above this final score will appear in reports.</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={field.value}
                      onChange={(e) => field.onChange(Number(e.target.value))}
                      className="w-32 accent-indigo-600"
                    />
                    <span className="text-sm font-bold text-slate-900 w-10 text-right">{field.value}%</span>
                  </div>
                </div>
              )}
            />

            {/* Max Articles */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-700">Max Articles Per Report</p>
                <p className="text-xs text-slate-500">Maximum number of articles included in each generated report.</p>
              </div>
              <input
                {...register('thresholds.maxArticlesPerReport', { valueAsNumber: true })}
                type="number"
                min={1}
                max={100}
                className={cn(inputClass(!!errors.thresholds?.maxArticlesPerReport), 'w-24 text-center')}
              />
            </div>
            {errors.thresholds?.maxArticlesPerReport && (
              <p className="text-xs text-red-500 font-medium">{errors.thresholds.maxArticlesPerReport.message}</p>
            )}
          </div>
        </SettingsSection>

        {/* Section 3: Retention & Display */}
        <SettingsSection
          title="Retention & Display"
          description="Control how long data is kept before automatic cleanup."
          icon={Database}
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700">Content Retention (days)</label>
              <input
                {...register('retention.contentDays', { valueAsNumber: true })}
                type="number"
                min={1}
                max={730}
                className={inputClass(!!errors.retention?.contentDays)}
              />
              {errors.retention?.contentDays && (
                <p className="text-xs text-red-500 font-medium">{errors.retention.contentDays.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700">Report Retention (days)</label>
              <input
                {...register('retention.reportDays', { valueAsNumber: true })}
                type="number"
                min={1}
                max={3650}
                className={inputClass(!!errors.retention?.reportDays)}
              />
              {errors.retention?.reportDays && (
                <p className="text-xs text-red-500 font-medium">{errors.retention.reportDays.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700">Run History (days)</label>
              <input
                {...register('retention.runHistoryDays', { valueAsNumber: true })}
                type="number"
                min={1}
                max={3650}
                className={inputClass(!!errors.retention?.runHistoryDays)}
              />
              {errors.retention?.runHistoryDays && (
                <p className="text-xs text-red-500 font-medium">{errors.retention.runHistoryDays.message}</p>
              )}
            </div>
          </div>
        </SettingsSection>

        {/* Section 4: Email Delivery */}
        <SettingsSection
          title="Email Delivery"
          description="Configure outbound email delivery for generated reports."
          icon={Mail}
        >
          <div className="space-y-5">
            {/* Enable/Disable */}
            <Controller
              name="emailDelivery.enabled"
              control={control}
              render={({ field }) => (
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-700">Enable Email Delivery</p>
                    <p className="text-xs text-slate-500">Send generated reports directly to specified email addresses.</p>
                  </div>
                  <ToggleSwitch checked={field.value} onChange={field.onChange} />
                </div>
              )}
            />

            {watch('emailDelivery.enabled') && (
              <div className="space-y-4 pt-2 border-t border-slate-100">
                <Controller
                  name="emailDelivery.recipients"
                  control={control}
                  render={({ field }) => (
                    <ListEditor
                      label="Recipients"
                      description="Email addresses to receive generated reports."
                      items={field.value || []}
                      onChange={field.onChange}
                      placeholder="e.g. team@company.com"
                    />
                  )}
                />
                {errors.emailDelivery?.recipients && (
                  <p className="text-xs text-red-500 font-medium">
                    {Array.isArray(errors.emailDelivery.recipients)
                      ? errors.emailDelivery.recipients[0]?.message
                      : 'Invalid email address'}
                  </p>
                )}

                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-slate-700">Subject Prefix</label>
                  <input
                    {...register('emailDelivery.subjectPrefix')}
                    placeholder="e.g. [Intel Report]"
                    className={inputClass(!!errors.emailDelivery?.subjectPrefix)}
                  />
                  {errors.emailDelivery?.subjectPrefix && (
                    <p className="text-xs text-red-500 font-medium">{errors.emailDelivery.subjectPrefix.message}</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </SettingsSection>

        {/* Section 5: Danger Zone */}
        <div className="p-6 bg-red-50 border-2 border-red-200 rounded-xl space-y-4">
          <div className="flex items-center gap-3 text-red-700">
            <AlertTriangle className="w-5 h-5" />
            <h3 className="font-bold text-lg">Danger Zone</h3>
          </div>
          <p className="text-sm text-red-600 leading-relaxed">
            Archiving this workspace will pause all scheduled runs, stop feed fetching, and move the workspace to a read-only state.
            Your data will be retained and the workspace can be restored later.
          </p>
          <DangerButton
            label="Archive Workspace"
            confirmText="Are you sure you want to archive this workspace? All automated operations will be paused."
            onConfirm={() => toast.info('Workspace archive initiated (demo mode).')}
          />
        </div>

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
                    if (settings) reset({
                      schedule: settings.schedule,
                      reportStyle: settings.reportStyle,
                      thresholds: {
                        minRelevanceScore: Math.round(settings.thresholds.minRelevanceScore * 100),
                        minFinalScore: Math.round(settings.thresholds.minFinalScore * 100),
                        maxArticlesPerReport: settings.thresholds.maxArticlesPerReport,
                      },
                      retention: settings.retention,
                      emailDelivery: settings.emailDelivery,
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
                  Save Settings
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
              You have unsaved changes to your settings. If you leave, your changes will be lost.
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

/* ────────────────────────── Reusable Sub-components ────────────────────────── */

function SettingsSection({
  title,
  description,
  icon: Icon,
  children,
}: {
  title: string;
  description: string;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
      <div className="flex items-start gap-4">
        <div className="p-2 bg-slate-50 text-slate-600 rounded-lg shrink-0">
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-base font-bold text-slate-900">{title}</h3>
          <p className="text-sm text-slate-500">{description}</p>
        </div>
      </div>
      <div className="pt-4 border-t border-slate-100">{children}</div>
    </div>
  );
}

function ToggleSwitch({ checked, onChange }: { checked: boolean; onChange: (val: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0',
        checked ? 'bg-indigo-600' : 'bg-slate-200'
      )}
    >
      <span
        className={cn(
          'inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform',
          checked ? 'translate-x-6' : 'translate-x-1'
        )}
      />
    </button>
  );
}

function DangerButton({ label, confirmText, onConfirm }: { label: string; confirmText: string; onConfirm: () => void }) {
  const [showConfirm, setShowConfirm] = useState(false);

  if (showConfirm) {
    return (
      <div className="flex items-center gap-3 p-3 bg-white border border-red-200 rounded-lg">
        <p className="text-sm text-red-700 flex-1">{confirmText}</p>
        <button
          onClick={() => setShowConfirm(false)}
          className="px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={() => {
            onConfirm();
            setShowConfirm(false);
          }}
          className="px-3 py-1.5 text-sm font-bold text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
        >
          Confirm
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setShowConfirm(true)}
      className="flex items-center gap-2 px-4 py-2 bg-white border-2 border-red-300 hover:border-red-500 text-red-600 rounded-lg text-sm font-bold transition-colors"
    >
      <Archive className="w-4 h-4" />
      {label}
    </button>
  );
}
