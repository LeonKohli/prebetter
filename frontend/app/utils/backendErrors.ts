/** Pydantic validation error format from FastAPI */
export interface ValidationError {
  loc: (string | number)[]
  msg: string
  type?: string
}

/** FastAPI error response shape */
export interface FastAPIErrorData {
  detail?: string | ValidationError[]
}

/**
 * Maps Pydantic validation errors to vee-validate form field errors.
 *
 * Pydantic `loc` is a path like `["body", "field_name"]` — the last element
 * is the field that failed validation. `fieldMap` translates backend snake_case
 * field names to frontend camelCase form field names.
 *
 * Generic over vee-validate's typed `setFieldError` which constrains field
 * names to the form's known fields.
 */
export function mapValidationErrorsToForm<TField extends string>(
  detail: ValidationError[],
  fieldMap: Record<string, TField>,
  setFieldError: (field: TField, message: string | string[] | undefined) => void,
) {
  for (const err of detail) {
    const backendField = err.loc.at(-1)
    if (backendField === undefined) continue
    const fieldName = String(backendField)
    const mapped = fieldMap[fieldName]
    if (mapped) {
      setFieldError(mapped, err.msg)
    }
  }
}
