'use client'

import { motion } from 'framer-motion'
import { usePathname } from 'next/navigation'

export default function Template({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  // Only re-animate when the top-level route group changes (e.g., /dashboard/hr → /dashboard/reports)
  // This prevents a 0.75s fade on every sub-page navigation within the same section
  const routeGroup = pathname?.split('/').slice(0, 4).join('/') || 'dashboard'

  return (
    <motion.div
      key={routeGroup}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ ease: 'easeInOut', duration: 0.75 }}
    >
      {children}
    </motion.div>
  )
}
