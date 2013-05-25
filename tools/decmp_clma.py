import glob
import os
import lz77

def decomp(file_path):
	f = open(file_path,"rb")
	
	unc = lz77.WiiLZ77(f, f.tell())
	 
	du = unc.uncompress()

	f2 = open(file_path[:-4] + ".lma", "wb")
	f2.write(du)
	f2.close()

for dir_path, dir_names, filenames in os.walk("lm"):
	for filename in filenames:
		file_path = os.path.join(dir_path, filename)
		if filename.endswith("..lma"):
			os.system("ren %s %s" % (file_path, filename[:-4] + "lma"))
		elif not filename.endswith(".clma"):
			assert filename.endswith("lma")
			continue
		else:
			os.system("del %s" % file_path)
		#decomp(os.path.join(dir_path, filename))
		#os.system("del %s" % os.path.join(dir_path, filename))
	