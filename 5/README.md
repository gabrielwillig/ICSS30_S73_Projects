Protobuf compile comand:

protoc -I=proto --go_out=pb --go_opt=paths=source_relative --go-grpc_out=pb --go-grpc_opt=paths=source_relative  proto/replication.proto