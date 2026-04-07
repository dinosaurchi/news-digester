import * as z from 'zod';

export const feedSchema = z.object({
  name: z.string().min(1, 'Feed name is required'),
  url: z.string().min(1, 'URL is required').url('Please enter a valid URL (e.g., https://example.com/feed)'),
  type: z.enum(['rss', 'website', 'competitor', 'blog']),
  cadence: z.enum(['hourly', 'daily', 'weekly']),
  tags: z.array(z.string()).default([]),
});

export type FeedFormValues = z.infer<typeof feedSchema>;
