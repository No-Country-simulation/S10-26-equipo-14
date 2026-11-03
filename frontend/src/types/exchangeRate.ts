import type { DecimalString } from './price'

/** Historical exchange quote; rate_side distinguishes reference/buy/sell. */
export interface ExchangeRate {
  id: number
  source: string
  rate_type: string
  rate_side: 'reference' | 'buy' | 'sell'
  base_currency: string
  quote_currency: string
  rate: DecimalString
  observed_at: string
}
