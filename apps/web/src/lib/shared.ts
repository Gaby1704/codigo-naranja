import constants from "../../../../packages/shared/constants.json"

export const filters = constants.filters
export const zones = constants.zones
export const product = constants.product

export const allFilters = {
  period: filters.allPeriods,
  year: "Todos",
  month: "Todos",
  day: "Todos",
  municipality: filters.allZones,
  violence: filters.allViolence,
  service: filters.allServices,
} as const

export type Filters = {
  period: string
  year: string
  month: string
  day: string
  municipality: string
  violence: string
  service: string
}
