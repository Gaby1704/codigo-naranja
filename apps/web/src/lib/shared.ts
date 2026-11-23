import constants from "../../../../packages/shared/constants.json"

export const filters = constants.filters
export const zones = constants.zones
export const product = constants.product

export const allFilters = {
  period: filters.allPeriods,
  municipality: filters.allZones,
  violence: filters.allViolence,
  service: filters.allServices,
} as const

export type Filters = {
  period: string
  municipality: string
  violence: string
  service: string
}
