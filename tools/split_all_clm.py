import glob
import os
import lz77
import split_clm
from TPL2PNG import image

for dir_path, dir_names, filenames in os.walk("lm"):
	for filename in filenames:
		file_path = os.path.join(dir_path, filename)
		out_folder = os.path.splitext(file_path)[0]
		
		print "Doing %s | %s" % (dir_path, filename)

		if filename.endswith(".lm"):
			continue
		if filename.endswith(".tpl"):
			image.TPL(file_path).toImage(dir_path)
			os.system("del %s" % file_path)
			continue
			
		assert filename.endswith(".lma"), filename
		
		
		if not os.path.exists(out_folder):
			os.mkdir(out_folder)
		
		f = open(file_path, "rb")
		data = f.read()
		f.close()
	
		finfo_list = split_clm.split(data)
		for fname, off, size in finfo_list:
			fout = open(os.path.join(out_folder, fname), "wb")
			fout.write(data[off: off+size])
			fout.close()
			
		os.system("del %s" % file_path)