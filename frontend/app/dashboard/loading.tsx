import { LoadingSpinner } from "@/components/loading-spinner"

export default function DashboardLoading() {
  return (
    <div className="h-full w-full flex items-center justify-center">
      <LoadingSpinner />
    </div>
  )
}
