import { useContext } from 'react'
import { RadioContext, RadioStatusContext, type RadioStatusValue, type RadioValue } from './radioContexts'

export function useRadio(): RadioValue {
  const ctx = useContext(RadioContext)
  if (!ctx) throw new Error('useRadio must be used within RadioProvider')
  return ctx
}

export function useRadioStatus(): RadioStatusValue {
  const ctx = useContext(RadioStatusContext)
  if (!ctx) throw new Error('useRadioStatus must be used within RadioProvider')
  return ctx
}
