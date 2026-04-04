import { useState, useEffect, useCallback } from 'react'
import { GlobalHeader } from '@/components/layout/GlobalHeader'
import { SplitPane } from '@/components/layout/SplitPane'
import { useRxSocket } from '@/hooks/useRxSocket'
import { useTxSocket } from '@/hooks/useTxSocket'
import { RxPanel } from '@/components/rx/RxPanel'
import { TxPanel } from '@/components/tx/TxPanel'
import { ConfigSidebar } from '@/components/config/ConfigSidebar'
import { LogViewer } from '@/components/logs/LogViewer'
import { HelpModal } from '@/components/shared/HelpModal'
import type { GssConfig } from '@/lib/types'

function isInputFocused(): boolean {
  const tag = document.activeElement?.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' ||
    (document.activeElement as HTMLElement)?.isContentEditable === true
}

export default function App() {
  const rx = useRxSocket()
  const tx = useTxSocket()

  const [config, setConfig] = useState<GssConfig | null>(null)
  const [showLogs, setShowLogs] = useState(false)
  const [showConfig, setShowConfig] = useState(false)
  const [showHelp, setShowHelp] = useState(false)

  // Keyboard shortcuts
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Ctrl+S: send queue
    if (e.ctrlKey && e.key === 's') {
      e.preventDefault()
      if (tx.queue.length > 0 && !tx.sendProgress) {
        tx.sendAll()
      }
      return
    }

    // Ctrl+Z: undo last
    if (e.ctrlKey && e.key === 'z') {
      e.preventDefault()
      tx.undoLast()
      return
    }

    // Escape: close modals in priority order, or abort send
    if (e.key === 'Escape') {
      if (showConfig) { setShowConfig(false); return }
      if (showLogs) { setShowLogs(false); return }
      if (showHelp) { setShowHelp(false); return }
      if (tx.sendProgress) { tx.abortSend(); return }
      return
    }

    // ?: toggle help (only when not in an input element)
    if (e.key === '?' && !isInputFocused()) {
      setShowHelp((v) => !v)
      return
    }
  }, [showConfig, showLogs, showHelp, tx])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  useEffect(() => {
    fetch('/api/config')
      .then((r) => r.json())
      .then((data: GssConfig) => setConfig(data))
      .catch(() => {/* offline */})
  }, [])

  const version = config?.general?.version ?? '...'
  const frequency = config?.tx?.frequency ?? 0
  const uplinkMode = config?.tx?.uplink_mode ?? ''

  return (
    <div className="flex flex-col h-full">
      <GlobalHeader
        version={version}
        zmqRx={rx.status.zmq}
        zmqTx={tx.connected ? 'LIVE' : 'DOWN'}
        frequency={frequency}
        uplinkMode={uplinkMode}
        onLogsClick={() => setShowLogs((v) => !v)}
        onConfigClick={() => setShowConfig((v) => !v)}
        onHelpClick={() => setShowHelp((v) => !v)}
      />
      <SplitPane
        left={
          <TxPanel
            queue={tx.queue}
            summary={tx.summary}
            history={tx.history}
            sendProgress={tx.sendProgress}
            guardConfirm={tx.guardConfirm}
            error={tx.error}
            uplinkMode={uplinkMode}
            queueCommand={tx.queueCommand}
            queueBuilt={tx.queueBuilt}
            deleteItem={tx.deleteItem}
            clearQueue={tx.clearQueue}
            undoLast={tx.undoLast}
            toggleGuard={tx.toggleGuard}
            reorder={tx.reorder}
            addDelay={tx.addDelay}
            editDelay={tx.editDelay}
            sendAll={tx.sendAll}
            abortSend={tx.abortSend}
            approveGuard={tx.approveGuard}
            rejectGuard={tx.rejectGuard}
          />
        }
        right={
          <RxPanel packets={rx.packets} status={rx.status} />
        }
      />
      <ConfigSidebar open={showConfig} onClose={() => { setShowConfig(false); fetch('/api/config').then(r => r.json()).then(setConfig) }} />
      <LogViewer open={showLogs} onClose={() => setShowLogs(false)} />
      <HelpModal open={showHelp} onClose={() => setShowHelp(false)} />
    </div>
  )
}
