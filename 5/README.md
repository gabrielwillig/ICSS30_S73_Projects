Protobuf compile comand:

# Install the plugin of protobuf for golang if not exists
go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.30.0

# Install the plugin of grpc for golang if not exists
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.3.0

# Compile the proto file
protoc -I=proto --go_out=pb --go_opt=paths=source_relative --go-grpc_out=pb --go-grpc_opt=paths=source_relative  proto/replication.proto