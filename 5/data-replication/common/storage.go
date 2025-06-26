// --- common/storage.go ---
package common

type LogEntry struct {
  Epoch   int
  Offset  int
  Data    string
  Committed bool
}