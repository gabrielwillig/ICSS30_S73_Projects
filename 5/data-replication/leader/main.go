package main

import (
  "context"
  "log"
  "net"
  "sync"

  pb "data-replication/pb"
  "google.golang.org/grpc"
)

type LeaderServer struct {
  pb.UnimplementedLeaderServer
  log []pb.LogEntry
  epoch int
  mu sync.Mutex
  replicas []pb.ReplicaClient
}

func (l *LeaderServer) Write(ctx context.Context, req *pb.WriteRequest) (*pb.WriteResponse, error) {
  l.mu.Lock()
  defer l.mu.Unlock()

  entry := &pb.LogEntry{
    Epoch: int32(l.epoch),
    Offset: int32(len(l.log)),
    Data: req.Data,
  }
  l.log = append(l.log, *entry)

  var wg sync.WaitGroup
  acks := 0
  ackMu := sync.Mutex{}

  for _, replica := range l.replicas {
    wg.Add(1)
    go func(r pb.ReplicaClient) {
      defer wg.Done()
      ack, err := r.ReplicateLog(ctx, entry)
      if err == nil && ack.Success {
        ackMu.Lock()
        acks++
        ackMu.Unlock()
      }
    }(replica)
  }
  wg.Wait()

  if acks >= 2 { // quorum
    for _, replica := range l.replicas {
      _, _ = replica.Commit(ctx, &pb.CommitRequest{
        Epoch: entry.Epoch,
        Offset: entry.Offset,
      })
    }
    l.log[entry.Offset].Committed = true
    return &pb.WriteResponse{Status: "committed"}, nil
  }

  return &pb.WriteResponse{Status: "failed quorum"}, nil
}

func (l *LeaderServer) Read(ctx context.Context, req *pb.ReadRequest) (*pb.ReadResponse, error) {
  var committed []*pb.LogEntry
  for i := range l.log {
      e := &l.log[i]
      if e.Committed {
          committed = append(committed, e)
      }
  }
  return &pb.ReadResponse{Entries: committed}, nil
}

func main() {
  lis, _ := net.Listen("tcp", ":50051")
  grpcServer := grpc.NewServer()
  pb.RegisterLeaderServer(grpcServer, &LeaderServer{})
  log.Fatal(grpcServer.Serve(lis))
}