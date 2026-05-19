'use client';

import { SWRConfig } from 'swr';
import { fetcher } from '@/app/dashboard/lib/swr-fetcher';

export const SWRProvider = ({ children }: { children: React.ReactNode }) => {
  return (
    <SWRConfig 
      value={{
        fetcher,
        refreshInterval: 0,        // disabled: no background polling — manual refresh only
        revalidateOnFocus: true,   // enabled: re-fetch when tab regains focus (keeps data fresh)
        revalidateOnReconnect: true,
        dedupingInterval: 2000     // 2s: prevents duplicate requests but doesn't suppress forced revalidations
      }}
    >
      {children}
    </SWRConfig>
  );
};
