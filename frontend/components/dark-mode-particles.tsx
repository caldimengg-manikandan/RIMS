"use client"

import { useTheme } from "next-themes"
import { useEffect, useState } from "react"
import Particles from "@/components/ui/particles"

export function DarkModeParticles() {
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return null
  }

  if (resolvedTheme === "dark") {
    return (
      <div className="absolute inset-0 z-0 pointer-events-none">
         <Particles
            particleColors={["#ffffff", "#a0a0ff", "#bf6bff"]}
            particleCount={200}
            particleSpread={10}
            speed={0.1}
            particleBaseSize={100}
            moveParticlesOnHover
            alphaParticles={false}
            disableRotation={false}
            pixelRatio={1}
            className="h-full w-full"
        />
      </div>
    )
  }

  return null
}
