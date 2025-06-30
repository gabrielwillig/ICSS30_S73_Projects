package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"data-replication/pb"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func main() {
	conn, _ := grpc.NewClient("localhost:50051", grpc.WithTransportCredentials(insecure.NewCredentials()))
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
