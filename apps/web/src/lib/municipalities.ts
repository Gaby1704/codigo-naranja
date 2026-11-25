import type { Summary } from "../../../../packages/shared/types"

export function normalizeMunicipalityKey(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[.,;:/\-()]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toUpperCase()
}

const CANONICAL_ALIASES: Record<string, string> = {
  ACUAMANALA: "ACUAMANALA DE MIGUEL HIDALGO",
  AMAXAC: "AMAXAC DE GUERRERO",
  APETATITLAN: "APETATITLAN DE ANTONIO CARVAJAL",
  "SAN PABLO APETATITLAN": "APETATITLAN DE ANTONIO CARVAJAL",
  ALTZAYANCA: "ATLTZAYANCA",
  CHIAUTEMPAN: "CHIAUTEMPAN",
  "SANTA ANA CHIAUTEMPAN": "CHIAUTEMPAN",
  CONTLA: "CONTLA DE JUAN CUAMATZI",
  TEQUEXQUITLA: "EL CARMEN TEQUEXQUITLA",
  "CARMEN TEQUEXQUITLA": "EL CARMEN TEQUEXQUITLA",
  ESPANITA: "ESPANITA",
  IXTACUIXTLA: "IXTACUIXTLA DE MARIANO MATAMOROS",
  TLALTELULCO: "LA MAGDALENA TLALTELULCO",
  "MAGDALENA TLALTELULCO": "LA MAGDALENA TLALTELULCO",
  MAZATECOCHCO: "MAZATECOCHCO DE JOSE MARIA MORELOS",
  MUNOZ: "MUNOZ DE DOMINGO ARENAS",
  NANACAMILPA: "NANACAMILPA DE MARIANO ARISTA",
  NATIVITAS: "NATIVITAS",
  PAPALOTLA: "PAPALOTLA DE XICOHTENCATL",
  SANCTORUM: "SANCTORUM DE LAZARO CARDENAS",
  "SAN PABLO DEL MONTE": "SAN PABLO DEL MONTE",
  "VILLA VICENTE GUERRERO": "SAN PABLO DEL MONTE",
  "VICENTE GUERRERO": "SAN PABLO DEL MONTE",
  TEPETITLA: "TEPETITLA DE LARDIZABAL",
  TETLA: "TETLA DE LA SOLIDARIDAD",
  "TLAXCALA DE XICOHTENCATL": "TLAXCALA",
  "TLAXCALA CENTRO": "TLAXCALA",
  YAUHQUEMECAN: "YAUHQUEMEHCAN",
  XALOSTOC: "XALOZTOC",
  ZITLALTEPEC: "ZILTLALTEPEC DE TRINIDAD SANCHEZ SANTOS",
  ZILTALTEPEC: "ZILTLALTEPEC DE TRINIDAD SANCHEZ SANTOS",
  "ZILTLALTEPEC DE TRINIDAD SANCHEZ SANTOS": "ZILTLALTEPEC DE TRINIDAD SANCHEZ SANTOS",
  "ZITLALTEPEC DE TRINIDAD SANCHEZ SANTOS": "ZILTLALTEPEC DE TRINIDAD SANCHEZ SANTOS",
}

export function canonicalizeMunKey(value: string): string {
  const key = normalizeMunicipalityKey(value)
  return CANONICAL_ALIASES[key] ?? key
}

export function municipalitiesMatch(a: string, b: string): boolean {
  const ka = canonicalizeMunKey(a)
  const kb = canonicalizeMunKey(b)
  if (!ka || !kb) return false
  if (ka === kb) return true
  const firstA = ka.split(" ")[0]
  const firstB = kb.split(" ")[0]
  if (firstA.length >= 5 && (kb.startsWith(`${firstA} `) || ka.startsWith(`${firstB} `))) {
    return true
  }
  return false
}

export function findSummaryForGeoName(geoName: string, summaries: Summary[]): Summary | undefined {
  const exact = summaries.find((item) => normalizeMunicipalityKey(item.name) === normalizeMunicipalityKey(geoName))
  if (exact) return exact
  const alias = summaries.find((item) => canonicalizeMunKey(item.name) === canonicalizeMunKey(geoName))
  if (alias) return alias
  return summaries.find((item) => municipalitiesMatch(item.name, geoName))
}

export function findFilterValueForGeoName(geoName: string, options: string[]): string | undefined {
  const exact = options.find((opt) => normalizeMunicipalityKey(opt) === normalizeMunicipalityKey(geoName))
  if (exact) return exact
  const alias = options.find((opt) => canonicalizeMunKey(opt) === canonicalizeMunKey(geoName))
  if (alias) return alias
  return options.find((opt) => municipalitiesMatch(opt, geoName))
}
