# Setup

## Install go deps
go mod tidy

## Install protoc plugins for golang

### Install the plugin of protobuf for golang if not exists
go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.30.0

### Install the plugin of grpc for golang if not exists
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.3.0

## Compile the proto file (if generated protofiles are not committed in repo)
protoc -I=proto \
    --go_out=pb --go_opt=paths=source_relative \
    --go-grpc_out=pb --go-grpc_opt=paths=source_relative  \
    proto/replication.proto

# Run
Start in the following order:

## Web Server
The Web Server shows everything and is also the client.

> go run ./webserver

## leader
> go run ./leader

## replicas
> go run ./replica 1
> go run ./replica 2
> go run ./replica 3

## Observations
- The server usually don't have entries on it's uncommitted file since it trucates immediatelly when the process fails in the commit phase, in contrast with replicas that usually cannot determine when it fails, just when they receive another entry

# TODO
Conflict detected: Expected offset 8, got 9
2025/07/03 02:56:16 Replica log is behind leader's log
2025/07/03 02:56:16 Commit failed: Offset 9 not found in log

- The leader should read its files for the operations, not only consider what is in memory