'use client'

import { useTheme } from "next-themes"
import { ScaleLoader } from "react-spinners"
import { useEffect, useState } from "react"

export const LoadingSpinner = () => {
  const { theme, systemTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) return null

  const currentTheme = theme === 'system' ? systemTheme : theme
  const color = currentTheme === 'dark' ? '#ffffff' : '#000000'

  return (
    <div className="flex items-center justify-center min-h-[50vh] w-full">
      <ScaleLoader color={color} />
    </div>
  )
}
