import { type InputHTMLAttributes, forwardRef } from "react"
import { cn } from "@/lib/utils"

interface TronInputProps extends InputHTMLAttributes<HTMLInputElement> {}

export const TronInput = forwardRef<HTMLInputElement, TronInputProps>(({ className, ...props }, ref) => {
  return (
    <div className="relative w-full">
      <input
        ref={ref}
        className={cn(
          "w-full px-4 py-3 bg-card/80 border border-primary/50 rounded-md",
          "font-mono text-foreground placeholder:text-muted-foreground",
          "focus:outline-none focus:border-primary focus:glow-cyan",
          "transition-all duration-300",
          "backdrop-blur-sm",
          className,
        )}
        {...props}
      />
    </div>
  )
})

TronInput.displayName = "TronInput"
