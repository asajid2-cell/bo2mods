# T6 (Black Ops 2) XAnimParts Binary Format Reference

## Source
All structs from: https://github.com/Laupetin/OpenAssetTools
- src/Common/Game/T6/T6_Assets.h - Struct definitions
- src/ZoneCode/Game/T6/XAssets/XAnimParts.txt - Zone serialization spec
- src/ZoneWriting/Game/T6/ - Zone writing infrastructure

---

## 1. Core Struct: XAnimParts (x86, 32-bit pointers, sizeof=104)

| Offset | Size | Field | Type |
|--------|------|-------|------|
| 0x00 | 4 | name | const char* |
| 0x04 | 2 | dataByteCount | uint16_t |
| 0x06 | 2 | dataShortCount | uint16_t |
| 0x08 | 2 | dataIntCount | uint16_t |
| 0x0A | 2 | randomDataByteCount | uint16_t |
| 0x0C | 2 | randomDataIntCount | uint16_t |
| 0x0E | 2 | numframes | uint16_t |
| 0x10 | 1 | bLoop | bool |
| 0x11 | 1 | bDelta | bool |
| 0x12 | 1 | bDelta3D | bool (T6-specific) |
| 0x13 | 1 | bLeftHandGripIK | bool |
| 0x14 | 4 | streamedFileSize | uint32_t |
| 0x18 | 10 | boneCount[10] | uint8_t[10] |
| 0x22 | 1 | notifyCount | uint8_t |
| 0x23 | 1 | assetType | int8_t |
| 0x24 | 1 | isDefault | bool |
| 0x25 | 3 | (padding) | - |
| 0x28 | 4 | randomDataShortCount | uint32_t |
| 0x2C | 4 | indexCount | uint32_t |
| 0x30 | 4 | framerate | float |
| 0x34 | 4 | frequency | float |
| 0x38 | 4 | primedLength | float |
| 0x3C | 4 | loopEntryTime | float |
| 0x40 | 4 | names | uint16_t* |
| 0x44 | 4 | dataByte | char* |
| 0x48 | 4 | dataShort | int16_t* |
| 0x4C | 4 | dataInt | int32_t* |
| 0x50 | 4 | randomDataShort | int16_t* |
| 0x54 | 4 | randomDataByte | char* |
| 0x58 | 4 | randomDataInt | int32_t* |
| 0x5C | 4 | indices | XAnimIndices (union) |
| 0x60 | 4 | notify | XAnimNotifyInfo* |
| 0x64 | 4 | deltaPart | XAnimDeltaPart* |

Total: 0x68 = 104 bytes

---

## 2. boneCount[10]

Zone spec: set count names boneCount[9]
boneCount[9] = TOTAL bone count = names array size
boneCount[0..8] = bones by data type (channels animated)

---

## 3. Supporting Types

### XAnimIndices (union, 4 bytes)
- _1 (char*): byte indices when numframes < 256
- _2 (uint16_t*): short indices when numframes >= 256
- Count: indexCount

### XAnimNotifyInfo (8 bytes)
- name: uint16_t (script string) at +0
- (2 pad bytes)
- time: float at +4 (normalized 0.0-1.0)

### XAnimDeltaPart (12 bytes)
- trans: XAnimPartTrans* at +0
- quat2: XAnimDeltaPartQuat2* at +4
- quat: XAnimDeltaPartQuat* at +8

### XAnimPartTrans
- size: uint16_t (keyframe count, 0=single frame)
- smallTrans: char (1=ByteVec 3bytes, 0=UShortVec 6bytes)
- u: union { XAnimPartTransFrames frames; vec3_t frame0; }

### XAnimPartTransFrames (align 4)
- mins: float[3] (minimum bounds)
- size: float[3] (range for denormalization)
- frames: XAnimDynamicFrames (ByteVec* or UShortVec*)
- indices: XAnimDynamicIndicesTrans (char* or uint16_t*)
- Encoding: pos = mins + (val / max_val) * size
- ByteVec=uint8[3], max_val=255; UShortVec=uint16[3], max_val=65535

### XAnimDeltaPartQuat2 (2-comp rotation)
- size: uint16_t
- u: union { frames; XQuat2 frame0; }
- XQuat2: align(4), int16_t value[2]

### XAnimDeltaPartQuat (4-comp rotation)
- size: uint16_t
- u: union { frames; XQuat frame0; }
- XQuat: align(4), int16_t value[4], actual = val / 32767.0

---

## 4. Zone Serialization Order

Struct written first (104 bytes), then pointers resolved in ORDER:
1. name -> null-terminated string
2. names -> uint16_t[boneCount[9]]
3. notify -> XAnimNotifyInfo[notifyCount]
4. deltaPart -> XAnimDeltaPart(1)
   - trans -> XAnimPartTrans(1), sub: indices THEN frames
   - quat2 -> XAnimDeltaPartQuat2(1), sub: indices THEN frames
   - quat -> XAnimDeltaPartQuat(1), sub: indices THEN frames
5. dataByte -> char[dataByteCount]
6. dataShort -> int16_t[dataShortCount]
7. dataInt -> int32_t[dataIntCount]
8. randomDataShort -> int16_t[randomDataShortCount]
9. randomDataByte -> char[randomDataByteCount]
10. randomDataInt -> int32_t[randomDataIntCount]
11. indices -> byte/uint16_t[indexCount]

---

## 5. Zone File Structure (.ff)

Header (12 bytes): magic[8] + version(uint32=147)
Then Salsa20+zlib XChunk stream containing:
- XFile header: totalSize(u32) + externalSize(u32) + blockSizes[8](u32x8)
- XAssetList: {stringList, dependCount, depends, assetCount, assets}
- Script strings
- XAsset array: type(u32) + header_ptr(u32)
- Asset data

XAnimParts block = XFILE_BLOCK_TEMP (0)
Pointer encoding: 0xFFFFFFFE = following, 0x00 = null
ASSET_TYPE_XANIMPARTS = 4

Salsa20 key (PC hex): 641D8A2FE31D3AA63622BBC9CE8587229D42B0F8ED9B924130BF88B65EDC50BE
Chunk size: 0x8000, max write: 0x7FC0
File suffix: min 0x40 zero bytes aligned to 0x40

---

## 6. T6 vs T5 vs IW4

| Feature | T5 | IW4 | T6 |
|---------|----|----|-----|
| bDelta3D | No | No | Yes |
| DeltaPartQuat2 | No | Yes | Yes |
| boneCount | [10] | [10] | [10] |
| primedLength | Yes | No | Yes |
| loopEntryTime | Yes | No | Yes |

---

## 7. Python Compiler Notes

1. Struct = 104 bytes with 3-byte pad at 0x25
2. boneCount[9] = total bones = names count
3. Script strings = uint16 zone string table indices
4. Pointer fixups: 0xFFFFFFFE=following, 0=null
5. Delta only when bDelta=true
6. Indices: byte(<256 frames) or short(>=256)
7. Serialization order != struct order
8. Minimal idle: numframes=0, empty arrays
9. No OAT dumper exists for XAnimParts
10. Writer/Loader generated at build time from ZoneCode
