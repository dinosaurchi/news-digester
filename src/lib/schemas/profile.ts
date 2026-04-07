import * as z from 'zod';

export const profileSchema = z.object({
  businessName: z.string().min(2, 'Business name must be at least 2 characters'),
  description: z.string().min(10, 'Description must be at least 10 characters'),
  products: z.array(z.string()),
  competitors: z.array(z.string()),
  priorityThemes: z.array(z.string()),
  excludedTopics: z.array(z.string()),
  notes: z.string(),
});

export type ProfileFormValues = z.infer<typeof profileSchema>;
