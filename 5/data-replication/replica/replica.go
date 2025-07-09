package main

import (
	"context"
	"encoding/json"
	"log"
	"net"
	"os"
	"strconv"

	"data-replication/common"
	"data-replication/pb"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type ReplicaServer struct {
	pb.UnimplementedReplicaServer
	log          []*pb.LogEntry
	epoch        int
	leaderClient pb.LeaderClient
	dir          string // directory for this replica's files
}

func saveLogToFile(filename string, logEntries []*pb.LogEntry) error {
	data, err := json.MarshalIndent(logEntries, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filename, data, 0644)
}

func loadLogFromFile(filename string) ([]*pb.LogEntry, error) {
	data, err := os.ReadFile(filename)
	if err != nil {
		return nil, err
	}
	var logEntries []*pb.LogEntry
	if err := json.Unmarshal(data, &logEntries); err != nil {
		return nil, err
	}
	return logEntries, nil
}

func (r *ReplicaServer) persistLogs() {
	var committed, uncommitted []*pb.LogEntry
	for _, entry := range r.log {
		if entry.Committed {
			committed = append(committed, entry)
		} else {
			uncommitted = append(uncommitted, entry)
		}
	}
	_ = os.MkdirAll(r.dir, 0755)
	_ = saveLogToFile(r.dir+"/committed.json", committed)
	_ = saveLogToFile(r.dir+"/uncommitted.json", uncommitted)
}

func (r *ReplicaServer) loadLogs() {
	_ = os.MkdirAll(r.dir, 0755)
	committed, _ := loadLogFromFile(r.dir + "/committed.json")
	uncommitted, _ := loadLogFromFile(r.dir + "/uncommitted.json")
	r.log = append(committed, uncommitted...)
}

func (r *ReplicaServer) syncInMemoryWithDisk() {
	committed, _ := loadLogFromFile(r.dir + "/committed.json")
	uncommitted, _ := loadLogFromFile(r.dir + "/uncommitted.json")
	r.log = append(committed, uncommitted...)
}

func (r *ReplicaServer) ReplicateLog(ctx context.Context, entry *pb.LogEntry) (*pb.Ack, error) {
	r.syncInMemoryWithDisk() // Always reload from disk before any operation
	common.Info("Received log entry: %v", entry)

	if int(entry.Epoch) < r.epoch {
		common.Warn("Received stale epoch, ignoring entry")
		return &pb.Ack{Success: false, Message: "stale epoch"}, nil
	}

	// Handle uncommitted entries
	if len(r.log) > 0 && !r.log[len(r.log)-1].Committed {
		common.Warn("Uncommitted logs detected")

		var lastCommitedEntry int32

		// Truncate log to last committed entry or when reaching the end of the log
		for i := len(r.log) - 1; i >= 0; i-- {
			if r.log[i].Committed {
				r.log = r.log[:i+1]
				common.Warn("Truncated log to last committed entry at offset %d", i)
				lastCommitedEntry = r.log[i].Offset
				r.persistLogs()
				break
			}

			if i == 0 {
				// If no committed entry found, reset log
				common.Error("No committed entries found, resetting log")
				r.log = []*pb.LogEntry{}
				lastCommitedEntry = -1
				r.persistLogs()
			}
		}

		if entry.Offset != lastCommitedEntry+1 {
			common.Warn("Offset mismatch, starting background sync from %d", lastCommitedEntry+1)
			offsetToRequest := lastCommitedEntry + 1
			r.startBackgroundSync(offsetToRequest)
		}

		r.persistLogs()
		return &pb.Ack{Success: false, Message: "sync started"}, nil
	}

	// Handle offset mismatch (conflict)
	if int(entry.Offset) != len(r.log) {
		common.Warn("Conflict detected: Expected offset %d, got %d", len(r.log), entry.Offset)

		if int(entry.Offset) < len(r.log) {
			// If the replica is ahead the leader's log, truncate the replica log
			common.Warn("Replica log is ahead of leader's log")

			r.log = r.log[:entry.Offset]
			common.Warn("Truncated log to offset %d", entry.Offset)
			r.persistLogs()
		} else {
			// If the replica's log is behind the leader's log, start a background sync
			common.Warn("Replica log is behind leader's log")

			offsetToRequest := int32(len(r.log))
			r.startBackgroundSync(offsetToRequest)
		}

		return &pb.Ack{Success: false, Message: "sync started"}, nil
	}

	// Accept log entry
	r.epoch = int(entry.Epoch)
	r.log = append(r.log, entry)
	r.persistLogs()
	common.Info("Saved intermediary log entry: %+v", entry)

	return &pb.Ack{Success: true, Message: "ok"}, nil
}

func (r *ReplicaServer) Commit(ctx context.Context, commit *pb.CommitRequest) (*pb.Ack, error) {
	if int(commit.Offset) < len(r.log) {
		r.log[commit.Offset].Committed = true
		r.persistLogs()
		common.Info("Committed entry at offset %d: %+v", commit.Offset, r.log[commit.Offset])
		return &pb.Ack{Success: true, Message: "committed"}, nil
	}

	common.Error("Commit failed: Offset %d not found in log", commit.Offset)
	return &pb.Ack{Success: false, Message: "not found"}, nil
}

// SyncWithLeader fetches missing logs from leader starting at offset
func (r *ReplicaServer) syncWithLeader(ctx context.Context, fromOffset int32) error {
	req := &pb.ReadRequest{Offset: fromOffset}
	resp, err := r.leaderClient.Read(ctx, req)
	if err != nil {
		common.Error("SyncWithLeader failed: %v", err)
		return err
	}

	for _, entry := range resp.Entries {
		// Append missing logs from leader
		r.log = append(r.log, entry)
		r.persistLogs()
		common.Info("Synced log entry from leader: %v", entry)
	}

	common.Info("Synced %d entries from leader starting at offset %d", len(resp.Entries), fromOffset)
	return nil
}

func (r *ReplicaServer) startBackgroundSync(offset int32) {
	go func() {
		common.Info("Starting background sync from offset %d", offset)
		if err := r.syncWithLeader(context.Background(), offset); err != nil {
			common.Error("Background sync failed: %v", err)
		} else {
			common.Info("Background sync succeeded")
		}
	}()
}

func main() {
	if len(os.Args) < 2 {
		log.Fatalf("Usage: %s <replica_number>", os.Args[0])
	}
	replicaNum, err := strconv.Atoi(os.Args[1])
	if err != nil {
		log.Fatalf("Invalid replica number: %v", err)
	}
	port := 50050 + replicaNum
	addr := ":" + strconv.Itoa(port)
	dir := "./data/replica_" + strconv.Itoa(replicaNum)

	// Connect to the leader
	leaderAddr := "localhost:50040"
	conn, err := grpc.NewClient(leaderAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatalf("Failed to connect to leader: %v", err)
	}
	leader := pb.NewLeaderClient(conn)

	grpcServer := grpc.NewServer()
	replica := &ReplicaServer{leaderClient: leader, dir: dir}
	replica.loadLogs()
	pb.RegisterReplicaServer(grpcServer, replica)

	lis, _ := net.Listen("tcp", addr)
	common.Info("Replica %d listening on %s", replicaNum, addr)

	log.Fatal(grpcServer.Serve(lis))
}
