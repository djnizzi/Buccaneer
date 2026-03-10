"use client"

import { Activity } from "lucide-react"

interface CompletionDonutProps {
  completion: number
}

export function CompletionDonut({ completion }: CompletionDonutProps) {
  const circumference = 2 * Math.PI * 80
  const offset = circumference - (completion / 100) * circumference

  return (
    <div className="glass-panel glow-cyan rounded-lg p-8 flex flex-col items-center justify-center w-full max-w-sm">
      <div className="relative w-48 h-48">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 200 200">
          {/* Background circle */}
          <circle cx="100" cy="100" r="80" fill="none" stroke="rgba(100, 200, 255, 0.1)" strokeWidth="12" />
          {/* Progress circle */}
          <circle
            cx="100"
            cy="100"
            r="80"
            fill="none"
            stroke="url(#gradient)"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000 ease-out glow-cyan"
            style={{
              filter: "drop-shadow(0 0 8px rgba(0, 255, 255, 0.8))",
            }}
          />
          <defs>
            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="rgba(0, 255, 255, 1)" />
              <stop offset="100%" stopColor="rgba(100, 200, 255, 1)" />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <Activity className="w-8 h-8 text-primary mb-2 animate-pulse" />
          <span className="text-4xl font-mono font-bold text-primary text-glow-cyan">{completion}%</span>
          <span className="text-xs font-mono text-muted-foreground mt-1">COMPLETE</span>
        </div>
      </div>
    </div>
  )
}
