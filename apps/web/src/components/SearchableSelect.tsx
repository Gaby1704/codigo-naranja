import { Check, ChevronDown, Search, X } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import { createPortal } from "react-dom"

export type SelectOption = string | { value: string; label: string }

function fold(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim()
}

export function SearchableSelect({
  value,
  options,
  onChange,
  ariaLabel,
  searchPlaceholder = "Buscar opción…",
}: {
  value: string
  options: SelectOption[]
  onChange: (next: string) => void
  ariaLabel: string
  searchPlaceholder?: string
}) {
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [highlighted, setHighlighted] = useState(0)
  const [coords, setCoords] = useState<{ top: number; left: number; width: number; openUp: boolean }>({
    top: 0,
    left: 0,
    width: 220,
    openUp: false,
  })

  const normalizedOptions = useMemo(
    () => options.map((opt) => (typeof opt === "string" ? { value: opt, label: opt } : opt)),
    [options],
  )

  const selectedLabel = useMemo(
    () => normalizedOptions.find((opt) => opt.value === value)?.label ?? value,
    [normalizedOptions, value],
  )

  const filtered = useMemo(() => {
    const q = fold(query)
    if (!q) return normalizedOptions
    return normalizedOptions.filter((opt) => fold(opt.label).includes(q) || fold(opt.value).includes(q))
  }, [normalizedOptions, query])

  const updatePosition = () => {
    const el = triggerRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const viewportW = window.innerWidth
    const viewportH = window.innerHeight
    const menuWidth = Math.min(Math.max(rect.width, 190), viewportW - 16)
    const left = Math.max(8, Math.min(rect.left, viewportW - menuWidth - 8))
    const spaceBelow = viewportH - rect.bottom
    const openUp = spaceBelow < 230 && rect.top > spaceBelow
    const top = openUp ? rect.top - 4 : rect.bottom + 4
    setCoords({ top, left, width: menuWidth, openUp })
  }

  useEffect(() => {
    if (!open) return
    updatePosition()
    setHighlighted(Math.max(0, filtered.findIndex((item) => item.value === value)))
    const timer = window.setTimeout(() => searchRef.current?.focus(), 10)
    const handleOutside = (event: MouseEvent) => {
      const target = event.target as Node
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) return
      setOpen(false)
    }
    const handleReposition = () => updatePosition()
    document.addEventListener("mousedown", handleOutside)
    window.addEventListener("resize", handleReposition)
    window.addEventListener("scroll", handleReposition, true)
    return () => {
      window.clearTimeout(timer)
      document.removeEventListener("mousedown", handleOutside)
      window.removeEventListener("resize", handleReposition)
      window.removeEventListener("scroll", handleReposition, true)
    }
  }, [open])

  useEffect(() => {
    if (!open) setQuery("")
  }, [open])

  useEffect(() => {
    setHighlighted(0)
  }, [query])

  function selectOption(optionValue: string) {
    onChange(optionValue)
    setOpen(false)
    triggerRef.current?.focus()
  }

  function handleKeyDown(event: React.KeyboardEvent) {
    if (event.key === "Escape") {
      event.preventDefault()
      setOpen(false)
      triggerRef.current?.focus()
    } else if (event.key === "ArrowDown") {
      event.preventDefault()
      setHighlighted((prev) => Math.min(filtered.length - 1, prev + 1))
    } else if (event.key === "ArrowUp") {
      event.preventDefault()
      setHighlighted((prev) => Math.max(0, prev - 1))
    } else if (event.key === "Enter" && filtered[highlighted]) {
      event.preventDefault()
      selectOption(filtered[highlighted].value)
    }
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className={`s2-trigger ${open ? "s2-open" : ""}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="s2-value">{selectedLabel}</span>
        <ChevronDown size={14} className="s2-arrow" />
      </button>
      {open &&
        createPortal(
          <div
            ref={menuRef}
            className={`s2-dropdown ${coords.openUp ? "s2-up" : ""}`}
            style={{
              top: `${coords.top}px`,
              left: `${coords.left}px`,
              width: `${coords.width}px`,
            }}
            onKeyDown={handleKeyDown}
          >
            <div className="s2-search-wrap">
              <Search size={13} />
              <input
                ref={searchRef}
                type="text"
                className="s2-search-input"
                value={query}
                placeholder={searchPlaceholder}
                aria-label={`Buscar en ${ariaLabel}`}
                onChange={(event) => setQuery(event.target.value)}
              />
              {query && (
                <button
                  type="button"
                  className="s2-clear-search"
                  aria-label="Limpiar búsqueda"
                  onClick={() => {
                    setQuery("")
                    searchRef.current?.focus()
                  }}
                >
                  <X size={12} />
                </button>
              )}
            </div>
            <ul className="s2-options" role="listbox" aria-label={ariaLabel}>
              {filtered.length === 0 ? (
                <li className="s2-empty">Sin coincidencias</li>
              ) : (
                filtered.map((option, idx) => {
                  const isSelected = option.value === value
                  const isHighlighted = idx === highlighted
                  return (
                    <li
                      key={option.value}
                      role="option"
                      aria-selected={isSelected}
                      className={`s2-option ${isSelected ? "selected" : ""} ${isHighlighted ? "highlighted" : ""}`}
                      onMouseEnter={() => setHighlighted(idx)}
                      onMouseDown={(event) => {
                        event.preventDefault()
                        selectOption(option.value)
                      }}
                    >
                      <span>{option.label}</span>
                      {isSelected && <Check size={13} />}
                    </li>
                  )
                })
              )}
            </ul>
          </div>,
          document.body,
        )}
    </>
  )
}
