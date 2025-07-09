package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"data-replication/common"
	"data-replication/pb"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type FileData struct {
	Name string      `json:"name"`
	Data interface{} `json:"data"`
}

type FilesResponse struct {
	Files []FileData `json:"files"`
}

var leaderClient pb.LeaderClient

func readDataFiles() ([]FileData, error) {
	var files []FileData
	root := "./data"
	_ = filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return nil
		}
		if filepath.Ext(path) == ".json" {
			b, err := os.ReadFile(path)
			var parsed interface{} = nil
			if err == nil {
				_ = json.Unmarshal(b, &parsed)
			}
			files = append(files, FileData{
				Name: path,
				Data: parsed,
			})
		}
		return nil
	})
	return files, nil
}

func filesHandler(w http.ResponseWriter, r *http.Request) {
	files, _ := readDataFiles()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(FilesResponse{Files: files})
}

func writeHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	var req struct {
		Data string `json:"data"`
	}
	_ = json.NewDecoder(r.Body).Decode(&req)
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	resp, err := leaderClient.Write(ctx, &pb.WriteRequest{Data: req.Data})
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(err.Error()))
		return
	}
	json.NewEncoder(w).Encode(resp)
}

func readHandler(w http.ResponseWriter, r *http.Request) {
	offset := int32(0)
	if o := r.URL.Query().Get("offset"); o != "" {
		var parsed int
		fmt.Sscanf(o, "%d", &parsed)
		offset = int32(parsed)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	resp, err := leaderClient.Read(ctx, &pb.ReadRequest{Offset: offset})
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(err.Error()))
		return
	}
	json.NewEncoder(w).Encode(resp)
}

func main() {
	conn, _ := grpc.NewClient("localhost:50040", grpc.WithTransportCredentials(insecure.NewCredentials()))
	leaderClient = pb.NewLeaderClient(conn)

	http.HandleFunc("/api/files", filesHandler)
	http.HandleFunc("/api/write", writeHandler)
	http.HandleFunc("/api/read", readHandler)

	http.Handle("/", http.FileServer(http.Dir("./webserver/static")))

	common.Info("Webserver running at http://localhost:8080")
	http.ListenAndServe(":8080", nil)
}
