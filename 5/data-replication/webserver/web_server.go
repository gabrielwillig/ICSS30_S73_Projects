package main

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
)

type FileData struct {
	Name string      `json:"name"`
	Data interface{} `json:"data"`
}

type FilesResponse struct {
	Files []FileData `json:"files"`
}

func readDataFiles() ([]FileData, error) {
	var files []FileData
	root := "../data"
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

func main() {
	http.HandleFunc("/api/files", filesHandler)
	http.Handle("/", http.FileServer(http.Dir("./static")))
	println("Webserver running at http://localhost:8080")
	http.ListenAndServe(":8080", nil)
}
