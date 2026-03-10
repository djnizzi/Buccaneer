import { type ButtonHTMLAttributes, forwardRef } from "react"
import { cn } from "@/lib/utils"

interface TronButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {}

export const TronButton = forwardRef<HTMLButtonElement, TronButtonProps>(({ className, children, ...props }, ref) => {
  return (
    <button
      ref={ref}
      className={cn(
        "px-6 py-3 bg-primary/20 border-2 border-primary rounded-md",
        "font-mono font-bold text-primary uppercase tracking-wider",
        "hover:bg-primary/30 hover:glow-cyan-strong",
        "active:scale-95",
        "transition-all duration-300",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        "glow-cyan",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
})

TronButton.displayName = "TronButton"
