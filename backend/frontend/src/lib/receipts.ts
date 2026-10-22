/** Receipts this device has filed, per machine.
 *
 * A receipt is an unguessable bearer token the server issues when a report is filed: whoever
 * holds it can claim that report's reply, like a coat-check stub. Keeping it in local storage
 * is what lets a personal reply survive closing the tab, without the worker ever having an
 * account (see CLAUDE.md's Auth section) - the device holds the ticket, the server never learns
 * who the device belongs to.
 *
 * On a tablet shared by a whole machine this degrades to "questions asked from this tablet",
 * which is the honest limit of device-held tickets.
 */
const LIMIT = 20

function key(machineId: string) {
  return `myReceipts:${machineId}`
}

export function readReceipts(machineId: string): string[] {
  try {
    return JSON.parse(localStorage.getItem(key(machineId)) ?? '[]') as string[]
  } catch {
    return []
  }
}

export function saveReceipt(machineId: string, receipt: string) {
  try {
    const next = [receipt, ...readReceipts(machineId).filter((r) => r !== receipt)].slice(0, LIMIT)
    localStorage.setItem(key(machineId), JSON.stringify(next))
  } catch {
    // A private window or blocked site data just means this device cannot hold tickets.
  }
}
