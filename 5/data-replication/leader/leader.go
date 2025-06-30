package main

import (
	"context"
	"log"
	"net"
	"sync"

	"data-replication/pb"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// Quorum constant
const QUORUM = 1

type LeaderServer struct {
	pb.UnimplementedLeaderServer
	log      []*pb.LogEntry
	epoch    int
	mu       sync.Mutex
	replicas []pb.ReplicaClient
}

func (l *LeaderServer) Write(ctx context.Context, req *pb.WriteRequest) (*pb.WriteResponse, error) {
	log.Println("Received write request:", req.Data)

	l.mu.Lock()
	defer l.mu.Unlock()

	entry := &pb.LogEntry{
		Epoch:     int32(l.epoch),
		Offset:    int32(len(l.log)),
		Data:      req.Data,
		Committed: false,
	}
	l.log = append(l.log, entry)

	acks := l.replicateToQuorum(ctx, entry)
	if acks < QUORUM {
		log.Printf("Failed to achieve replication quorum: %d/%d", acks, QUORUM)
		l.log = l.log[:len(l.log)-1]
		return &pb.WriteResponse{Status: "failed quorum"}, nil
	}

	commitAcks := l.commitToQuorum(ctx, entry)
	if commitAcks < QUORUM {
		log.Printf("Failed to achieve commit quorum: %d/%d", commitAcks, QUORUM)
		l.log = l.log[:len(l.log)-1]
		return &pb.WriteResponse{Status: "failed quorum"}, nil
	}

	l.log[entry.Offset].Committed = true
	log.Printf("Committed entry: %+v", entry)

	return &pb.WriteResponse{Status: "committed"}, nil
}

func (l *LeaderServer) replicateToQuorum(ctx context.Context, entry *pb.LogEntry) int {
	var wg sync.WaitGroup
	var acks int
	var ackMu sync.Mutex

	for _, replica := range l.replicas {
		wg.Add(1)
		go func(r pb.ReplicaClient) {
			defer wg.Done()
			ack, err := r.ReplicateLog(ctx, entry)
			if err == nil && ack.Success {
				ackMu.Lock()
				acks++
				ackMu.Unlock()
				log.Printf("✅ Replicated to %v | Entry: %v", r, entry)
			} else {
				log.Printf("❌ Failed to replicate to %v | Err: %v | Entry: %v", r, err, entry)
			}
		}(replica)
	}

	wg.Wait()
	return acks
}

func (l *LeaderServer) commitToQuorum(ctx context.Context, entry *pb.LogEntry) int {
	var wg sync.WaitGroup
	var acks int
	var ackMu sync.Mutex

	for _, replica := range l.replicas {
		wg.Add(1)
		go func(r pb.ReplicaClient) {
			defer wg.Done()
			ack, err := r.Commit(ctx, &pb.CommitRequest{
				Epoch:  entry.Epoch,
				Offset: entry.Offset,
			})
			if err == nil && ack.Success {
				ackMu.Lock()
				acks++
				ackMu.Unlock()
				log.Printf("✅ Committed on %v | Entry: %v", r, entry)
			} else {
				log.Printf("❌ Failed to commit on %v | Err: %v | Entry: %v", r, err, entry)
			}
		}(replica)
	}

	wg.Wait()
	return acks
}

// Read only committed entries and sends them back to the client
func (l *LeaderServer) Read(ctx context.Context, req *pb.ReadRequest) (*pb.ReadResponse, error) {
	var committed []*pb.LogEntry
	for i := range l.log {
		e := l.log[i]
		if e.Committed {
			committed = append(committed, e)
		}
	}
	return &pb.ReadResponse{Entries: committed}, nil
}

func main() {
	// List of replica addresses (update as needed)
	replicaAddrs := []string{
		"localhost:50052",
		// "localhost:50053",
		// "localhost:50054",
	}
	var replicas []pb.ReplicaClient
	for _, addr := range replicaAddrs {
		conn, err := grpc.NewClient(addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
		if err != nil {
			log.Fatalf("Failed to connect to replica %s: %v", addr, err)
		}
		replicas = append(replicas, pb.NewReplicaClient(conn))
	}

	lis, _ := net.Listen("tcp", ":50051")

	grpcServer := grpc.NewServer()
	leader := &LeaderServer{replicas: replicas, epoch: 0}
	pb.RegisterLeaderServer(grpcServer, leader)
	log.Fatal(grpcServer.Serve(lis))
}
