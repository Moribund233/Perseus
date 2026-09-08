package lsp

import (
	"bufio"
	"bytes"
	"errors"
	"fmt"
	"io"
	"strconv"
	"strings"
)

var errMalformedHeader = errors.New("lsp: malformed Content-Length header")

// FrameWriter 把 JSON 消息写成 LSP 标准帧（Content-Length 头 + 空行 + body）。
type FrameWriter struct {
	w io.Writer
}

func NewFrameWriter(w io.Writer) *FrameWriter { return &FrameWriter{w: w} }

// WriteJSON 发送一条完整 JSON 消息。
func (fw *FrameWriter) WriteJSON(msg []byte) (int, error) {
	var b bytes.Buffer
	fmt.Fprintf(&b, "Content-Length: %d\r\n\r\n", len(msg))
	b.Write(msg)
	return fw.w.Write(b.Bytes())
}

// Next 返回下一条消息体（LSP 帧）。
type FramedMessage struct {
	Body []byte
}

// FrameReader 从流中解析 LSP Content-Length 帧。
type FrameReader struct {
	r *bufio.Reader
}

func NewFrameReader(r io.Reader) *FrameReader {
	return &FrameReader{r: bufio.NewReader(r)}
}

// Next 读取下一帧正文；io.EOF 表示流结束。
func (fr *FrameReader) Next() ([]byte, error) {
	var length int
	for {
		line, err := fr.r.ReadString('\n')
		if err != nil {
			return nil, err
		}
		line = strings.TrimRight(line, "\r\n")
		if line == "" {
			if length == 0 {
				return nil, errMalformedHeader
			}
			break
		}
		name, value, found := strings.Cut(line, ":")
		if !found || !strings.EqualFold(strings.TrimSpace(name), "Content-Length") {
			continue
		}
		length, err = strconv.Atoi(strings.TrimSpace(value))
		if err != nil || length < 0 {
			return nil, errMalformedHeader
		}
	}
	body := make([]byte, length)
	if _, err := io.ReadFull(fr.r, body); err != nil {
		return nil, err
	}
	return body, nil
}