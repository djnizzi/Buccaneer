"use client"

import { useState } from "react"
import { TronNavbar } from "@/components/tron-navbar"
import { TronInput } from "@/components/tron-input"
import { TronButton } from "@/components/tron-button"
import { LogsAccordion } from "@/components/logs-accordion"
import { CompletionDonut } from "@/components/completion-donut"
import { LyricsAccordion } from "@/components/lyrics-accordion"
import { TronFooter } from "@/components/tron-footer"

export default function TronPage() {
  const [inputValue, setInputValue] = useState("")
  const [logs, setLogs] = useState<string[]>([
    "System initialized...",
    "Loading neural networks...",
    "Connecting to mainframe...",
  ])
  const [completion, setCompletion] = useState(35)

  const handleLaunch = () => {
    const newLog = `[${new Date().toLocaleTimeString()}] Launch sequence initiated`
    setLogs((prev) => [...prev, newLog])
    setCompletion((prev) => Math.min(prev + 15, 100))
  }

  return (
    <div className="min-h-screen flex flex-col bg-background relative overflow-hidden">
      {/* Background abstract art */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute top-20 left-10 w-64 h-64 bg-primary/20 rounded-full blur-[100px]" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent/20 rounded-full blur-[120px]" />
        <div className="absolute top-1/2 left-1/3 w-48 h-48 bg-primary/10 rounded-full blur-[80px]" />
      </div>

      {/* Content */}
      <div className="relative z-10 flex flex-col min-h-screen">
        <TronNavbar />

        <main className="flex-1 container mx-auto px-4 py-8 space-y-8">
          {/* Input and Launch Section */}
          <div className="flex flex-col md:flex-row gap-4 items-center justify-center">
            <TronInput
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Enter command sequence..."
              className="flex-1 max-w-2xl"
            />
            <TronButton onClick={handleLaunch}>Launch</TronButton>
          </div>

          {/* Three Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column - Logs Accordion */}
            <div className="lg:col-span-1">
              <LogsAccordion logs={logs} />
            </div>

            {/* Center Column - Completion Donut */}
            <div className="lg:col-span-1 flex items-center justify-center">
              <CompletionDonut completion={completion} />
            </div>

            {/* Right Column - Lyrics Accordion */}
            <div className="lg:col-span-1">
              <LyricsAccordion />
            </div>
          </div>
        </main>

        <TronFooter />
      </div>
    </div>
  )
}
