import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "../../lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-blue-500/10 text-blue-400",
        secondary:
          "border-transparent bg-gray-700 text-gray-200",
        destructive:
          "border-transparent bg-red-500/10 text-red-400",
        outline: "text-gray-300 border-gray-600",
      },
      color: {
        blue: "border-transparent bg-blue-500/10 text-blue-400",
        red: "border-transparent bg-red-500/10 text-red-400",
        green: "border-transparent bg-green-500/10 text-green-400",
        orange: "border-transparent bg-orange-500/10 text-orange-400",
        amber: "border-transparent bg-amber-500/10 text-amber-400",
        purple: "border-transparent bg-purple-500/10 text-purple-400",
        indigo: "border-transparent bg-indigo-500/10 text-indigo-400",
        yellow: "border-transparent bg-yellow-500/10 text-yellow-400",
        cyan: "border-transparent bg-cyan-500/10 text-cyan-400",
        gray: "border-transparent bg-gray-500/10 text-gray-400",
        rose: "border-transparent bg-rose-500/10 text-rose-400",
        violet: "border-transparent bg-violet-500/10 text-violet-400",
        fuchsia: "border-transparent bg-fuchsia-500/10 text-fuchsia-400",
        emerald: "border-transparent bg-emerald-500/10 text-emerald-400",
      },
      size: {
        default: "px-2.5 py-0.5 text-xs",
        xs: "px-2 py-0.5 text-[10px]",
        sm: "px-2 py-0.5 text-xs",
        lg: "px-3 py-1 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, color, size, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant: color ? undefined : variant, color, size }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
