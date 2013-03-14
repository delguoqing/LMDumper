import sys
import optparse
import glob
import os

parser = optparse.OptionParser()
parser.add_option("-f", dest="filename")
	
(options, args) = parser.parse_args(sys.argv)

os.system("TPL2TGA.exe %s" % options.filename)
for tga_file in glob.glob("*.tga"):
	fname = os.path.split(tga_file)[1]
	beg = fname.find("#")
	end = fname.find("_")
	idx = int(fname[beg+1: end])
	os.system("convert.exe %s noname_%d.png" % (tga_file, idx))
	
os.system("del *.tga")