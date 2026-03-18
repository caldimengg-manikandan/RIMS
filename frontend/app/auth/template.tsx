'use client'

import { motion } from 'motion/react'

export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ ease: 'easeInOut', duration: 0.75 }}
      className="w-full flex justify-center"
    >
      {children}
    </motion.div>
  )
}
