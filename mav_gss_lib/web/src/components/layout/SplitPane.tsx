import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable'

interface SplitPaneProps {
  left: React.ReactNode
  right: React.ReactNode
}

export function SplitPane({ left, right }: SplitPaneProps) {
  return (
    <ResizablePanelGroup orientation="horizontal" className="flex-1 h-full">
      <ResizablePanel defaultSize={33} minSize={15}>
        {left}
      </ResizablePanel>
      <ResizableHandle withHandle className="mx-2 w-1 rounded-full bg-transparent hover:bg-[#222222] data-[resize-handle-active]:bg-[#30C8E0] transition-colors" />
      <ResizablePanel defaultSize={67} minSize={15}>
        {right}
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}
