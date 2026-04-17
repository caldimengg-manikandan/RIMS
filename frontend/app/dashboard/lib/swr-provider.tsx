'use client';

import { SWRConfig } from 'swr';
import { fetcher } from '@/app/dashboard/lib/swr-fetcher';

export const SWRProvider = ({ children }: { children: React.ReactNode }) => {
  return (
    <SWRConfig 
      value={{
        fetcher,
        refreshInterval: 0,        // disabled: was 5000ms — was hammering remote Supabase DB constantly
        revalidateOnFocus: false,  // disabled: was re-fetching every time tab regained focus
        revalidateOnReconnect: true,
        dedupingInterval: 15000    // increased: was 2000ms — prevents rapid re-fetches on navigation
      }}
    >
      {children}
    </SWRConfig>
  );
};
