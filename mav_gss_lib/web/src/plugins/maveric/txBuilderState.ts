// Module-scoped state that survives TxBuilder unmount/remount.
//
// The MAVERIC TX builder remounts every time the operator reopens the
// panel; without an out-of-tree cache the destination node would
// always reset to nodes[0]. Live here, not inside the component, so a
// remount keeps the operator's last pick.

let lastDestNode: string | null = null

export function getLastDestNode(): string | null {
  return lastDestNode
}

export function setLastDestNode(name: string | null): void {
  lastDestNode = name
}
