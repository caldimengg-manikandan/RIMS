'use client';

import { SWRConfig } from 'swr';
import { fetcher } from '@/app/dashboard/lib/swr-fetcher';

export const SWRProvider = ({ children }: { children: React.ReactNode }) => {
  return (
    <SWRConfig 
      value={{
        fetcher,
        refreshInterval: 5000, 
        revalidateOnFocus: true,
        revalidateOnReconnect: true,
        dedupingInterval: 2000
      }}
    >
      {children}
    </SWRConfig>
  );
};
