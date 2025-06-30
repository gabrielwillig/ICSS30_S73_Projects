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

	var wg sync.WaitGroup
	acks := 0
	ackMu := sync.Mutex{}

	for _, replica := range l.replicas {
		wg.Add(1)
		go func(r pb.ReplicaClient) {
			defer wg.Done()
			ack, err := r.ReplicateLog(ctx, entry)
			// Log the replication attempt
			if err == nil && ack.Success {
				ackMu.Lock()
				acks++
				ackMu.Unlock()

				log.Printf("Success replication request \n Replica: %v \n Entry: %v", replica, entry)
			} else {
				log.Printf("Fail replication request \n Replica %v: \n Err: %v \n Entry: %v", replica, err, entry)
			}
		}(replica)
	}
	wg.Wait()

	if acks < QUORUM {
		log.Printf("Failed to achieve replication request quorum: %d acks received, %d required", acks, QUORUM)
		l.log = l.log[:len(l.log)-1]
		return &pb.WriteResponse{Status: "failed quorum"}, nil
	}

	commitAcks := 0

	for _, replica := range l.replicas {
		ack, err := replica.Commit(ctx, &pb.CommitRequest{
			Epoch:  entry.Epoch,
			Offset: entry.Offset,
		})

		if err == nil && ack.Success {
			commitAcks++
			log.Printf("Success commit request \n Replica: %v \n Entry: %v", replica, entry)
		} else {
			log.Printf("Fail commit request \n Replica %v: \n Err: %v \n Entry: %v", replica, err, entry)
		}
	}

	if commitAcks < QUORUM {
		log.Printf("Failed to achieve commit quorum: %d acks received, %d required", commitAcks, QUORUM)
		l.log = l.log[:len(l.log)-1]
		return &pb.WriteResponse{Status: "failed quorum"}, nil
	}

	l.log[entry.Offset].Committed = true
	log.Printf("Committed \n Entry: %v", entry)
	return &pb.WriteResponse{Status: "committed"}, nil
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
