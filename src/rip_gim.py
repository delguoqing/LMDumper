# $Id$
# -*- coding: gbk -*-
# A helper script for guessing and analyzing LM file format.

import struct
import sys
import optparse
import tag_reader

format = None

blend_mode_2_name = {
	0 : "normal",
	1 : "normal",
	2 : "layer",
	3 : "multiply",
	4 : "screen",
	5 : "lighten",
	6 : "darken",
	7 : "difference",
	8 : "add",
	9 : "subtract",
	10 : "invert",
	11 : "alpha",
	12 : "erase",
	13 : "overlay",
	14 : "hardlight",
}

align_2_name = {
	0: "left",
	1: "right",
	2: "center",
	3: "justify",
}

def set_format(_format):
	global format
	format = _format
	
def get_max_characterID(lm_data):
	v_list = list_tagF00C_symbol(lm_data)
	return v_list[3]
	
def read_tagF022(tag):

	res = tag_reader.read_tag(format.DATA[0xF022], tag)
	character_id = res["character_id"]
	unk1 = res["const0_0"] or 0
	assert unk1 == 0
	size_idx = res["size_idx"]
	f023_cnt = res["f023_cnt"]
	f024_cnt = res["f024_cnt"] or 0
	
	return character_id, unk1, size_idx, f023_cnt, f024_cnt

def read_tagF023(data):
	
	d = tag_reader.read_tag(format.DATA[0xF023], tag)
	uv_list = [
		d["x0"], d["y0"], d["u0"], d["v0"],
		d["x1"], d["y1"], d["u1"], d["v1"],
		d["x2"], d["y2"], d["u2"], d["v2"],
		d["x3"], d["y3"], d["u3"], d["v3"],
	]
	flag = d["fill_style"]
	idx = d["fill_idx"]
	
	return idx, uv_list
	
def iter_tag(lumen, type_set=None):
	lumen = lumen[0x40:]
	
	_type_set = type_set or ()
	off = 0x40
	
	while lumen:
	
		d = tag_reader.read_tag(format.DATA[0xFF00], lumen)
		tag_type, tag_size = d["tag_type"], d["tag_size"]
		tag_size_bytes = tag_size * 4 + format.HEADER_SIZE
		
#		assert tag_type in format.DATA, "Not Analyzed Tag!!! off=%x 0x%04x" % (off, tag_type)
		
		if not _type_set or tag_type in _type_set:
			yield off, tag_type, tag_size_bytes, lumen
		if tag_type == 0xFF00:
			break
			
		off += tag_size_bytes
		lumen = seek_next_tag(lumen)
		
def get_frame_label_dict(lm_data):
	ret = {}
	data = lm_data[0x40:]
	symbol_list = get_symbol_list(data)
	
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0x0027, 0x002b)):
		d = tag_reader.read_tag(format.DATA[tag_type], tag)
		
		if tag_type == 0x0027:
			sprite_id = d["character_id"]
			frame_label_cnt = d["frame_label_cnt"]
			ret.setdefault(sprite_id, {})
		elif tag_type == 0x002b:
			frame_label_idx, the_frame = d["name_idx"], d["frame_id"]
			frame_label = symbol_list[frame_label_idx]
			ret[sprite_id][frame_label] = the_frame + 1
	
	return ret
						
def get_symbol_list(tag):
	res = tag_reader.read_tag(format.DATA[0xF001], tag)
	ret = [symbol["symbol"] or "" for symbol in res["symbol_list"]]

	return ret

def seek_next_tag(data, id=None):
	assert data, "No Tags Any More"
	
	d = tag_reader.read_tag(format.DATA[0xFF00], data)
	tag_type, tag_size = d["tag_type"], d["tag_size"]
	data = data[tag_size * 4 + format.HEADER_SIZE:]
	
	# Has Next Tag?
	if len(data):
		d = tag_reader.read_tag(format.DATA[0xFF00], data)
		tag_type, tag_size = d["tag_type"], d["tag_size"]
	else:
		return data
		
	if id is None or tag_type in id:
		return data
	else:
		return seek_next_tag(data, id)
		
def tag_list(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data):
		print "tag:0x%04x, off=0x%x,\tsize=0x%x" % (tag_type, off, \
			tag_size_bytes)

def list_tag002b_symbol(lm_data):
	data = lm_data[0x40:]
	symbol_list = get_symbol_list(data)
	
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0x002b, )):
		d = tag_reader.read_tag(format.DATA[tag_type], tag)
		symbol_idx = d["name_idx"]
		frame = d["frame_id"]
		print "tag:0x%04x, off=0x%x,\tsize=0x%x,\t%s, frame=%x" % (tag_type, 
			off, tag_size_bytes, symbol_list[symbol_idx], frame)

def list_tag0027_symbol(lm_data, fname=""):
	data = lm_data[0x40:]
	symbol_list = get_symbol_list(data)
	
	ret = []
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0x0027, )):
		res = tag_reader.read_tag(format.DATA[0x0027], tag)

		characterID = res["character_id"]
		unk1, class_name_idx, frame_label_cnt = res["const0_0"], res["class_name_idx"], res["frame_label_cnt"]
		tag0001_cnt = res["0001_cnt"]
		key_frame_cnt = res["key_frame_cnt"]
		max_depth, unk2 = res["max_depth"], res["const1_0"]
		class_name = symbol_list[class_name_idx]
		
		unk1 = unk1 or 0
		unk2 = unk2 or 0
		
		ret.append((tag_type, off, tag_size_bytes, characterID, tag0001_cnt, frame_label_cnt, max_depth, class_name, key_frame_cnt, unk1, unk2))
		
#		assert unk1 == 0
#		assert text in range(15), fname
#		assert unk2 == 0
			
	return ret
	
def list_tagF022_symbol(lm_data, fname=""):
	bounding_box_list = list_tagF004_symbol(lm_data)
	ret = []
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF022, )):
		character_id, unk1, size_idx, f023_cnt, f024_cnt = read_tagF022(tag)
		box = bounding_box_list[size_idx]
		ret.append((tag_type, off, tag_size_bytes, character_id, f024_cnt, 
			f023_cnt, box[0], box[1], box[2], box[3]))
	return ret

def list_tagF024_img(lm_data):
	data = lm_data[0x40:]
	symbol_list = get_symbol_list(data)
	ori_pic_list = list_tagF007_symbol(lm_data)	
	off = 0x40
	
	tex_size_list = list_tagF004_symbol(lm_data)
	
	x_min = y_min = 1000000000000
	x_max = y_max = -1000000000000
	size = (x_min, y_min, x_max, y_max)
					
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF022, 0xF023, 0xF024)):
		
		if tag_type == 0xF022:

			BOUND_ERR_MSG = "texture boundary not match boundary table!"
			assert x_min >= size[0], BOUND_ERR_MSG
			assert y_min >= size[1], BOUND_ERR_MSG
	   		assert x_max <= size[2], BOUND_ERR_MSG
			assert y_max <= size[3], BOUND_ERR_MSG

			x_min = y_min = 1000000000000
   			x_max = y_max = -1000000000000			

			res = read_tagF022(tag)
			id = res[0]
			size_idx = res[2]
			size = tex_size_list[size_idx]
			print "CharacterID=%d, size: (%d, %d, %d, %d)" % (id, size[0], size[1], size[2], size[3])
					
		elif tag_type == 0xF024:
			d = tag_reader.read_tag(format.DATA[0xF023], tag)
			
			idx, flag, unk1, unk2 = d["fill_idx"], d["fill_stype"], d["unk1"], d["unk2"]
			
			fv_list = [
				d["x0"], d["y0"], d["u0"], d["v0"],
				d["x1"], d["y1"], d["u1"], d["v1"],
				d["x2"], d["y2"], d["u2"], d["v2"],
				d["x3"], d["y3"], d["u3"], d["v3"],	
			]
				
			unk3, unk4, unk5, unk6 = d["unk3"], d["unk4"], d["unk5"], d["unk6"]

			x_min = min(x_min, fv_list[0], fv_list[4], fv_list[8], fv_list[12])
			x_max = max(x_max, fv_list[0], fv_list[4], fv_list[8], fv_list[12])
			y_min = min(y_min, fv_list[1], fv_list[5], fv_list[9], fv_list[13])
			y_max = max(y_max, fv_list[1], fv_list[5], fv_list[9], fv_list[13])
				
			if flag == 0x41:
			
				ori_pic_list = list_tagF007_symbol(lm_data)
#				print ori_pic_list, idx
				ori_pic_fname_idx = ori_pic_list[idx][1]
				ori_pic_tga_idx = ori_pic_list[idx][0]
				sb = symbol_list[ori_pic_fname_idx]

				print "\ttag:0x%04x, off=0x%x,\tsize=0x%x,\tfill_img=%s" \
					% (tag_type, off, tag_size_bytes, sb)
				print "\t\t",fv_list[:4]
				print "\t\t",fv_list[4:8]
				print "\t\t",fv_list[8:12]
				print "\t\t",fv_list[12:]

			else:
				pass
				print "\ttag:0x%04x, off=0x%x,\tsize=0x%x,fill_color_idx=0x%x" \
					% (tag_type, off, tag_size_bytes,idx)
				print "\t\t",fv_list[:4]
				print "\t\t",fv_list[4:8]
				print "\t\t",fv_list[8:12]
				print "\t\t",fv_list[12:]			
				
			print "unk = 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x" % (unk1, unk2, unk3, unk4, unk5, unk6)
			
		if tag_type == 0xF023:
			
			d = tag_reader.read_tag(format.DATA[0xF023], tag)
			fv_list = [
						d["x0"], d["y0"], d["u0"], d["v0"],
						d["x1"], d["y1"], d["u1"], d["v1"],
						d["x2"], d["y2"], d["u2"], d["v2"],
						d["x3"], d["y3"], d["u3"], d["v3"],
						]
			flag, idx = d["fill_style"], d["fill_idx"]
			unk = d["const0_0"] or 0

			x_min = min(x_min, fv_list[0], fv_list[4], fv_list[8], fv_list[12])
			x_max = max(x_max, fv_list[0], fv_list[4], fv_list[8], fv_list[12])
			y_min = min(y_min, fv_list[1], fv_list[5], fv_list[9], fv_list[13])
			y_max = max(y_max, fv_list[1], fv_list[5], fv_list[9], fv_list[13])
				
			if flag in (0x41, 0x40):
			
				ori_pic_fname_idx = ori_pic_list[idx][1]
				ori_pic_tga_idx = ori_pic_list[idx][0]
				sb = symbol_list[ori_pic_fname_idx]
				if not sb:
					sb = "[TEXPACK_%d]" % ori_pic_list[idx][0]

				print "\ttag:0x%04x, off=0x%x,\tsize=0x%x,\tfill_img=%s" \
					% (tag_type, off, tag_size_bytes, sb)
				print "\t\t",fv_list[:4]
				print "\t\t",fv_list[4:8]
				print "\t\t",fv_list[8:12]
				print "\t\t",fv_list[12:]
				
			else:
				pass
				print "\ttag:0x%04x, off=0x%x,\tsize=0x%x,fill_color_idx=0x%x" \
					% (tag_type, off, tag_size_bytes, idx)
				print "\t\t",fv_list[:4]
				print "\t\t",fv_list[4:8]
				print "\t\t",fv_list[8:12]
				print "\t\t",fv_list[12:]			
			
			assert unk == 0
			
		elif tag_type == 0x0027:
			break
		elif tag_type == 0xFF00:
			break
	
# DefineButton	
def list_tag0007_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF00D, 0x0007, )):
		d = tag_reader.read_tag(format.DATA[tag_type], tag)
		if tag_type == 0xF00D:
			tag0007_cnt = d["0007_cnt"]
		elif tag_type == 0x0007:
			tag0007_cnt -= 1
			print "%x, %x, %x" % (d["unk2"], d["unk3"], d["unk5"], )
			if tag0007_cnt == 0:
				break
				
def list_tag0001_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0x0001,)):
		d = tag_reader.read_tag(format.DATA[0x0001], tag)
		print "tag:0x%04x, off=0x%x,\tsize=0x%x,\tframe=0x%x,\tsub_tag_cnt_cnt=%d" % \
			(tag_type, off, tag_size_bytes, d["frame_id"], d["cmd_cnt"])
	
def get_xref(lm_data):
	ref_table = {}
	data = lm_data[0x40:]
	symbol_list = get_symbol_list(data)
	off = 0x40
	
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0x0004,)):
		d = tag_reader.read_tag(format.DATA[tag_type], tag)
		id = d["character_id"]
		name_idx = d["name_idx"]
		if name_idx > 0:
			name = symbol_list[name_idx]
			name_set = ref_table.setdefault(id, set())
			name_set.add(name)
			ref_table[id] = name_set

	return ref_table
	
def list_tag0004_symbol(lm_data):
	ref_table = get_xref(lm_data)
	
	xy_list = list_tagF103_symbol(lm_data)
	data = lm_data[0x40:]
	symbol_list = get_symbol_list(data)
	color_list = list_tagF002_symbol(lm_data)
	as_list = list_tagF005_symbol(lm_data)
	matrix_list = list_tagF003_symbol(lm_data)

	for off, tag_type, tag_size_bytes, data in iter_tag(lm_data):
		d = tag_reader.read_tag(format.DATA[tag_type], data)
		if tag_type == 0x0027:
			d = tag_reader.read_tag(format.DATA[0x0027], data)
			id = d["character_id"]
			max_depth = d["max_depth"]
			print "===================== offset=0x%x, CharacterID=%d, max_depth=%d %s" % (off, id, max_depth, id in ref_table and "Ref As %s" % (",".join(list(ref_table[id]))) or "")
		elif tag_type == 0x0001:
			d = tag_reader.read_tag(format.DATA[0x0001], data)
			print "Frame %d, cmd_cnt=%d" % (d["frame_id"], d["cmd_cnt"])
		elif tag_type == 0xf014:
			d = tag_reader.read_tag(format.DATA[0xF014], data)		
			print ">>>>>>>>>Do ClipAction: %d" % d["as_idx"]
		elif tag_type == 0xf105:
			d = tag_reader.read_tag(format.DATA[0xF105], data)
			print ">>>>>>>>>KeyFrame: v=%d" % d["frame_id"]
		elif tag_type == 0x000c:
			print ">>>>>>>>>Do Action %d" % d["as_idx"]
		elif tag_type == 0x0005:
			d = tag_reader.read_tag(format.DATA[0x0005], data)
			print ">>>>>>>>>RemoveObject at depth%d" % d["depth"]

			assert d["unk1"] == 0
			assert d["unk0"] == 0 or d["unk0"] is None
			assert d["depth"] < max_depth
		elif tag_type == 0x002b:
			d = tag_reader.read_tag(format.DATA[0x002B], data)
			print ">>>>>>>>>FrameLabel: %s@%d" % (symbol_list[d["name_idx"]], d["frame_id"])
			assert d["unk0"] == 0
		if tag_type == 0x0004:
			res = tag_reader.read_tag(format.DATA[0x0004], data)
			
			character_id = res["character_id"]
			inst_id = res["inst_id"]
			unk1, name_idx = res["unk1"], res["name_idx"]
			flags, blend_mode, = res["flags"], res["blend_mode"]
			depth, clip_depth, ratio, unk5 = res["depth"], res["clip_depth"], res["ratio"], res["unk5"]
			trans_idx, color_mul_idx ,color_add_idx, unk6, clip_action_cnt = res["trans_idx"], res["color_mul_idx"], res["color_add_idx"], res["unk6"], res["clip_action_cnt"]

			blend_mode_name = blend_mode_2_name[blend_mode]
			if trans_idx == -1:
				translate = scale = rotateskew = "null"
			elif trans_idx >= 0:
				translate = "(%.1f, %.1f)" % (matrix_list[trans_idx][4],
					matrix_list[trans_idx][5])
				scale = "(%.1f, %.1f)" % (matrix_list[trans_idx][0],
					matrix_list[trans_idx][3])
				rotateskew = "(%.1f, %.1f)" % (
					matrix_list[trans_idx][1], 
					matrix_list[trans_idx][2])
			else:	# tricky!!!, find the first 0x8
					# TODO: need to fix this!
				trans_idx = trans_idx & 0xFFFFFFFF
				bit_cnt = 28
				while True:
					old_trans_idx = trans_idx
					trans_idx ^= (0xF << bit_cnt)
					if (old_trans_idx & (0xF << bit_cnt)) == (0x8 << bit_cnt):
						trans_idx = (old_trans_idx ^ (0x8 << bit_cnt))
						break
					bit_cnt -= 4
				translate = "(%.1f, %.1f)" % xy_list[trans_idx]
				scale = rotateskew = ""
			if name_idx >= 0:
				name = symbol_list[name_idx]
			else:
				name = ""

			flags_str = ""
			flags_str += (flags & 0x1) and "N" or "-"
			flags_str += (flags & 0x2) and "M" or "-"
			if flags & (~0x3) != 0:
				assert False, "==============#new flags ! 0x%x " % flags

			if color_mul_idx < 0:
				color_mul_str = ""
			else:
				color_mul = color_list[color_mul_idx]
				color_mul_str = "(%.1f,%.1f,%.1f,%.1f)" % tuple([c/256.0 for c in color_mul])
			if color_add_idx < 0:
				color_add_str = ""
			else:
				color_add = color_list[color_add_idx]
				color_add_str = "(%d,%d,%d,%d)" % tuple(color_add)

			print "PlaceObject, off=0x%x,\tsize=0x%x" % (off, tag_size_bytes)
			print ("\tID=%d,\tdepth=%d,\tpos=%s,\tscale=%s,\tskew=%s,\tInstID=%d," \
				+"\tflags=%s,\tcolMul=%s,\tcolAdd=%s,\tclipAction=%d,\tname=%s,\tratio=%d\tblend_mode=%s\tclip_depth=%d") % \
				(character_id, depth, translate, scale, rotateskew, inst_id,
					flags_str, color_mul_str, color_add_str, clip_action_cnt, name, ratio, blend_mode_name, clip_depth)

#			assert unk1 == 0 and unk5 == 0 and unk6 == 0
			
		if tag_type == 0xFF00:
			break
		off += tag_size_bytes
		data = data[tag_size_bytes:]
#
#	print "{{{{{{{{{{{{{{{{{{{{{{{{{{{"
#	for k, v in sorted(off0x4_cnt.items()):
#		print "\t%x:%d" % (k, v)
#	print "}}}}}}}}}}}}}}}}}}}}}}}}}}}"		

def list_tagF103_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF103,)):
		res = tag_reader.read_tag(format.DATA[0xF103], tag)
		pos_list = [(pos["x"], pos["y"]) for pos in res["pos_list"]]
		return pos_list
	assert False, "Missing tag F103"

def list_tagF004_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF004,)):
		res = tag_reader.read_tag(format.DATA[0xF004], tag)
		box_list = [(box["xmin"], box["ymin"], box["xmax"], box["ymax"]) for box in res["box_list"]]
		return box_list
	assert False, "Missing tag F004"
		
def list_tagF00C_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF00C,)):
		res = tag_reader.read_tag(format.DATA[0xF00C], tag)

		assert res["v"] == 0 and res["e"] == 1 and res["r"] == 2
		assert res["max_character_id"] == res["start_character_id"]
		assert res["reserved"] == -1
		assert res["reserved2"] == 0
		
		return res
	assert False, "Missing tag F00C"
			
def list_tagF008_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF008,)):
		res = tag_reader.read_tag(format.DATA[0xF008], tag)
		return
	assert False, "Missing tag F008"

def list_tagF009_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF009,)):
		res = tag_reader.read_tag(format.DATA[0xF009], tag)
		assert res["unk"] == 0
		return		
	assert False, "Missing tag F009"
	
def list_tagF00A_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF00A,)):
		res = tag_reader.read_tag(format.DATA[0xF00A], tag)
		return		
	assert False, "Missing tag F00A"

def list_tag000A_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0x000A,)):
		res = tag_reader.read_tag(format.DATA[0x000A], tag)
		return res
	assert False, "Missing tag 000A"

def list_tag000C_symbol(lm_data):
	as_list = list_tagF005_symbol(lm_data)
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0x000C,)):
		res = tag_reader.read_tag(format.DATA[0x000C], tag)
#		assert res["unk1"] == 0, "%d" % res["unk1"]
		assert res["unk0"] < len(as_list)
		
def list_tagF00B_symbol(lm_data):

	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF00B,)):
		res = tag_reader.read_tag(format.DATA[0xF00B], tag)
		assert res["unk"] == 1
		return		
	assert False, "Missing tag F00B"
				
def list_tagF007_symbol(lm_data):
	symbol_list = get_symbol_list(lm_data[0x40:])
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF007,)):
		res = tag_reader.read_tag(format.DATA[0xF007], tag)
		image_list = []
		for image_info in res["img_list"]:
			if symbol_list[image_info["name_idx"]] == "":
				fname = "noname_0x%x.png" % (image_info["img_idx"], )
			else:
				fname = symbol_list[image_info["name_idx"]]
			image_list.append((image_info["img_idx"], image_info["name_idx"], image_info["width"], image_info["height"], fname))
		return image_list
	assert False, "Missing tag F007"
						
def list_tagF005_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF005,)):
		res = tag_reader.read_tag(format.DATA[0xF005], tag)
		as_list = []
		off = 0xc
		idx = 0
		for abc in res["as_list"]:
			as_list.append((off+0x4, abc["as_len"]))
#			print "%x\toff=0x%x len=0x%x" % ((idx, ) + as_list[-1])
			abc["padding"] = abc["padding"] or ""
			off += 0x4 + abc["as_len"] + len(abc["padding"])
			idx += 1

		as_list = [(abc["as_len"], abc["bytecode"]) for abc in res["as_list"]]
		return as_list
	assert False, "Missing tag F005"

def list_tagF002_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF002,)):
		res = tag_reader.read_tag(format.DATA[0xF002], tag)
		color_list = [(color["R"], color["G"], color["B"], color["A"]) for color in res["color_list"]]
		return color_list
	assert False, "Missing tag F002"
			
def list_tagF003_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF003,)):
		res = tag_reader.read_tag(format.DATA[0xF003], tag)
		mat_list = [(mat["trans_x"], mat["trans_y"], mat["rotateskew_x"], mat["rotateskew_y"], mat["scale_x"], mat["scale_y"]) for mat in res["mat_list"]]
		return mat_list
	assert False, "Missing tag F003"
					
def list_tagF00D_symbol(lm_data):
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF00D,)):
		res = tag_reader.read_tag(format.DATA[0xF00D], tag)
#		assert res["unk6"] in (0, ), "%d" % res["unk6"]
		
		return res
		
def list_tag0025_symbol(lm_data):
	data = lm_data[0x40:]
	symbol_list = get_symbol_list(data)
	
	box_list = list_tagF004_symbol(lm_data)
	
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data, (0xF00D, 0x0025)):
		d = tag_reader.read_tag(format.DATA[tag_type], tag)
		if tag_type == 0xF00D:
			tag0025_cnt = d["0025_cnt"]
		elif tag_type == 0x0025:
			tag0025_cnt -= 1
			assert d["max_length"] == 0xFFFF
			assert d["unk0"] == 0
		
			# A neat print for all known fields of tag 0x0025
			# --- edit text flags

			box = box_list[d["rect_idx"]]
			var_name = symbol_list[d["var_name_idx"]]
			init_text = symbol_list[d["init_txt_idx"]]
			font_class_name = symbol_list[d["font_class_name_idx"]]
			align = align_2_name[d["align"]]
			
			print "ID=%d, rect:(%.2f, %.2f, %.2f, %.2f), font_size=%.2f, spacing=(%.2f, %.2f, %.2f, %.2f), var=%s, init_text=%s, align=%s, max_length=0x%04x, font_id=%d, font_class=%s" % ((d["character_id"],) + tuple(box) + (d["font_size"], d["left_margin"], d["right_margin"], d["indent"], d["leading"], var_name, init_text, align, d["max_length"], d["font_id"], font_class_name))
			
		if tag0025_cnt == 0:
			break
	
if __name__ == "__main__":
	
	parser = optparse.OptionParser()
	parser.add_option("-f", dest="filename")
	parser.add_option("-o", dest="outfile")
	parser.add_option("-t", action="store_true", dest="print_tag")
	parser.add_option("-i", type="int", action="store", dest="tag_id")
	parser.add_option("-P", action="store", dest="platform", type="string", default="wii", help="specify the platform where the LM file come from!(wii or pspdx)")
	
	(options, args) = parser.parse_args(sys.argv)
	
	# set up the global format file
	if options.platform == "wii":
		import format.lm_format_wii as format
	elif options.platform == "pspdx":
		import format.lm_format_pspdx as format
	else:
		print "An unknown platform name!"
		sys.exit()
		
	if not options.filename:
		print "No filename is specified!"

	elif options.print_tag:		# print tag info in LM file
		f = open(options.filename, "rb")
		data = f.read()
		f.close()
		
		if options.tag_id is None:
			tag_list(data)
		elif options.tag_id == 0x002b:
			list_tag002b_symbol(data)
		elif options.tag_id == 0x0027 or options.tag_id == 0xF022:
			res = list_tagF022_symbol(data)
			for arg in res:
				print ("tag:0x%04x off=0x%x,\tsize=0x%x,\tCharacterID=%d," + \
				"\tf024_cnt=%d,f023_cnt=%d\n\tbox=(%.2f,%.2f,%.2f,%.2f)\n") \
				 % arg
			print "==============="
			res = list_tag0027_symbol(data)
			for arg in res:
				print "tag:0x%04x, off=0x%x,\tsize=0x%x,\tCharacterID=%d\tframe=%d,\tlabel=%d,\tmaxdepth=0x%x,class_name=%s,key_frame_cnt=%d,unk=%d, %d" % arg
		elif options.tag_id == 0xF023:
#			for off in range(0, 0x48, 2):
#				print "off %x~%x" % (off, off+2)
#				list_tagF023_symbol(data, off, off+2)
			list_tagF023_img(data)

		elif options.tag_id == 0x0001:
			list_tag0001_symbol(data)
		elif options.tag_id == 0x0004:
			list_tag0004_symbol(data)
		elif options.tag_id == 0x0007:
			list_tag0007_symbol(data)
		elif options.tag_id == 0xF103:
			xy_list = list_tagF103_symbol(data)
			if xy_list:
				print "point list:"
				for i, point in enumerate(xy_list):
					print "0x%x\t" % i, point
		elif options.tag_id == 0xF001:
			f = open(options.filename, "rb")
			data = f.read()
			f.close()
		
			tag = data[0x40:]
			symbol_list = get_symbol_list(tag)
			print "symbols:"
			for i, symbol in enumerate(symbol_list):
				print "0x%x\t" % i, symbol			
		elif options.tag_id == 0xF002:
			color_list = list_tagF002_symbol(data)
			if color_list:
				print "color list:"
				for i, color in enumerate(color_list):
					print "0x%x\t" % i, color				
		elif options.tag_id == 0xF003:
			matrix_list = list_tagF003_symbol(data)
			if matrix_list:
				print "matrix list:"	
				for i, v in enumerate(matrix_list):
					print "0x%x\t[%.3f, %.3f, %.3f, %.3f, %.3f, %.3f]" % ((i,)+v)			
		elif options.tag_id == 0xF004:
			res = list_tagF004_symbol(data)
			print "Bounding Box Info:"
			for i, v in enumerate(res):
				print "0x%x\t" % i, v	
		elif options.tag_id == 0xF005:
			res = list_tagF005_symbol(data)
			print "Actionscript:"
			for i, (as_len, bytecode) in enumerate(res):
				print "%x:\tsize=0x%x" % (i, as_len)
		elif options.tag_id == 0xF007:
			v_list = list_tagF007_symbol(data)
			print "img file info:"
			for v in v_list:
				print "\timg_idx=%d, width=%.2f, height=%.2f, fname=%s" % \
					(v[0], v[2], v[3], v[4].decode("utf8"))
		elif options.tag_id == 0xF008:
			list_tagF008_symbol(data)
		elif options.tag_id == 0xF009:
			list_tagF009_symbol(data)			
		elif options.tag_id == 0xF00A:
			list_tagF00A_symbol(data)				
		elif options.tag_id == 0xF00B:
			list_tagF00B_symbol(data)					
		elif options.tag_id == 0xF00C:
			color_list = list_tagF002_symbol(data)
			res = list_tagF00C_symbol(data)
			
			print "Stage info:"
			print "ver = %d%d%d" % (res["v"], res["e"], res["r"])
			print "max/start character id = %d" % res["max_character_id"]
			print "stage size (%.2f, %.2f), pos=(%.2f, %.2f), fps = %.2f" % (res["width"], res["height"], res["x"], res["y"], res["fps"])
			print "UNKNOWN unk = %d" % res["unk"]
			print "reserved = %d, reserved2 = %d" % (res["reserved"], res["reserved2"])
			
		elif options.tag_id == 0xF00D:
			res = list_tagF00D_symbol(data)
			print "\tF022:%d, 0027:%d" % (res["f022_cnt"], res["0027_cnt"])			
		elif options.tag_id == 0x0025:
			res = list_tag0025_symbol(data)
		elif options.tag_id == 0xF024:
			res = list_tagF024_img(data)
		elif options.tag_id == 0x000A:
			res = list_tag000A_symbol(data)
			print "font count = %d" % res["unk_cnt"]
