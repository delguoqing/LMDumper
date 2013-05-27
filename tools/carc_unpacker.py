import struct
import sys
import os

def unpack(file_path, out_dir):
	
	if not os.path.exists(out_dir):
		os.mkdir(out_dir)
#	out_dir = os.path.join(out_dir, os.path.splitext(os.path.split(file_path)[1])[0])
#	if not os.path.exists(out_dir):
#		os.mkdir(out_dir)	
	tmp_path = os.path.join(out_dir, "tmp.dearc")
	
	
	if os.system("DSDecmp.exe %s %s" % (file_path, tmp_path)) != 0:
		return
	
	if os.path.exists(tmp_path):
		f = open(tmp_path, "rb")
	else:
		f = open(file_path, "rb")
	
	f.seek(0x28)
	
	token_count, = struct.unpack(">I", f.read(4))
	file_count = token_count
	
	filename_tab_off = file_count * 0xC + 0x20
	file_info_off = 0x38
	
	f.seek(file_info_off)
	folder_name_len, = struct.unpack(">I", f.read(4))
	folder_name_len -= 2
	f.seek(filename_tab_off + 1)
	folder_name = f.read(folder_name_len)
	
	sub_folder_name = ""
	
	for off in xrange(file_info_off, filename_tab_off, 0xc):
		f.seek(off)
		fname_off = filename_tab_off + struct.unpack(">I", f.read(4))[0]
		foff, = struct.unpack(">I", f.read(4))
		fsize, = struct.unpack(">I", f.read(4))
	
		if fname_off & 0x1000000:
			fname_off -= 0x1000000
			f.seek(fname_off)
			sub_folder_name = read_0end_string(f)

			#print "sub_folder_name %s" % sub_folder_name
			continue
			
		#print "off= %x, fname_off = %x, %x, %x" % (off, fname_off, foff, fsize)
		
		f.seek(fname_off)
		fname = read_0end_string(f)
		#f.seek(fname_off)
		
		out_folder = os.path.join(out_dir, folder_name)
		if sub_folder_name:
			out_folder = os.path.join(out_folder, sub_folder_name)
		out_path = os.path.join(out_folder, fname)
		
		if not os.path.exists(out_folder):
			os.mkdir(out_folder)
		f.seek(foff)
		data = f.read(fsize)
		
		fout = open(out_path, "wb")
		fout.write(data)
		fout.close
		
		print "filename: %s, off=%x, size=%x" % (out_path, foff, fsize)
		
	f.close()
	os.system("del %s" % tmp_path)
	
def read_0end_string(f):
	fname = ""
	c = f.read(1)
	while c != "\0":
		fname += c
		c = f.read(1)
	return fname
	
if __name__ == "__main__":
	unpack(sys.argv[1], sys.argv[2])