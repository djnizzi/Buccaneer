export function TronFooter() {
  return (
    <footer className="border-t border-primary/30 bg-card/50 backdrop-blur-sm mt-auto">
      <div className="container mx-auto px-4 py-6">
        <div className="text-center">
          <p className="font-mono text-xs text-muted-foreground">
            © {new Date().getFullYear()} TRON.SYSTEM - All Rights Reserved
          </p>
        </div>
      </div>
    </footer>
  )
}
