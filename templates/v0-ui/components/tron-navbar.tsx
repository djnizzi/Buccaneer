"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"

const tabs = ["System", "Network", "Analytics", "Settings"]

export function TronNavbar() {
  const [activeTab, setActiveTab] = useState("System")

  return (
    <header className="border-b border-primary/30 bg-card/50 backdrop-blur-sm">
      <div className="container mx-auto px-4">
        <nav className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <div className="font-mono text-xl font-bold text-glow-cyan text-primary">TRON.SYSTEM</div>
            <div className="hidden md:flex items-center gap-1">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    "px-4 py-2 font-mono text-sm transition-all duration-300 relative",
                    activeTab === tab ? "text-primary" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {tab}
                  {activeTab === tab && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary glow-cyan" />}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary glow-cyan animate-pulse" />
            <span className="font-mono text-xs text-muted-foreground">ONLINE</span>
          </div>
        </nav>
      </div>
    </header>
  )
}
