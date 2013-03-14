# -*- coding: gbk -*-
import sys
import struct
import os
import optparse
import swf_helper
import as_fixer
import tag_reader

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
		
def iter_tag(lumen, type_set=None):
	lumen = lumen[0x40:]
	
	_type_set = type_set or ()
	off = 0x40
	
	while lumen:
	
		d = tag_reader.read_tag(format.DATA[0xFF00], lumen)
		tag_type, tag_size = d["tag_type"], d["tag_size"]
		tag_size_bytes = tag_size * 4 + format.HEADER_SIZE
		
		assert tag_type in format.DATA, "Not Analyzed Tag!!! off=%x 0x%04x" % \
			(off, tag_type)
		
		if not _type_set or tag_type in _type_set:
			yield off, tag_type, tag_size_bytes, lumen
		if tag_type == 0xFF00:
			break
			
		off += tag_size_bytes
		lumen = seek_next_tag(lumen)
		
def make_imgs(ctx):
	img_idx_2_cid = {}
	img_tags = []
	img_info_list = ctx["img_info_list"]
	symbol_list = ctx["symbol_list"]
	root = ctx["img_root"]
	
	for i, img_info in enumerate(img_info_list):
		# fix image name
		if img_info["name_idx"] < len(symbol_list):
			fname = symbol_list[img_info["name_idx"]]
		else:
			fname = ""
		if fname == "":
			fname = "noname_%d.png" % img_info["img_idx"]
		# remove blend mode suffix in filename
		# e.g: xyz.png__BLEND_ADD__ ---> xyz.png		
		idx = fname.rfind(".png")
		fname = fname[:idx] + ".png"
		
		# store image data in a dict
		try:
			f = open(os.path.join(root, fname), "rb")
			image_data = f.read()
			f.close()
		except IOError:
			fname = "noname_%d.png" % img_info["img_idx"]
			f = open(os.path.join(root, fname), "rb")
			image_data = f.read()
			f.close()
		
		cid = ctx["last_cid"]
		ctx["last_cid"] += 1
		tag = swf_helper.make_define_bits_JPEG2_tag(cid, image_data)
		img_tags.append(tag)
		img_idx_2_cid[i] = cid
		
	return img_idx_2_cid, img_tags
	
def _make_shape(ctx, d):
	assert d["tag_type"] in (0xf023, 0xf024), "unknown shape define tag!"
	
	fv_list = [
		d["x0"], d["y0"], d["u0"], d["v0"],
		d["x1"], d["y1"], d["u1"], d["v1"],
		d["x2"], d["y2"], d["u2"], d["v2"],
		d["x3"], d["y3"], d["u3"], d["v3"],	
	]
	fill_style, fill_idx = d["fill_style"], d["fill_idx"]
	img_idx_2_cid = ctx["img_idx_2_cid"]
	color_list = ctx["color_list"]
	img_info_list = ctx["img_info_list"]

	xs = fv_list[::4]
	ys = fv_list[1::4]
	xmin, xmax = min(xs), max(xs)
	ymin, ymax = min(ys), max(ys)
	width = int(xmax - xmin)
	height = int(ymax - ymin)
				
	shape_id = ctx["last_cid"]
	if fill_style == 0x0:
		c = color_list[fill_idx]
		color = swf_helper.pack_color((c["R"], c["G"], c["B"], c["A"]))
		tag = make_define_shape3_tag_solid_simple(shape_id, width, height, color)
	elif fill_style in (0x40, 0x41):
		bitmap_id = img_idx_2_cid[fill_idx]
		tag = swf_helper.make_define_shape3_tag_bitmap_simple(shape_id, bitmap_id, width, height, fill_style)
	else:
		assert False, "unsupported fill style type. 0x%x" % fill_style
	ctx["last_cid"] += 1
		
	return tag, shape_id

def make_tex_sprite(ctx, d, subds):
	sprite_id = d["character_id"]
	sub_tags = []

	for i, subd in enumerate(subds):
		shape_tag, shape_id = _make_shape(ctx, subd)
		xmin = min(subd["x0"], subd["x1"], subd["x2"], subd["x3"])
		ymin = min(subd["y0"], subd["y1"], subd["y2"], subd["y3"])
		matrix = swf_helper.pack_matrix(None, None, (xmin, ymin))
		place_obj2_tag = swf_helper.make_place_object2_tag(swf_helper.PLACE_FLAG_HAS_CHARACTER | swf_helper.PLACE_FLAG_HAS_MATRIX, i+1, id=shape_id, matrix=matrix)
		sub_tags.append(place_obj2_tag)
		ctx.setdefault("shape_tags", []).append(shape_tag)
	show_frame_tag = swf_helper.make_show_frame_tag()
	sub_tags.append(show_frame_tag)
	sub_tags.append(swf_helper.make_end_tag())
	
	return swf_helper.make_define_sprite_tag(sprite_id, 1, sub_tags)
	
def make_normal_sprite(ctx, d, subds):
	color_list = ctx["color_list"]
	point_list = ctx["pos_list"]
	matrix_list = ctx["mat_list"]
	symbol_list = ctx["symbol_list"]
	as_list = ctx["as_list"]
	
	frame_label_cnt = d["frame_label_cnt"]
	frame_cnt = d["0001_cnt"]
	sprite_id = d["character_id"]
#	print "sprite id = %d" % sprite_id
	frame_label_dict = {}
	
	# build a frame label dict for later ref	
	for subd in subds[:frame_label_cnt]:
		assert subd["tag_type"] == 0x002B
		frame_id = subd["frame_id"]
		frame_label = symbol_list[subd["name_idx"]]
		frame_label_dict[frame_id] = frame_label
		
#	print "frame_label_cnt = %d" % frame_label_cnt
	# handle the rest, all the frames
	sub_tags = []
	depth2matrix = {}
	depth2color_trans = {}
	clip_action_cnt = -1
	frame_cmd_cnt = -1
	for subd in subds[frame_label_cnt:]:
	
		# finish all clip_action tags, pack place object2 tag
		if clip_action_cnt == 0:
			if len(clip_action_records) > 0:
				flags |= swf_helper.PLACE_FLAG_HAS_CLIP_ACTIONS
				clip_actions = \
					swf_helper.pack_clip_actions(clip_action_records)
			else:
				clip_actions = None
				
			ptag = swf_helper.make_place_object2_tag(flags, depth + 1, id, 
				name=name, matrix=matrix, color_trans=color_trans, clip_actions=clip_actions, ratio=ratio, clip_depth=clip_depth)
			sub_tags.append(ptag)
			
			clip_action_cnt = -1
					
		if frame_cmd_cnt == 0:
			sub_tags.append(swf_helper.make_show_frame_tag())
			frame_cmd_cnt = -1
			
		if subd["tag_type"] == 0x0001:
			frame_cmd_cnt = subd["cmd_cnt"]
			frame_id = subd["frame_id"]
			frame_label = frame_label_dict.get(frame_id, None)
			if frame_label is not None:
				frame_label_tag = swf_helper.make_frame_label_tag(frame_label)
				sub_tags.append(frame_label_tag)
			
		elif subd["tag_type"]	== 0x0005:
			sub_tags.append(swf_helper.make_remove_object2_tag(
				subd["depth"] + 1))
			frame_cmd_cnt -= 1
		elif subd["tag_type"] == 0x000c:
			global format
			bytecodes = as_list[subd["as_idx"]]["bytecode"]
			bytecodes = as_fixer.fix(bytecodes, symbol_list, format)
			sub_tags.append(swf_helper.make_do_action_tag([bytecodes]))
			frame_cmd_cnt -= 1
		elif subd["tag_type"] == 0xf014:

			clip_action_cnt -= 1
			bytecodes = as_fixer.fix(as_list[subd["as_idx"]["bytecode"]], symbol_list, format)
			event_flags = subd["event_flags"]
			keycode = 0
			clip_action_records.append(
				swf_helper.pack_clip_action_record(event_flags, [bytecodes], keycode))
					
		elif subd["tag_type"] != 0x0004:
			assert False, "unhandled tag! %d" % subd["tag_type"]

		else:	# handle tag0004
			frame_cmd_cnt -= 1
			_flags = subd["flags"]
			flags = 0
			if _flags & 1:
				flags |= swf_helper.PLACE_FLAG_HAS_CHARACTER
			if _flags & 2:
				flags |= swf_helper.PLACE_FLAG_MOVE
			id = subd["character_id"]
#			print "sub character id = %d" % id
			trans_idx = subd["trans_idx"]
			if trans_idx == -1:
				pass
			elif trans_idx >= 0:
				translate = (matrix_list[trans_idx]["trans_x"],
					matrix_list[trans_idx]["trans_y"])
				scale = (matrix_list[trans_idx]["scale_x"],
					matrix_list[trans_idx]["scale_y"])
				rotateskew = (matrix_list[trans_idx]["rotateskew_x"], 
					matrix_list[trans_idx]["rotateskew_y"])
				flags |= swf_helper.PLACE_FLAG_HAS_MATRIX
			else:
				fdef = format.DATA[0x0004]
				size = 0
				for vname, size, fmt in fdef:
					if vname == "trans_idx":
						break
				mask = (1 << (size * 8 - 1))-1
				trans_idx &= mask
				translate = point_list[trans_idx]["x"], point_list[trans_idx]["y"]
				scale = rotateskew = None
				flags |= swf_helper.PLACE_FLAG_HAS_MATRIX
			if flags & swf_helper.PLACE_FLAG_HAS_MATRIX:
				matrix = swf_helper.pack_matrix(scale, rotateskew, 
					translate)
			else:
				matrix = None
			depth = subd["depth"]
			name_idx = subd["name_idx"]
			name = symbol_list[name_idx]
			if name != "":
				flags |= swf_helper.PLACE_FLAG_HAS_NAME
			color_mul_idx = subd["color_mul_idx"]
			color_add_idx = subd["color_add_idx"]

			if color_mul_idx >= 0 or color_add_idx >= 0:
				flags |= swf_helper.PLACE_FLAG_HAS_COLOR_TRANSFORM
			if color_mul_idx < 0:
				color_mul = None
			else:
				c = color_list[color_mul_idx]
				color_mul = [c["R"]/256.0, c["G"]/256.0, c["B"]/256.0, c["A"]/256.0]
			if color_add_idx < 0:
				color_add = None
			else:
				c = color_list[color_add_idx]
				color_add = [c["R"], c["G"], c["B"], c["A"]]
			if flags & swf_helper.PLACE_FLAG_HAS_COLOR_TRANSFORM:
				color_trans = \
					swf_helper.pack_color_transform_with_alpha(
						color_add, color_mul)
			else:
				color_trans = None
			
			if matrix:
				depth2matrix[depth] = matrix
			if color_trans:
				depth2color_trans[depth] = color_trans
				
			clip_depth = subd["clip_depth"]
			if clip_depth > 0:
				flags |= swf_helper.PLACE_FLAG_HAS_CLIP_DEPTH
				
			ratio = subd["inst_id"]	# Not sure??
			if ratio >= 0:
				flags |= swf_helper.PLACE_FLAG_HAS_RATIO

			if flags & swf_helper.PLACE_FLAG_HAS_CHARACTER and \
				flags & swf_helper.PLACE_FLAG_MOVE:
				sub_tags.append(swf_helper.make_remove_object2_tag(depth + 1))
				flags &= (0xFFFF - swf_helper.PLACE_FLAG_MOVE)
				if not (flags & swf_helper.PLACE_FLAG_HAS_MATRIX):
					flags |= swf_helper.PLACE_FLAG_HAS_MATRIX
					matrix = depth2matrix[depth]
			
			clip_action_cnt = subd["clip_action_cnt"]
			clip_action_records = []

	sub_tags.append(swf_helper.make_end_tag())	
	return swf_helper.make_define_sprite_tag(sprite_id, frame_cnt, sub_tags)
	
def dump(fname, ID, label, pos, scale, fout, img_path, norecreate):
	
	image_root = img_path or r"c:\png"

	f = open(fname, "rb")
	lm_data = f.read()
	f.close()
	
	fout = fout or fname[:-3] + ".swf"
	if norecreate and os.path.exists(fout):
		return
	
	ctx = {"tags": [], "img_root": image_root, "tex_sprite": [], "normal_sprite": [], }
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data):
		d = tag_reader.read_tag(format.DATA[tag_type], tag)
		if d["tag_type"] == 0xF001:
			ctx["symbol_list"] = []
			for symbol_info in d["symbol_list"]:
				ctx["symbol_list"].append(symbol_info["symbol"])
			if ctx["symbol_list"][0] is None:
				ctx["symbol_list"][0] = ""
		elif d["tag_type"] == 0xF002:
			ctx["color_list"] = d["color_list"]
		elif d["tag_type"] == 0xF007:
			ctx["img_info_list"] = d["img_list"]
		elif d["tag_type"] == 0xF103:
			ctx["pos_list"] = d["pos_list"]
		elif d["tag_type"] == 0xF003:
			ctx["mat_list"] = d["mat_list"]
		elif d["tag_type"] == 0xF005:
			ctx["as_list"] = d["as_list"]
		elif d["tag_type"] == 0xF00C:
			ctx["max_character_id"] = d["max_character_id"]
		elif d["tag_type"] == 0xF022:
			ctx["tex_sprite"].append([d])
		elif d["tag_type"] in (0xF023, 0xF024):
			ctx["tex_sprite"][-1].append(d)
		elif d["tag_type"] == 0x0027:
			ctx["normal_sprite"].append([d])
		elif d["tag_type"] in (0x0001, 0x0004, 0x0005, 0x002b, 0xf014, 0x000c):
			ctx["normal_sprite"][-1].append(d)
		
		
	max_characterID = ctx["max_character_id"]
	ctx["last_cid"] = max_characterID + 1
	
	# all tags append to this list
	all_tags = []
	
	# make FileAttributes tag
	all_tags.append(swf_helper.make_file_attributes_tag())
	
	# make SetBackgroundColor tag
	all_tags.append(swf_helper.make_set_background_color_tag(0xFF, 0xFF, 0xFF))

	# make all DefineBitsJPEG2 tags
	ctx["img_idx_2_cid"], img_tags = make_imgs(ctx)
	all_tags.extend(img_tags)
	
	# make all Texture sprite tags
	tex_sprite_tags = []
	for data in ctx["tex_sprite"]:
		tex_sprite_tags.extend(make_tex_sprite(ctx, data[0], data[1:]))

	# make all DefineShape tags
	all_tags.extend(ctx["shape_tags"])
	all_tags.extend(tex_sprite_tags)
		
	# make all normal sprite tags
	for data in ctx["normal_sprite"]:
		all_tags.extend(make_normal_sprite(ctx, data[0], data[1:]))	
			
	# test basic display
	tmp_tags = []
	
	id = ID or max_characterID
	tmp_tags.append(swf_helper.make_place_object2_tag(swf_helper.PLACE_FLAG_HAS_CHARACTER|swf_helper.PLACE_FLAG_HAS_MATRIX|swf_helper.PLACE_FLAG_HAS_NAME|swf_helper.PLACE_FLAG_HAS_RATIO, 1, id=id, matrix=swf_helper.pack_matrix(scale and (scale, scale) or None, None, pos or (0, 0), ),name="main",ratio=0xFFFF))

	if label is not None:
		action_records = []
		action_records.append("\x8B\x05\x00main\x00")   # ActionSetTarget "main"
		frame_idx = frame_label_dict[id][label]
		action_records.append("\x81\x02\x00" + struct.pack("<H", frame_idx))
		action_records.append("\x06")
		action_records.append("\x8B\x01\x00")
		tmp_tags.append(swf_helper.make_do_action_tag(action_records))		
	
	tmp_tags.append(swf_helper.make_show_frame_tag())
	
	all_tags.extend(tmp_tags)
	
	# make end tag
	end_tag = swf_helper.make_end_tag()
	all_tags.append(end_tag)
	
	# build swf header
	all_data = ""
	for tag in all_tags:
		all_data += tag
		
	swf_header = swf_helper.make_swf_header(0xa, 0, 480, 272, 60.0, 1)
	file_length = len(swf_header) + len(all_data)
	swf_header = swf_helper.make_swf_header(0xa, file_length, 480, 272, 60.0, 
		1)
	
	fout = open(fout, "wb")
	fout.write(swf_header + all_data)
	fout.close()
	
if __name__ == "__main__":
	parser = optparse.OptionParser()
	parser.add_option("-f", dest="filename", help="LM file path")
	parser.add_option("-o", dest="fout", help="output file path")
	parser.add_option("-t", dest="texture_root", help="where your png files are.")
	parser.add_option("-l", dest="label", help="framelabel of the sprite.")
	parser.add_option("-i", type="int", action="store", dest="characterID", help="ID of the character to be placed on the stage.")
	parser.add_option("-p", type="float", nargs=2, dest="pos", help="postion of the sprite. example: -p 128 128")
	parser.add_option("-s", type="float", dest="scale", help="the scale of the sprite")
	parser.add_option("-d", action="store_true", dest="dry_run", help="show all character IDs and their frame labels.")
	parser.add_option("-I", action="store_true", dest="norecreate", help="Ignore a file when the corresponding swf is already exists!")
	parser.add_option("-P", action="store", type="string", dest="platform", default="wii", help="specify platform: wii or pspdx, default: wii")

	(options, args) = parser.parse_args(sys.argv)
	
	if options.platform == "wii":
		import format.lm_format_wii as format
	elif options.platform == PLATFORM_PSPDX:
		import format.lm_format_pspdx as format
	else:
		print "Unsupported platform!"
		os.exit()
		
	if os.path.isdir(options.filename):
		def is_LM(filename):
			return filename.upper().endswith(".LM")
		def join_filename(filename):
			return os.path.join(options.filename, filename)
		filenames = map(join_filename, filter(is_LM, os.listdir(options.filename)))
	else:
		filenames = (options.filename,)
	
	for filename in filenames:
		print "Doing %s:" % filename
		if options.dry_run:
			f = open(filename, "rb")
			lm_data = f.read()
			f.close()
			ret = rip_gim.get_frame_label_dict(lm_data)
			
			for id, dic in sorted(ret.items()):
				print "labels of %d" % id
				print dic.keys()		
		else:
			dump(filename, options.characterID, options.label, options.pos, options.scale, options.fout, options.texture_root, options.norecreate)
			
