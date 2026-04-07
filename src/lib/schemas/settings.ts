import * as z from 'zod';

export const settingsSchema = z.object({
  schedule: z.object({
    enabled: z.boolean(),
    frequency: z.enum(['daily', 'twice_daily', 'weekly']),
    timeOfDay: z.string().min(1, 'Time of day is required'),
    timezone: z.string().min(1, 'Timezone is required'),
  }),
  reportStyle: z.enum(['concise', 'detailed', 'bulleted']),
  thresholds: z.object({
    minRelevanceScore: z.number().min(0).max(100),
    minFinalScore: z.number().min(0).max(100),
    maxArticlesPerReport: z.number().int().min(1).max(100),
  }),
  retention: z.object({
    contentDays: z.number().int().min(1).max(730),
    reportDays: z.number().int().min(1).max(3650),
    runHistoryDays: z.number().int().min(1).max(3650),
  }),
  emailDelivery: z.object({
    enabled: z.boolean(),
    recipients: z.array(z.string()),
    subjectPrefix: z.string(),
  }),
});

export type SettingsFormValues = z.infer<typeof settingsSchema>;
