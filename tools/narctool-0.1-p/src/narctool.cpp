// narctool by natrium42
// Tool for working with NARC and compressed NARC files (CARC files).
// See narc.h for description of NARC file format.
//
// narc.h, narctool.* by natrium42
// gbalzss.* by and Haruhiko Okumura and Andre Perrot

#define VERSION "0.1-p"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <direct.h>
#include <io.h>
#include <vector>
#include "gbalzss.h"
#include "narc.h"

#pragma warning(disable : 4996)

using namespace std;

void printInfo(char * exeName) {
	printf("Tool for working with NARC and compressed NARC files (CARC files).\n\n");
	printf("\tUsage:\n");
	printf("\t\t%s d <infile.carc> <outfile.narc>\n\t\t\tdecompress CARC file into NARC file\n\n", exeName);
	printf("\t\t%s c <infile.narc> <outfile.carc>\n\t\t\tcompress NARC file into CARC file\n\n", exeName);
	printf("\t\t%s u <infile.narc> <directory>\n\t\t\tunpack NARC file into directory\n\n", exeName);
	printf("\t\t%s p <directory> <outfile.narc>\n\t\t\tpack directory into NARC file\n", exeName);
}

int packNARC(char * narcFileName, char * dir) {
	int result = 0;

	printf("\nPacking...\n");

	struct _finddata_t fileinfo;
	char * findStr = new char[strlen(dir) + 4 + 1];
	sprintf(findStr, "%s\\*.*", dir);
	intptr_t hFile = _findfirst(findStr, &fileinfo);
	delete findStr;
	if(hFile == -1) {
		printf("Error: Directory is empty!\n");
		return -1;
	}

	vector<_finddata_t> files; // vector to contain files to be compressed
	u32 imageSize = 0;
	u32 numFiles = 0;
	do {
		if(fileinfo.attrib & _A_ARCH) {
			printf("%s\n", fileinfo.name);
			files.push_back(fileinfo);
			u32 size = fileinfo.size % 4 == 0 ? fileinfo.size :  fileinfo.size + (4 - (fileinfo.size % 4));
			imageSize += size;
			numFiles++;
		}
	} while(_findnext(hFile, &fileinfo) == 0);

	FILE * narcFile = fopen(narcFileName, "wb");
	if(narcFile == NULL) {
		printf("Error: Couldn't create NARC file!\n");
		_findclose(hFile);
		return -1;
	}

	_findclose(hFile);

	// write Nintendo ARChive (NARC)

	NARCHeader narcHeader;
	narcHeader.id = (u32)'CRAN';
	narcHeader.id0 = 0xFFFE;
	narcHeader.id1 = 0x0100;
	narcHeader.file_size = 0; // TO BE MODIFIED LATER
	narcHeader.length = sizeof(NARCHeader);
	narcHeader.num_sections = 3;
	u32 narcFileSizeOffset = 8;
	fwrite(&narcHeader, sizeof(NARCHeader), 1, narcFile);

	// write FileAllocationTaBle (FATB)
	
	FATBHeader fatbHeader;
	fatbHeader.id = (u32)'FATB';
	fatbHeader.length = sizeof(FATBHeader) + numFiles * sizeof(FATBEntry);
	fatbHeader.num_entries = numFiles;
	fwrite(&fatbHeader, sizeof(FATBHeader), 1, narcFile);

	u32 currOffset = 0;
	for(u32 i = 0; i < numFiles; i++) {
		u32 size = files[i].size % 4 == 0 ? files[i].size :  files[i].size + (4 - (files[i].size % 4));

		FATBEntry fatbEntry;
		fatbEntry.file_from_offset = currOffset;
		fatbEntry.file_to_offset = currOffset + size;
		fwrite(&fatbEntry, sizeof(FATBEntry), 1, narcFile);
		currOffset += size;
	}

	// write FileNameTaBle (FNTB)
	
	FNTBHeader fntbHeader;
	fntbHeader.id = (u32)'FNTB';
	fntbHeader.length = 0; // TO BE MODIFIED LATER
	fntbHeader.unknown0 = 0x00000008;
	fntbHeader.unknown1 = 0x00010000;
	u32 fntbHeaderLengthOffset = ftell(narcFile) + 4;
	u32 fntbHeaderFromOffset = ftell(narcFile);
	fwrite(&fntbHeader, sizeof(FNTBHeader), 1, narcFile);

	for(u32 i = 0; i < numFiles; i++) {
		u8 len = (u8) strlen(files[i].name);
		fwrite(&len, 1, 1, narcFile);				// name size
		fwrite(&files[i].name, 1, len, narcFile);	// name
	}
	fputc(0x00, narcFile); // end of name list

	// pad file to word alignment
	while(ftell(narcFile) % 4 != 0) {
		fputc(0xFF, narcFile); // pad with 0xFF
	}

	// now we know how long this section is, so update the value in its header:
	u32 fntbHeaderToOffset = ftell(narcFile);
	fseek(narcFile, fntbHeaderLengthOffset, SEEK_SET);
	fntbHeader.length = fntbHeaderToOffset - fntbHeaderFromOffset;
	fwrite(&(fntbHeader.length), sizeof(u32), 1, narcFile);
	fseek(narcFile, 0, SEEK_END);

	// write FileIMaGe (FIMG)

	FIMGHeader fimgHeader;
	fimgHeader.id = (u32)'FIMG';
	fimgHeader.length = imageSize;
	fwrite(&fimgHeader, sizeof(FIMGHeader), 1, narcFile);

	for(u32 i = 0; i < numFiles; i++) {
		char * filename = new char[strlen(dir) + 1 + strlen(files[i].name) + 1];
		sprintf(filename, "%s\\%s", dir, files[i].name);
		//printf("%s\n", filename);

		FILE * file = fopen(filename, "rb");
		if(file == NULL) {
			printf("Error: Couldn't open file %s!\n", files[i].name);
			delete filename;
			result = -1;
			break;
		}

		char * buffer = new char[files[i].size];
		fread(buffer, 1, files[i].size, file);
		fwrite(buffer, 1, files[i].size, narcFile);

		// pad file to word alignment
		while(ftell(narcFile) % 4 != 0) {
			fputc(0xFF, narcFile); // pad with 0xFF
		}

		fclose(file);
		delete filename;
		delete buffer;
	}

	// now we know how long the NARC file is, so update file length in NARC header:
	narcHeader.file_size = ftell(narcFile);
	fseek(narcFile, narcFileSizeOffset, SEEK_SET);
	fwrite(&(narcHeader.file_size), sizeof(u32), 1, narcFile);
	fseek(narcFile, 0, SEEK_END);

	fclose(narcFile);

	return result;
}

int unpackNARC(char * narcFileName, char * dir) {
	int result = 0;

	printf("\nUnpacking...\n");

	FILE * narcFile = fopen(narcFileName, "rb");
	if(narcFile == NULL) {
		printf("Error: Couldn't open NARC file!\n");
		return -1;
	}

	// read Nintendo ARChive (NARC)

	NARCHeader narcHeader;
	fread(&narcHeader, sizeof(NARCHeader), 1, narcFile);

	// read FileAllocationTaBle (FATB)

	FATBHeader fatbHeader;
	fread(&fatbHeader, sizeof(FATBHeader), 1, narcFile);
	printf("Number of files: %i\n", fatbHeader.num_entries);

	FATBEntry * fatbEntries = new FATBEntry[fatbHeader.num_entries];
	fread(fatbEntries, sizeof(FATBEntry), fatbHeader.num_entries, narcFile);

	// read FileNameTaBle (FNTB)

	FNTBHeader fntbHeader;
	fread(&fntbHeader, sizeof(FNTBHeader), 1, narcFile);

	FNTBEntry * fntbEntries = new FNTBEntry[fatbHeader.num_entries];
	if(fntbHeader.unknown1 == 8) // 0x00000008 means filenames present?
	{
		for(u32 i = 0; i < fatbHeader.num_entries; i++) {
			fread(&(fntbEntries[i].name_length), sizeof(u8), 1, narcFile);
			memset(&(fntbEntries[i].name), 0, 256);
			fread(&(fntbEntries[i].name), sizeof(char), fntbEntries[i].name_length, narcFile);
		}
	}

	// at the end of names list, there is a single 0x00
	// then this section is padded with 0xFF to word allignment
	fseek(narcFile, narcHeader.length + fatbHeader.length + fntbHeader.length - ftell(narcFile), SEEK_CUR);

	// read FileIMaGe (FIMG)

	FIMGHeader fimgHeader;
	fread(&fimgHeader, sizeof(FIMGHeader), 1, narcFile);
	u32 pos = ftell(narcFile);
	_mkdir(dir);
	for(u32 i = 0; i < fatbHeader.num_entries; i++) {
		u32 fileLength = fatbEntries[i].file_to_offset - fatbEntries[i].file_from_offset;

		char * filename;
		if(fntbHeader.unknown1 == 8) {
			filename = new char[strlen(dir) + 1 + strlen(fntbEntries[i].name) + 1];
			sprintf(filename, "%s\\%s", dir, fntbEntries[i].name);
			printf("%s\n", filename);
		}
		else {
			// Assume no more than 10 characters in the index.
			char *fp1 = strrchr(narcFileName, '\\');
			fp1++;

			char *fp2 = strchr(narcFileName, '.');
			*fp2 = 0;

			char type[5] = "";
			fseek(narcFile, pos + fatbEntries[i].file_from_offset, SEEK_SET);
			fread(type, 1, 4, narcFile);
			type[3] ^= type[0];
			type[0] ^= type[3];
			type[3] ^= type[0];
			type[1] ^= type[2];
			type[2] ^= type[1];
			type[1] ^= type[2];

			filename = new char[strlen(dir) + strlen(fp1) + 17];
			sprintf(filename, "%s\\%s.%d.%s", dir, fp1, i, type);

			*fp2 = '.';
		}

		FILE * file = fopen(filename, "wb");
		if(file == NULL) {
			printf("Error: Couldn't create file %s!\n", filename);
			delete filename;
			result = -1;
			break;
		}

		fseek(narcFile, pos + fatbEntries[i].file_from_offset, SEEK_SET);
		char * buffer = new char[fileLength];
		fread(buffer, 1, fileLength, narcFile);
		fwrite(buffer, 1, fileLength, file);

		fclose(file);
		delete filename;
		delete buffer;
	}


	delete fatbEntries;
	delete fntbEntries;
	fclose(narcFile);
	return result;
}

int main(int argc, char* argv[]) {
	printf("narctool "VERSION" - by natrium42, modifications by Pipian\n");
	if(argc != 4) {
		printInfo(argv[0]);
		return -1;
	}
	if(strcmp(argv[1], "d") == 0 || strcmp(argv[1], "e") == 0) {	// decompress or compress
		FILE * srcFile = fopen(argv[2], "rb");
		FILE * dstFile = fopen(argv[3], "wb");
		if(srcFile == NULL) {
			printf("Error: Couldn't open input file!\n");
			return -1;
		}
		if(dstFile == NULL) {
			printf("Error: Couldn't open output file!\n");
			return -1;
		}

		if(strcmp(argv[1], "d") == 0) { // decompress
			Decode(srcFile, dstFile);
		} else {						// compress
			Encode(srcFile, dstFile);
		}	

		fclose(srcFile);
		fclose(dstFile);
	} else if(strcmp(argv[1], "u") == 0) {	// unpack
		unpackNARC(argv[2], argv[3]);
	} else if(strcmp(argv[1], "p") == 0) {	// pack
		//printf("Error: Not implemented!\n");
		packNARC(argv[3], argv[2]);
	} else {
		printInfo(argv[0]);
		return -1;
	}

	return 0;
}

