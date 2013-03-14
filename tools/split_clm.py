import struct
import optparse
import sys
import os

def split(clm_data):
	lm_off, lm_size = struct.unpack(">II", clm_data[0x30:0x38])
	tpl_off, tpl_size = struct.unpack(">II", clm_data[0x3c:0x44])
	
	lm_name_beg = 0x45
	lm_name_end = clm_data.find('\x00', lm_name_beg)
	lm_name = clm_data[lm_name_beg: lm_name_end]
	
	tpl_name_beg = lm_name_end + 1
	tpl_name_end = clm_data.find('\x00', tpl_name_beg)
	tpl_name = clm_data[tpl_name_beg: tpl_name_end]
	
	return ((lm_name, lm_off, lm_size), (tpl_name, tpl_off, tpl_size))
	
if __name__ == "__main__":
	parser = optparse.OptionParser()
	parser.add_option("-f", dest="filename")
	parser.add_option("-d", dest="outdir")
	
	(options, args) = parser.parse_args(sys.argv)
	
	f = open(options.filename, "rb")
	data = f.read()
	f.close()
	
	finfo_list = split(data)
	for fname, off, size in finfo_list:
		fout = open(os.path.join(options.outdir, fname), "wb")
		fout.write(data[off: off+size])
		fout.close()