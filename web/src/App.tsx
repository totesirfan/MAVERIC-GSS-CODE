export default function App() {
  return (
    <div className="flex flex-col h-full">
      <div className="bg-[var(--color-bg-panel)] px-3 py-2 border-b border-[#333] flex justify-between items-center">
        <span className="text-[var(--color-label)] font-bold">MAVERIC GSS</span>
        <span className="text-[var(--color-dim)] text-xs">Web Dashboard</span>
      </div>
      <div className="flex-1 flex items-center justify-center text-[var(--color-dim)]">
        Dashboard loading...
      </div>
    </div>
  )
}
