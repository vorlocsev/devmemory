"""Validate shipped indexed PNG assets without external dependencies."""
import struct, unittest, zlib
from pathlib import Path

class StoreBrandingTests(unittest.TestCase):
    def test_png_assets(self):
        for name, dimensions in [('icon.png',(128,128)),('logo.png',(250,100))]:
            with self.subTest(name=name):
                data=(Path(__file__).resolve().parents[1]/name).read_bytes()
                self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
                pos=8; chunks=[]; compressed=[]
                while pos<len(data):
                    size,kind=struct.unpack_from('>I4s',data,pos)
                    payload=data[pos+8:pos+8+size]
                    crc=struct.unpack_from('>I',data,pos+8+size)[0]
                    self.assertEqual(zlib.crc32(kind+payload),crc)
                    chunks.append(kind)
                    if kind==b'IHDR':
                        self.assertEqual(struct.unpack('>IIBBBBB',payload),(*dimensions,4,3,0,0,0))
                    if kind==b'IDAT': compressed.append(payload)
                    pos+=12+size
                self.assertEqual(pos,len(data))
                self.assertEqual(chunks[0],b'IHDR')
                self.assertEqual(chunks[-1],b'IEND')
                self.assertIn(b'PLTE',chunks)
                pixels=zlib.decompress(b''.join(compressed))
                w,h=dimensions
                self.assertEqual(len(pixels),(1+(w+1)//2)*h)
                self.assertGreater(len(set(pixels)),4)
