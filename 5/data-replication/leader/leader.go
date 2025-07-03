package main

import (
	"context"
	"encoding/json"
	"log"
	"net"
	"os"
	"sync"

	"data-replication/pb"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// Quorum constant
const QUORUM = 2

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
	l.persistLogs()

	acks := l.replicateToQuorum(ctx, entry)
	if acks < QUORUM {
		log.Printf("Failed to achieve replication quorum: %d/%d", acks, QUORUM)
		l.log = l.log[:len(l.log)-1]
		l.persistLogs()
		return &pb.WriteResponse{Status: "failed quorum"}, nil
	}

	commitAcks := l.commitToQuorum(ctx, entry)
	if commitAcks < QUORUM {
		log.Printf("Failed to achieve commit quorum: %d/%d", commitAcks, QUORUM)
		l.log = l.log[:len(l.log)-1]
		l.persistLogs()
		return &pb.WriteResponse{Status: "failed quorum"}, nil
	}

	l.log[entry.Offset].Committed = true
	l.persistLogs()
	log.Printf("Committed entry: %+v", entry)

	return &pb.WriteResponse{Status: "committed"}, nil
}

func (l *LeaderServer) replicateToQuorum(ctx context.Context, entry *pb.LogEntry) int {
	var wg sync.WaitGroup
	var acks int
	var ackMu sync.Mutex

	for replicaNum, replica := range l.replicas {
		wg.Add(1)
		go func(r pb.ReplicaClient) {
			defer wg.Done()
			ack, err := r.ReplicateLog(ctx, entry)
			if err == nil && ack.Success {
				ackMu.Lock()
				acks++
				ackMu.Unlock()
				log.Printf("✅ Successful requested replication | Replica: %v | Entry: %v", replicaNum, entry)
			} else {
				log.Printf("❌ Failed requesting replication | Replica: %v | Err: %v | Entry: %v", replicaNum, err, entry)
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

	for replicaNum, replica := range l.replicas {
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
				log.Printf("✅ Successful committed | Replica: %v | Entry: %v", replicaNum, entry)
			} else {
				log.Printf("❌ Failed to commit | Replica: %v | Err: %v | Entry: %v", replicaNum, err, entry)
			}
		}(replica)
	}

	wg.Wait()
	return acks
}

// Read only committed entries and sends them back to the client
func (l *LeaderServer) Read(ctx context.Context, req *pb.ReadRequest) (*pb.ReadResponse, error) {
	var committed []*pb.LogEntry

	for i := int(req.Offset); i < len(l.log); i++ {
		e := l.log[i]
		if e.Committed {
			committed = append(committed, e)
		}
	}

	return &pb.ReadResponse{Entries: committed}, nil
}

func saveLeaderLogToFile(filename string, logEntries []*pb.LogEntry) error {
	data, err := json.MarshalIndent(logEntries, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filename, data, 0644)
}

func loadLeaderLogFromFile(filename string) ([]*pb.LogEntry, error) {
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

func (l *LeaderServer) persistLogs() {
	var committed, uncommitted []*pb.LogEntry
	for _, entry := range l.log {
		if entry.Committed {
			committed = append(committed, entry)
		} else {
			uncommitted = append(uncommitted, entry)
		}
	}
	_ = os.MkdirAll("data/leader", 0755)
	_ = saveLeaderLogToFile("data/leader/committed.json", committed)
	_ = saveLeaderLogToFile("data/leader/uncommitted.json", uncommitted)
}

func (l *LeaderServer) loadLogs() {
	_ = os.MkdirAll("data/leader", 0755)
	committed, _ := loadLeaderLogFromFile("data/leader/committed.json")
	uncommitted, _ := loadLeaderLogFromFile("data/leader/uncommitted.json")
	l.log = append(committed, uncommitted...)
}

func main() {
	// List of replica addresses (update as needed)
	replicaAddrs := []string{
		"localhost:50052",
		"localhost:50053",
		"localhost:50054",
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
	leader.loadLogs()
	pb.RegisterLeaderServer(grpcServer, leader)
	log.Fatal(grpcServer.Serve(lis))
}
