type LogoSize = 'compact' | 'sidebar' | 'hero'

const sizeClasses: Record<LogoSize, string> = {
  compact: 'h-8 w-8',
  sidebar: 'h-12 w-12',
  hero: 'h-[88px] w-[88px] sm:h-[104px] sm:w-[104px]',
}

export function Logo({ size = 'compact', className = '' }: { size?: LogoSize; className?: string }) {
  return (
    <img
      src="/siresoft-mark.png"
      alt="SireSoft"
      className={`${sizeClasses[size]} shrink-0 object-contain ${className}`}
      draggable={false}
    />
  )
}
