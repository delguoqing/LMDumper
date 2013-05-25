import glob
import os
import carc_unpacker

for file_path in glob.glob(r"lm/packfiles/*.carc"):
	carc_unpacker.unpack(file_path, r"lm")
