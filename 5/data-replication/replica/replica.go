package main

import (
	"context"
	"log"
	"net"

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
		return &pb.Ack{Success: false, Message: "stale epoch"}, nil
	}

	// Handle uncommitted entries
	if len(r.log) > 0 && !r.log[len(r.log)-1].Committed {
		log.Println("Uncommitted logs detected, truncating and syncing with leader")

		for i := len(r.log) - 1; i >= 0; i-- {
			if r.log[i].Committed {
				r.log = r.log[:i+1]
				log.Printf("Truncated log to last committed entry at offset %d", i)
				break
			}
		}

		log.Printf("Syncing log with leader async, expected offset %d, got %d", len(r.log), entry.Offset)
		r.startBackgroundSync(entry.Offset)
		return &pb.Ack{Success: false, Message: "sync started"}, nil
	}

	// Handle offset mismatch (conflict)
	if int(entry.Offset) != len(r.log) {
		log.Printf("Conflict detected: expected offset %d, got %d", len(r.log), entry.Offset)

		if int(entry.Offset) < len(r.log) {
			log.Printf("Truncating log to offset %d", entry.Offset)
			r.log = r.log[:entry.Offset]
		} else {
			log.Printf("Syncing log with leader async, expected offset %d, got %d", len(r.log), entry.Offset)
			r.startBackgroundSync(entry.Offset)
			return &pb.Ack{Success: false, Message: "sync started"}, nil
		}
	}

	// Accept log entry
	r.epoch = int(entry.Epoch)
	r.log = append(r.log, entry)

	return &pb.Ack{Success: true, Message: "ok"}, nil
}

func (r *ReplicaServer) Commit(ctx context.Context, commit *pb.CommitRequest) (*pb.Ack, error) {
	if int(commit.Offset) < len(r.log) {
		r.log[commit.Offset].Committed = true
		return &pb.Ack{Success: true, Message: "committed"}, nil
	}

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
	leaderAddr := "localhost:50051" // change to actual leader address
	conn, err := grpc.NewClient(leaderAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatalf("Failed to connect to leader: %v", err)
	}
	leader := pb.NewLeaderClient(conn)

	lis, _ := net.Listen("tcp", ":50052") // change port per instance

	grpcServer := grpc.NewServer()
	replica := &ReplicaServer{leaderClient: leader}
	pb.RegisterReplicaServer(grpcServer, replica)
	log.Fatal(grpcServer.Serve(lis))
}
