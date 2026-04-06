/** Config-driven full names for abbreviated node identifiers. */
export function getNodeFullName(name: string, nodeDescriptions?: Record<string, string>): string | undefined {
  return nodeDescriptions?.[name]
}
