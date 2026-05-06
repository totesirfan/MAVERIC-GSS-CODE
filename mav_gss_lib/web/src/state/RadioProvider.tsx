import { useMemo, type ReactNode } from 'react'
import { useRadioSocket } from '@/components/radio/useRadioSocket'
import { RadioContext, RadioStatusContext, type RadioStatusValue } from './radioContexts'

export function RadioProvider({ children }: { children: ReactNode }) {
  const radio = useRadioSocket()
  // Narrow slot for consumers (e.g. header pill) that only need radio
  // status — log-line updates re-render `radio` but leave `status` stable.
  const statusValue = useMemo<RadioStatusValue>(
    () => ({ status: radio.status, connected: radio.connected }),
    [radio.status, radio.connected],
  )
  return (
    <RadioStatusContext.Provider value={statusValue}>
      <RadioContext.Provider value={radio}>{children}</RadioContext.Provider>
    </RadioStatusContext.Provider>
  )
}
