import { SkeletonBlock } from '@/components/ui/Spinner'

export function LemonPageSkeleton() {
  return (
    <div className="space-y-6">
      <SkeletonBlock className="h-24 w-full" />
      <SkeletonBlock className="h-80 w-full" />
      <SkeletonBlock className="h-72 w-full" />
      <SkeletonBlock className="h-72 w-full" />
      <SkeletonBlock className="h-72 w-full" />
    </div>
  )
}
