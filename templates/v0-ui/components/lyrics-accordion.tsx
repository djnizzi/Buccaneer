"use client"

import { useState, useEffect } from "react"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Music } from "lucide-react"

const sampleLyrics = [
  {
    artist: "Daft Punk",
    song: "Technologic",
    lines: ["Buy it, use it, break it, fix it", "Trash it, change it, mail, upgrade it"],
  },
  {
    artist: "The Prodigy",
    song: "Firestarter",
    lines: ["I'm the firestarter, twisted firestarter", "You're the firestarter, twisted firestarter"],
  },
  {
    artist: "Kraftwerk",
    song: "The Robots",
    lines: ["We are the robots", "We are programmed just to do"],
  },
  {
    artist: "Daft Punk",
    song: "Derezzed",
    lines: ["[Instrumental]", "The Grid. A digital frontier..."],
  },
]

export function LyricsAccordion() {
  const [currentLyric, setCurrentLyric] = useState(sampleLyrics[0])

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentLyric(sampleLyrics[Math.floor(Math.random() * sampleLyrics.length)])
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="glass-panel glow-cyan rounded-lg p-4 h-full">
      <Accordion type="single" collapsible defaultValue="lyrics">
        <AccordionItem value="lyrics" className="border-none">
          <AccordionTrigger className="hover:no-underline py-2">
            <div className="flex items-center gap-2">
              <Music className="w-4 h-4 text-primary" />
              <span className="font-mono text-sm text-primary">Audio Feed</span>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div className="space-y-4 mt-4">
              <div className="border-l-2 border-primary/50 pl-3">
                <div className="font-mono text-xs text-primary mb-1">{currentLyric.artist}</div>
                <div className="font-mono text-xs text-muted-foreground mb-3">{currentLyric.song}</div>
                {currentLyric.lines.map((line, index) => (
                  <div key={index} className="font-mono text-sm text-foreground/80 mb-2">
                    {line}
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-2 pt-2">
                <div className="flex gap-1">
                  {[...Array(5)].map((_, i) => (
                    <div
                      key={i}
                      className="w-1 bg-primary/50 rounded-full animate-pulse"
                      style={{
                        height: `${Math.random() * 20 + 10}px`,
                        animationDelay: `${i * 100}ms`,
                      }}
                    />
                  ))}
                </div>
                <span className="font-mono text-xs text-muted-foreground">STREAMING</span>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  )
}
