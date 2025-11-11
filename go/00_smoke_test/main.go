package main

import (
	"fmt"
	"io"
	"net"
)

func handleConnection(conn net.Conn) {
	defer conn.Close()
	
	data, err := io.ReadAll(conn) // reads until EOF
    if err != nil {
        fmt.Println("read error:", err)
        return
    }

	fmt.Printf("Data recieved: %v\n", data)
	fmt.Printf("Writing back to conn\n")

	n, err := conn.Write(data)
    if err != nil {
		fmt.Errorf("Error writing: %v, err: %w",data, err)
	}

	if n != len(data) {
		fmt.Printf("Unable to write all bytes, bytes expected: %d, bytes written: %d", len(data), n)
	}

}

func main() {
	port := ":8081"
	ln, err := net.Listen("tcp", port)
	if err != nil {
		fmt.Errorf("Error creating a listener on PORT: %d, with err: %w", port, err)
	}
	fmt.Printf("Server listening on PORT: %s\n", port)
	for {
		conn, err := ln.Accept()
		if err != nil {
			fmt.Errorf("Error listening with err: %w", err)
		}
		go handleConnection(conn)
	}
}