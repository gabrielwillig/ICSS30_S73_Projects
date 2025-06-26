package main

import (
  "context"
  "fmt"
  "log"
  "time"

  pb "data-replication/pb"
  "google.golang.org/grpc"
)

func main() {
  conn, _ := grpc.Dial("localhost:50051", grpc.WithInsecure())
  client := pb.NewLeaderClient(conn)

  ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
  defer cancel()

  _, err := client.Write(ctx, &pb.WriteRequest{Data: "Hello"})
  if err != nil {
    log.Fatal(err)
  }

  resp, _ := client.Read(ctx, &pb.ReadRequest{})
  fmt.Println("Committed entries:")
  for _, e := range resp.Entries {
    fmt.Printf("[%d:%d] %s\n", e.Epoch, e.Offset, e.Data)
  }
}
