package main

import (
	"encoding/binary"
	"fmt"
	"io"
	"net"
)

const N = 9

type TimestampedPrice struct {
	Timestamp int32
	Price int32
}

func readN(conn net.Conn, n int) ([]byte, error) {
	buf := make([]byte, n)
	total := 0
	for total < n {
		// Attempt to read the remaining bytes
		nRead, err := conn.Read(buf[total:])
		if err != nil {
			if err == io.EOF {
				// Connection closed before all data arrived
				return buf[:total], io.ErrUnexpectedEOF
			}
			return buf[:total], err
		}
		total += nRead
	}
	return buf, nil
}

func parseBuffer(buffer []byte) (int32, int32, error) {
	if len(buffer) != N - 1 {
		return 0, 0, fmt.Errorf("Unexpected Buffer length: %d", len(buffer))
	}

	firstIntBuffer, secondIntBuffer := buffer[:4], buffer[4:]

	return int32(binary.BigEndian.Uint32(firstIntBuffer)), int32(binary.BigEndian.Uint32(secondIntBuffer)), nil
}

func getMeanBetween(mintime, maxtime int32, prices []TimestampedPrice)  int32 {
	var count int32
	var totalSum int32
	for _, price := range prices {
		if mintime <= price.Timestamp && price.Timestamp <= maxtime {
			totalSum += price.Price
			count++
		}
	}
	if count == 0 {
		return 0
	}
	return totalSum / count
}

func handleConnection(conn net.Conn) {
	defer conn.Close()

	prices := []TimestampedPrice{}

	for {
		buffer, err := readN(conn, N)
		if err != nil || len(buffer) != N {
			break
		}

		firstInt32, secondInt32, err := parseBuffer(buffer[1:])
		if err != nil {
			fmt.Printf("Error occured while parsing: %s", err.Error())
			break
		}

		if buffer[0] == 'I' {
			prices = append(prices, TimestampedPrice{
				Timestamp: firstInt32,
				Price: secondInt32,
			})

		} else if (buffer[0] == 'Q') {
			mean := getMeanBetween(firstInt32, secondInt32, prices)

			buf := make([]byte, 4)
			binary.BigEndian.PutUint32(buf, uint32(mean))

			_, err := conn.Write(buf)
			if err != nil {
				fmt.Printf("Error writing to connection: %s", err.Error())
				break
			}
		} else {
			break
		}
	}

	fmt.Printf("Ending session!\n")
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
