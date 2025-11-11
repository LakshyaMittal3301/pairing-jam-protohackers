package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net"
)

const MALFORMED = "malformed"

type IncomingMsg struct {
	Method string  `json:"method"`
	Number float64 `json:"number"`
}

func isPrime(n float64) bool {
	if n > math.Floor(n) {
		return false
	}
	intN := int(n)
	if intN <= 1 {
		return false
	}
	if intN == 2 {
		return true
	}
	for i := 2; i*i <= intN; i++ {
		if intN%i == 0 {
			return false
		}
	}
	return true
}

func buildResponse(msgStr string) string {
	msg, err := parseMessage(msgStr)
	if err != nil {
		return MALFORMED
	}
	prime := isPrime(msg.Number)
	return fmt.Sprintf("{\"method\": \"isPrime\",\"prime\":\"%v\"}", prime)
}

func parseMessage(str string) (IncomingMsg, error) {
	var msg IncomingMsg
	err := json.Unmarshal([]byte(str), &msg)
	if err != nil || msg.Method != "isPrime" {
		return IncomingMsg{}, fmt.Errorf("message parse error: %w", err)
	}

	return msg, nil
}

func handleConnection(conn net.Conn) {
	defer conn.Close()

	reader := bufio.NewReader(conn)

	for {
		str, err := reader.ReadString('\n')
		if err == io.EOF {
			if len(str) != 0 {
				conn.Write([]byte(MALFORMED))
			}
			break
		}

		if err != nil {
			fmt.Printf("Error reading message: %s", err.Error())
			fmt.Printf("ABORTING SESSION")
			break
		} else {
			fmt.Printf("READ: %s\n", str)

			response := buildResponse(str)
			fmt.Printf("REPLY: %s\n", response)
			conn.Write([]byte(response))
		}
	}
}

func main() {
	port := ":8081"
	ln, err := net.Listen("tcp", port)
	if err != nil {
		fmt.Printf("Error creating a listener on PORT: %s, with err: %s", port, err.Error())
	}
	fmt.Printf("Server listening on PORT: %s\n", port)
	for {
		conn, err := ln.Accept()
		if err != nil {
			fmt.Printf("Error listening with err: %s", err.Error())
		}
		go handleConnection(conn)
	}
}
