"""Tiny valid synthetic PNG for OFFLINE adapters, never browser-capture proof."""
import struct
import zlib

def _chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)

PNG = (b'\x89PNG\r\n\x1a\n' + _chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
       + _chunk(b'IDAT', zlib.compress(b'\x00\xf7\x93\x1a')) + _chunk(b'IEND', b''))
