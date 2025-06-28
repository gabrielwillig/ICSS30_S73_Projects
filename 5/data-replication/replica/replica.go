package main

import (
	"context"
	"log"
	"net"

	pb "data-replication/pb"

	"google.golang.org/grpc"
)

type ReplicaServer struct {
	pb.UnimplementedReplicaServer
	log   []pb.LogEntry
	epoch int
}

func (r *ReplicaServer) ReplicateLog(ctx context.Context, entry *pb.LogEntry) (*pb.Ack, error) {
	if int(entry.Epoch) < r.epoch {
		return &pb.Ack{Success: false, Message: "stale epoch"}, nil
	}

	if int(entry.Offset) != len(r.log) {
		r.log = r.log[:entry.Offset] // truncate on conflict
	}

	r.epoch = int(entry.Epoch)
	r.log = append(r.log, *entry)
	return &pb.Ack{Success: true, Message: "ok"}, nil
}

func (r *ReplicaServer) Commit(ctx context.Context, commit *pb.CommitRequest) (*pb.Ack, error) {
	if int(commit.Offset) < len(r.log) {
		r.log[commit.Offset].Committed = true
		return &pb.Ack{Success: true, Message: "committed"}, nil
	}
	return &pb.Ack{Success: false, Message: "not found"}, nil
}

func main() {
	lis, _ := net.Listen("tcp", ":5005X") // change port per instance
	grpcServer := grpc.NewServer()
	pb.RegisterReplicaServer(grpcServer, &ReplicaServer{})
	log.Fatal(grpcServer.Serve(lis))
}
