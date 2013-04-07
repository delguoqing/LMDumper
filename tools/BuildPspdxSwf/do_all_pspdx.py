import os
import glob

split = os.path.split
splitext = os.path.splitext
for filename in glob.glob(r"C:\Users\delguoqing\Documents\GitHub\LMDumper\lm\pspdx\*.LM"):
	outfilename = splitext(split(filename)[1])[0] + ".swf"
	os.system(r"""python C:\Users\delguoqing\Documents\GitHub\LMDumper\src\dumper.py -P pspdx -f %s -t C:\png -o C:\Users\delguoqing\Documents\GitHub\LMDumper\src\tmp\%s""" % (filename, outfilename))
	