#ifndef _NARC_H_
#define _NARC_H_

typedef unsigned char	u8;
typedef unsigned short	u16;
typedef unsigned int	u32;

// NARC header ---------------------------------------------------------------------------------------
typedef struct {
	u32	id;						// "NARC" or 0x4352414E
	u16	id0; 					// 0xFFFE
	u16	id1; 					// 0x0100
	u32	file_size;				// size of (decompressed) file
	u16	length;					// length of this section (i.e. header)
	u16 num_sections;			// 0x0003 (number of sections: FATB, FNTB, FIMG)
} NARCHeader;

// File Allocation TaBle -----------------------------------------------------------------------------
typedef struct {
	u32	id;						// "BTAF" or 0x46415442
	u32	length;					// length of this section
	u32 num_entries;			// 0x00000009
} FATBHeader;

typedef struct {
	u32 file_from_offset;		// 0x00000000 (offset of file in the image (not including header))
	u32 file_to_offset;			// 0x0000133C
} FATBEntry;

// File Name TaBle -----------------------------------------------------------------------------------
typedef struct {
	u32 id;						// "BTNF" or 0x464E5442
	u32	length;					// length of this section
	u32 unknown0;				// 0x00000008
	u32 unknown1;				// 0x00010000
} FNTBHeader;

typedef struct {
	u8 name_length;				// length of file name
	char name[256];				// file name (not actually 256 bytes, don't read this struct from file)
} FNTBEntry;

typedef struct {
	u8 unknown0;				// 0x00 (end of file name list indicator)
} FNTBFooter;

// then, this section is padded with 0xFF for word allignment

// File IMaGe ----------------------------------------------------------------------------------------
typedef struct {
	u32 id;						// "GMIF" or 0x46494D47
	u32	length;					// length of this section
} FIMGHeader;

#endif // _NARC_H_

