import * as React from "react"
import { Input } from "./input"

/**
 * NumericInput: Input numérico que muestra vacío cuando el valor es 0,
 * permitiendo escribir directamente sin tener que borrar el 0 primero.
 * Almacena el valor como string y lo parsea solo al enviar.
 */
const NumericInput = React.forwardRef(({ value, onChange, ...props }, ref) => {
  const displayValue = value === 0 || value === '0' ? '' : (value ?? '')

  return (
    <Input
      ref={ref}
      type="number"
      value={displayValue}
      onChange={onChange}
      {...props}
    />
  )
})
NumericInput.displayName = "NumericInput"

export { NumericInput }
