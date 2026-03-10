"use client"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Terminal } from "lucide-react"

interface LogsAccordionProps {
  logs: string[]
}

export function LogsAccordion({ logs }: LogsAccordionProps) {
  return (
    <div className="glass-panel glow-cyan rounded-lg p-4 h-full">
      <Accordion type="single" collapsible defaultValue="logs">
        <AccordionItem value="logs" className="border-none">
          <AccordionTrigger className="hover:no-underline py-2">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-primary" />
              <span className="font-mono text-sm text-primary">System Logs</span>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div className="space-y-2 mt-4 max-h-[400px] overflow-y-auto">
              {logs.map((log, index) => (
                <div
                  key={index}
                  className="font-mono text-xs text-muted-foreground border-l-2 border-primary/50 pl-3 py-1"
                >
                  {log}
                </div>
              ))}
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  )
}
