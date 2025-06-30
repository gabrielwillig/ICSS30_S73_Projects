package main

import (
	"context"
	"log"
	"net"
	"os"
	"strconv"

	"data-replication/pb"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type ReplicaServer struct {
	pb.UnimplementedReplicaServer
	log          []*pb.LogEntry
	epoch        int
	leaderClient pb.LeaderClient
}

func (r *ReplicaServer) ReplicateLog(ctx context.Context, entry *pb.LogEntry) (*pb.Ack, error) {
	log.Println("Received log entry:", entry)

	if int(entry.Epoch) < r.epoch {
		log.Println("Received stale epoch, ignoring entry")
		return &pb.Ack{Success: false, Message: "stale epoch"}, nil
	}

	// Handle uncommitted entries
	if len(r.log) > 0 && !r.log[len(r.log)-1].Committed {
		log.Println("Uncommitted logs detected")

		var lastCommitedEntry int32

		for i := len(r.log) - 1; i >= 0; i-- {
			if r.log[i].Committed {
				r.log = r.log[:i+1]
				log.Printf("Truncated log to last committed entry at offset %d", i)
				lastCommitedEntry = r.log[i].Offset
				break
			}
		}

		if entry.Offset != lastCommitedEntry+1 {
			offsetToRequest := lastCommitedEntry + 1
			r.startBackgroundSync(offsetToRequest)
		}

		return &pb.Ack{Success: false, Message: "sync started"}, nil
	}

	// Handle offset mismatch (conflict)
	if int(entry.Offset) != len(r.log) {
		log.Printf("Conflict detected: Expected offset %d, got %d", len(r.log), entry.Offset)

		if int(entry.Offset) < len(r.log) {
			// If the replica is ahead the leader's log, truncate the replica log
			log.Printf("Replica log is ahead of leader's log")

			r.log = r.log[:entry.Offset]
			log.Printf("Truncated log to offset %d", entry.Offset)
		} else {
			// If the replica's log is behind the leader's log, start a background sync
			log.Printf("Replica log is behind leader's log")

			offsetToRequest := int32(len(r.log))
			r.startBackgroundSync(offsetToRequest)

			return &pb.Ack{Success: false, Message: "sync started"}, nil
		}
	}

	// Accept log entry
	r.epoch = int(entry.Epoch)
	r.log = append(r.log, entry)
	log.Printf("Saved intermediary log entry: %+v", entry)

	return &pb.Ack{Success: true, Message: "ok"}, nil
}

func (r *ReplicaServer) Commit(ctx context.Context, commit *pb.CommitRequest) (*pb.Ack, error) {
	if int(commit.Offset) < len(r.log) {
		r.log[commit.Offset].Committed = true
		log.Printf("Committed entry at offset %d: %+v", commit.Offset, r.log[commit.Offset])
		return &pb.Ack{Success: true, Message: "committed"}, nil
	}

	log.Printf("Commit failed: Offset %d not found in log", commit.Offset)
	return &pb.Ack{Success: false, Message: "not found"}, nil
}

// SyncWithLeader fetches missing logs from leader starting at offset
func (r *ReplicaServer) syncWithLeader(ctx context.Context, fromOffset int32) error {
	req := &pb.ReadRequest{Offset: fromOffset}
	resp, err := r.leaderClient.Read(ctx, req)
	if err != nil {
		return err
	}

	for _, entry := range resp.Entries {
		// Append missing logs from leader
		r.log = append(r.log, entry)
		log.Printf("Synced log entry from leader: %v", entry)
	}

	log.Printf("Synced %d entries from leader starting at offset %d", len(resp.Entries), fromOffset)
	return nil
}

func (r *ReplicaServer) startBackgroundSync(offset int32) {
	go func() {
		log.Printf("Starting background sync from offset %d", offset)
		if err := r.syncWithLeader(context.Background(), offset); err != nil {
			log.Printf("Background sync failed: %v", err)
		} else {
			log.Printf("Background sync succeeded")
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
	port := 50051 + replicaNum
	addr := ":" + strconv.Itoa(port)

	// Connect to the leader
	leaderAddr := "localhost:50051"
	conn, err := grpc.NewClient(leaderAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatalf("Failed to connect to leader: %v", err)
	}
	leader := pb.NewLeaderClient(conn)

	grpcServer := grpc.NewServer()
	replica := &ReplicaServer{leaderClient: leader}
	pb.RegisterReplicaServer(grpcServer, replica)

	lis, _ := net.Listen("tcp", addr)
	log.Printf("Replica %d listening on %s", replicaNum, addr)

	log.Fatal(grpcServer.Serve(lis))
}
