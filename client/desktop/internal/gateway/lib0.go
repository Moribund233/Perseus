package gateway

import "bytes"

// lib0 varint/varstring 编解码（对齐 yjs 生态 encoding.writeVarUint/writeVarString）。
// Hocuspocus 的 AuthenticationMessage 为 lib0 二进制帧：
//
//	varString(docName) varUint(MessageType.Auth=2) varUint(AuthSubType.Token=0)
//	varString(token) varString(version)
//
// 其中 varUint 为 LEB128（7bit/字节，最高位续传），varString 为「字节长度前缀 + UTF-8」。

func readVarUint(b []byte, off int) (uint64, int, bool) {
	var result uint64
	shift := uint(0)
	for {
		if off >= len(b) {
			return 0, off, false
		}
		c := b[off]
		off++
		result |= uint64(c&0x7f) << shift
		if c&0x80 == 0 {
			return result, off, true
		}
		shift += 7
		if shift >= 64 {
			return 0, off, false
		}
	}
}

func writeVarUint(buf *bytes.Buffer, v uint64) {
	for v >= 0x80 {
		buf.WriteByte(byte(v&0x7f) | 0x80)
		v >>= 7
	}
	buf.WriteByte(byte(v))
}

func readVarString(b []byte, off int) (string, int, bool) {
	n, next, ok := readVarUint(b, off)
	if !ok || n > uint64(len(b)-next) {
		return "", off, false
	}
	end := next + int(n)
	return string(b[next:end]), end, true
}

func writeVarString(buf *bytes.Buffer, s string) {
	writeVarUint(buf, uint64(len(s)))
	buf.WriteString(s)
}
