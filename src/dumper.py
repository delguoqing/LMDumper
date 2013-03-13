# -*- coding: gbk -*-
import optparse
import swf_helper
import as_fixer

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
		
#		assert tag_type in format.DATA, "Not Analyzed Tag!!! off=%x 0x%04x" % (off, tag_type)
		
		if not _type_set or tag_type in _type_set:
			yield off, tag_type, tag_size_bytes, lumen
		if tag_type == 0xFF00:
			break
			
		off += tag_size_bytes
		lumen = seek_next_tag(lumen)
		
def make_imgs(ctx, cid):
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
		f = open(os.path.join(root, fname), "rb")
		image_data = f.read()
		f.close()
		
		tag = swf_helper.make_define_bits_JPEG2_tag(cid, image_data)
		img_tags.append(tag)
		img_idx_2_cid[i] = cid
		cid += 1
		
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
		
	return tag

def make_tex_sprite(ctx, d, subds):
	sprite_id = d["sprite_id"]
	sub_tags = []

	for i, subd in enumerate(subds):
		shape_tag = make_shape(ctx, subd)
		shape_id, = struct.unpack("<H", shape_tag[0x3:0x5])
		xmin = min(subd["x0"], subd["x1"], subd["x2"], subd["x3"])
		ymin = min(subd["y0"], subd["y1"], subd["y2"], subd["y3"])
		matrix = swf_helper.pack_matrix(None, None, (xmin, ymin))
		place_obj2_tag = swf_helper.swf_helper.make_place_object2_tag(swf_helper.PLACE_FLAG_HAS_CHARACTER | swf_helper.PLACE_FLAG_HAS_MATRIX, i+1, id=shape_id, matrix=matrix)
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
	frame_cnt = d["frame_cnt"]
	sprite_id = d["sprite_id"]
	frame_label_dict = {}
	
	# build a frame label dict for later ref	
	for subd in subds[:frame_label_cnt]:
		assert subd["tag_type"] == 0x002B
		frame_id = subd["frame_id"]
		frame_label = symbol_list[subd["frame_label_idx"]]
		frame_label_dict[frame_id] = frame_label
		
	# handle the rest, all the frames
	sub_tags = []
	depth2matrix = {}
	depth2color_trans = {}
	clip_action_cnt = -1
	frame_cmd_cnt = -1
	for subd in subds[:frame_label_cnt]:
	
		# finish all clip_action tags, pack place object2 tag
		if clip_action_cnt == 0:
			if len(clip_action_records) > 0:
				flags |= swf_helper.PLACE_FLAG_HAS_CLIP_ACTIONS
				clip_actions = \
					swf_helper.pack_clip_actions(clip_action_records)
			else:
				clip_actions = None
				
			ptag = swf_helper.make_place_object2_tag(flags, depth, id, 
				name=name, matrix=matrix, color_trans=color_trans, clip_actions=clip_actions, ratio=ratio, clip_depth=clip_depth)
			sub_tags.append(ptag)
			
			clip_action_cnt = -1
					
		if frame_cmd_cnt == 0:
			sub_tags.append(swf_helper.make_show_frame_tag())
			frame_cmd_cnt = -1
			
		if subd["tag_type"] == 0x0001:
			frame_cmd_cnt = subd["cmd_cnt"]
		elif subd["tag_type"]	== 0x0005:
			sub_tags.append(swf_helper.make_remove_object2_tag(
				subd["depth"] + 1))
			frame_cmd_cnt -= 1
		elif subd["tag_type"] == 0x000c:
			global format
			bytecodes = as_list[subd["as_idx"]]
			bytecodes = as_fixer.fix(bytecodes, symbol_list, format)
			sub_tags.append(swf_helper.make_do_action_tag([bytecodes]))
			frame_cmd_cnt -= 1
		elif subd["tag_type"] == 0xf014:

			clip_action_cnt -= 1
			bytecodes = as_fixer.fix(as_list[subd["as_idx"]], symbol_list, format)
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
				translate = point_list[trans_idx]
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
				c = color_list[color_mul_idx]
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
				
			ratio = d["inst_id"]	# Not sure??
			if ratio >= 0:
				flags |= swf_helper.PLACE_FLAG_HAS_RATIO

			if flags & swf_helper.PLACE_FLAG_HAS_CHARACTER and \
				flags & swf_helper.PLACE_FLAG_MOVE:
				sub_tags.append(swf_helper.make_remove_object2_tag(depth))
				flags &= (0xFFFF - swf_helper.PLACE_FLAG_MOVE)
				if not (flags & swf_helper.PLACE_FLAG_HAS_MATRIX):
					flags |= swf_helper.PLACE_FLAG_HAS_MATRIX
					matrix = depth2matrix[depth]
			
			clip_action_cnt = subd["clip_action_cnt"]
			clip_action_records = []
	
	return swf_helper.make_define_sprite_tag(sprite_id, frame_cnt, sub_tags)
	
def dump(fname, ID, label, pos, scale, fout, img_path, norecreate):
	
	image_root = img_path or r"c:\png"

	f = open(fname, "rb")
	lm_data = f.read()
	f.close()
	
	fout = fout or fname[:-3] + ".swf"
	if norecreate and os.path.exists(fout):
		return
	
	ctx = {"tags": [], "img_root": image_root,}
	for off, tag_type, tag_size_bytes, tag in iter_tag(lm_data):
		d = tag_reader.read_tag(format.DATA[tag_type], tag)
		if d["tag_type"] == 0xF001:
			ctx["symbol_list"] = []
			for symbol_info in d["symbol_list"]:
				ctx["symbol_list"].append(symbol_info["symbol"])
		elif d["tag_type"] == 0xF002:
			

		
	# init
	symbol_table = rip_gim.get_symbol_list(lm_data[0x40:])
	assert symbol_table[0] == ""
	constant_pool = "".join([str+"\x00" for str in symbol_table])
	action_constant_pool = struct.pack("<BHH", 0x88, 2+len(constant_pool), 
		len(symbol_table)) + constant_pool
	action_record_list = rip_gim.list_tagF005_symbol(lm_data)
	frame_label_dict = rip_gim.get_frame_label_dict(lm_data)
#	action_record_list = map(fix_action_record, action_record_list)
#	print len(action_record_list)
#	for i in ():
	for i in xrange(len(action_record_list)):
		print "fixing action record %d" % i
		action_record_list[i] = fix_action_record(action_record_list[i], symbol_table)
#	fix_action_record(action_record_list[2])
	
	max_characterID = rip_gim.get_max_characterID(lm_data)
	
	# image_dict: {filename : image_data}
	# image_dict2: {filename: (fill_style_type, shape_width, shape_height)}
	# shape_dict: {filename: (fill_style_type,)}

	image_dict = get_image_dict(lm_data, image_root)
	shape_dict, image_dict2 = get_shape_dict(lm_data)
	# all tags append to this list
	all_tags = []
	
	# make FileAttributes tag
	all_tags.append(swf_helper.make_file_attributes_tag())
	
	# make SetBackgroundColor tag
	all_tags.append(swf_helper.make_set_background_color_tag(0xFF, 0xFF, 0xFF))
	
	# make all DefineBitsJPEG2 tags
	define_bits_JPEG2_tags = []
	image_2_id = {}
	id = max_characterID + 1
	for k, v in image_dict.iteritems():
		tag = swf_helper.make_define_bits_JPEG2_tag(id, v)
		define_bits_JPEG2_tags.append(tag)
		image_2_id[k] = id
		id += 1
	all_tags.extend(define_bits_JPEG2_tags)
	
	# make all DefineShape tags
	define_shape_tags = []
	image_2_shape_id = {}
	shape_2_shape_id = {}
	id = max_characterID + len(image_dict) + 1
	for k, v in image_dict.iteritems():
		img_data = image_dict[k]
		
		fill_style_type, shape_width, shape_height = image_dict2[k]
		tag = swf_helper.make_define_shape3_tag_bitmap_simple(id, 
			image_2_id[k], shape_width, shape_height, fill_style_type)
		image_2_shape_id[k] = id
		id += 1
		define_shape_tags.append(tag)
		
	for k, (color, size) in shape_dict.iteritems():
		tag = swf_helper.make_define_shape3_tag_solid_simple(id, size[0],
			size[1], swf_helper.pack_color(color))
		shape_2_shape_id[k] = id
		id += 1
		define_shape_tags.append(tag)
		
	all_tags.extend(define_shape_tags)

	# make all texture mc tags
	define_sprite_tags = get_texture_sprite_tags(lm_data, image_2_shape_id, shape_2_shape_id, image_dict)
	all_tags.extend(define_sprite_tags)

	# make all general mc tags
	define_sprite_tags_general = get_define_sprite_tags(lm_data, action_constant_pool, action_record_list)
	all_tags.extend(define_sprite_tags_general)
	
	# test basic display
	tmp_tags = []
	
	# INSTANCE ID(ratio) should be enough!
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
	parser.add_option("-P", action="store", type="int", dest="platform", default=0, help="specify platform: %d for wii, %d for pspdx, default:%d" % (PLATFORM_WII, PLATFORM_PSPDX, 0))

	(options, args) = parser.parse_args(sys.argv)
	
	sys.path.append("../CLM")
	
	if options.platform == PLATFORM_WII:
		import rip_gim_wii as rip_gim
	elif options.platform == PLATFORM_PSPDX:
		import rip_gim_pspdx as rip_gim
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
			test(filename, options.characterID, options.label, options.pos, options.scale, options.fout, options.texture_root, options.norecreate)
