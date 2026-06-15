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
