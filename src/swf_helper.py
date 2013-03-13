import struct

TWIPS_PER_PIXEL = 20
PLACE_FLAG_HAS_CLIP_ACTIONS = 0x80
PLACE_FLAG_HAS_CLIP_DEPTH = 0x40
PLACE_FLAG_HAS_NAME = 0x20
PLACE_FLAG_HAS_RATIO = 0x10
PLACE_FLAG_HAS_COLOR_TRANSFORM = 0x8
PLACE_FLAG_HAS_MATRIX = 0x4
PLACE_FLAG_HAS_CHARACTER = 0x2
PLACE_FLAG_MOVE = 0x1

SHAPE_FLAG_NON_EDGE = 0x80	
SHAPE_FLAG_STATE_NEW_STYLES = 0x40
SHAPE_FLAG_STATE_LINE_STYLE = 0x20
SHAPE_FLAG_STATE_FILL_STYLE1 = 0x10
SHAPE_FLAG_STATE_MOVE_TO = 0x8

# don't bother to list all, most are not used!
CLIP_EVENT_KEY_UP = 0x80000000
CLIP_EVENT_KEY_DOWN = 0x40000000
CLIP_EVENT_MOUSE_UP = 0x20000000
CLIP_EVENT_KEY_PRESS = 0x00000200

def calc_nbits(v):
	v = abs(v)
	if v == 0:
		return 0
	else:
		nbits = 0
		while v != 0:
			v >>= 1
			nbits += 1
		nbits += 1
	return nbits

def to_fixed(v):
	a = int(v)
	b = int((v - a) * 0xFFFF)
#	print a, b
	return (a << 16) + b
			
def to_fixed16(v):
	a = int(v)
	b = int((v - a) * 0xFF)
#	print a, b
	return (a << 8) + b
	
def pack_fixed(v):
	a = int(v)
	b = int((v - a) * 0xFFFF)
	return struct.pack("<hh", b, a)
	
def pack_fixed16(v):
	a = int(v)
	b = int((v - a) * 0xFF)
	return struct.pack("<bb", b, a)
	
def pack_ubyte(v):
	return struct.pack("<B", v)
	
def pack_uword(v):
	return struct.pack("<I", v)
	
def pack_uhalf(v):
	return struct.pack("<H", v)

def pack_byte(v):
	return struct.pack("<b", v)
	
def pack_word(v):
	return struct.pack("<i", v)
	
def pack_half(v):
	return struct.pack("<h", v)
		
def pack_bits(vs, bits, debug=False):
	totbits = sum(bits)
	padbits = (totbits + 7) / 8 * 8 - totbits
	vs = list(vs)
	bits = list(bits)
	if padbits > 0:
		bits.append(padbits)
		vs.append(0)
	ret = ""	
	cur_bits = 0
	cur_byte = 0
	idx = 0
	while idx < len(bits) or cur_bits > 0:
		if cur_bits < 8:
			cur_byte <<= bits[idx]
#			print "add number %d" % vs[idx]
			cur_byte |= vs[idx] & ((1 << bits[idx]) - 1)
#			print "make number %d" % cur_byte
			cur_bits += bits[idx]
#			print "make_curbits %d" % cur_bits
#			print
			idx += 1
			
		if cur_bits >= 8:
#			print "write bytes 0x%02x" % (cur_byte >> cur_bits - 8)
			ret += pack_ubyte(cur_byte >> cur_bits - 8)
			cur_bits -= 8
#			print "make cur bits %d" % cur_bits
#			print
			cur_byte &= (1 << cur_bits) - 1
	return ret	
	
def pack_string(str):
	return str + "\x00"
	
def pack_rect(xmin, ymin, xmax, ymax):
	vmax = max(abs(xmin), abs(ymin), abs(xmax), abs(ymax)) * TWIPS_PER_PIXEL
	nbits = calc_nbits(vmax)
	assert nbits <= 0x1F, "TOO LARGE VALUE %d" % nbits
	return pack_bits((nbits, xmin * TWIPS_PER_PIXEL, xmax * TWIPS_PER_PIXEL, 
		ymin * TWIPS_PER_PIXEL, ymax * TWIPS_PER_PIXEL),
		(5, nbits, nbits, nbits, nbits))
	
def pack_color(color):
	data = ""
	for x in color:
		data += pack_ubyte(int(x))
	return data
	
def pack_matrix(scale, rotate, translate):
	has_scale = (scale is not None)
	has_rotate = (rotate is not None)
	has_translate = (translate is not None)
	
	vs = []
	bits = []
	if has_scale:
		scale_x = to_fixed(scale[0])
		scale_y = to_fixed(scale[1])
		vmax = max(abs(scale_x), abs(scale_y))
		nbits = calc_nbits(vmax)
		assert nbits <= 0x1F, "TOO LARGE VALUE %d" % nbits
		vs.extend((1, nbits, scale_x, scale_y))
		bits.extend((1, 5, nbits, nbits))
	else:
		vs.append(0)
		bits.append(1)
		
	if has_rotate:
		rotate_x = to_fixed(rotate[0])
		rotate_y = to_fixed(rotate[1])
		vmax = max(abs(rotate_x), abs(rotate_y))
		nbits = calc_nbits(vmax)
		assert nbits <= 0x1F, "TOO LARGE VALUE %d" % nbits
		vs.extend((1, nbits, rotate_x, rotate_y))
		bits.extend((1, 5, nbits, nbits))
	else:
		vs.append(0)
		bits.append(1)	
		
	assert has_translate, "translate can't be null!"
	translate_x = int(translate[0] * TWIPS_PER_PIXEL)
	translate_y = int(translate[1] * TWIPS_PER_PIXEL)
	vmax = max(abs(translate_x), abs(translate_y))
	nbits = calc_nbits(vmax)
	assert nbits <= 0x1F, "TOO LARGE VALUE %d" % nbits
	vs.extend((nbits, translate_x, translate_y))
	bits.extend((5, nbits, nbits))
		
#	print vs
#	print bits
	return pack_bits(vs, bits)		

def pack_color_transform_with_alpha(color_add, color_mul):
	has_add_items = (color_add is not None)
	has_mul_items = (color_mul is not None)
	vs = []
	bits = []
	
	vs.extend((int(has_add_items), int(has_mul_items)))
	bits.extend((1, 1))
	
	tmp_vs = []
	nbits = 0
	if has_mul_items:
		for v in color_mul:
			v = to_fixed16(v)
			nbits = max(nbits, calc_nbits(v))
			tmp_vs.append(v)	
	if has_add_items:
		for v in color_add:
			nbits = max(nbits, calc_nbits(v))
			tmp_vs.append(v)
	assert nbits <= 0xF, "TOO LARGE VALUE %d" % nbits
	added_cnt = len(tmp_vs)
	
	vs.append(nbits)
	bits.append(4)
	
	vs.extend(tmp_vs)
	bits.extend([nbits] * added_cnt)
	
	return pack_bits(vs, bits)
	
def pack_fill_style(type, bitmap_id=None, bitmap_matrix=None, color=None):
	assert type in (0x00, 0x40, 0x41, 0x42, 0x43), "don't support this fill style atm!"
	data = ""
	if type in (0x40, 0x41, 0x42, 0x43):
		data += pack_ubyte(type)
		data += pack_uhalf(bitmap_id)
		data += bitmap_matrix
		return data
	elif type in (0x00, ):
		data += pack_ubyte(type)
		data += color
		return data
	
def pack_clip_action_record(flags, actions, keycode=None):
	ret = pack_uword(flags)
	data = ""
	if flags & CLIP_EVENT_KEY_PRESS:
		data += pack_ubyte(keycode)
	data += "".join(actions)
	ret += pack_uword(len(data))
	return ret + data
	
def pack_clip_actions(clip_action_records):
	ret = pack_uhalf(0)
	flags = 0
	for record in clip_action_records:
		flags |= struct.unpack("<I", record[:0x4])[0]
	ret += pack_uword(flags)
	ret += "".join(clip_action_records)
	ret += pack_uword(0)
	return ret
		
def pack_line_style(width, color):
	return pack_uhalf(width) + color
		
def pack_fill_style_array(fill_styles):
	data = ""
	if len(fill_styles) > 0xFF:
		data += pack_ubyte(0xFF)
		data += pack_uhalf(len(fill_styles))
	else:
		data += pack_ubyte(len(fill_styles))
	return data + "".join(fill_styles)
	
def pack_line_style_array(line_styles):
	data = ""
	if len(line_styles) > 0xFF:
		data += pack_ubyte(0xFF)
		data += pack_uhalf(len(line_styles))
	else:
		data += pack_ubyte(len(line_styles))
	return data + "".join(line_styles)
	
def pack_style_change_record():
	pass
	
def pack_end_shape_record():
	return pack_ubyte(0)

def pack_shape_with_style(fill_styles, line_styles):
	pass
	
def make_record_header(tag_type, length):
	if length >= 63:
		ret = pack_uhalf((tag_type << 6) + 63) + pack_word(length)
	else:
		ret = pack_uhalf((tag_type << 6) + length)
	return ret
	
def make_swf_header(version, file_length, frame_width, frame_height, 
	frame_rate, frame_count):
	ret = "FWS"
	ret += pack_ubyte(version)
	ret += pack_uword(file_length)
	ret += pack_rect(0, 0, frame_width, frame_height)
	ret += pack_fixed16(frame_rate)
	ret += pack_uhalf(frame_count)
	return ret
	
def make_remove_object2_tag(depth):
	ret = make_record_header(28, 2)
	ret += pack_uhalf(depth)
	return ret
	
def make_define_bits_JPEG2_tag(id, image_data):
	ret = make_record_header(21, 2+len(image_data))
	ret += pack_uhalf(id)
	ret += image_data
	return ret
	
def make_define_sprite_tag(id, frame_count, control_tags):
	data = pack_uhalf(id)
	data += pack_uhalf(frame_count)
	data += "".join(control_tags)
#	print "id=%d, control_tag_count = %d\n" % (id, len(control_tags))
	return make_record_header(39, len(data)) + data
	
def make_define_shape3_tag_solid_simple(shape_id, width, height, color):
	data = pack_uhalf(shape_id)
	data += pack_rect(0, 0, width, height)
	
	fill_style = pack_fill_style(0x0, color=color)
	fill_style_array = pack_fill_style_array((fill_style,))
	data += fill_style_array
	
	line_style_array = pack_line_style_array(())
	data += line_style_array
	
	data += pack_ubyte(0x10)
	
	# shape record (style change) flags
	vs = [0, 0, 0, 1, 0, 0]
	bits = [1, 1, 1, 1, 1, 1]
	# state fill style1
	vs.append(1)
	bits.append(1)
	# shape record (straight edge): (0, 0) --> (width, 0)
	nbits = calc_nbits(width*TWIPS_PER_PIXEL)
	nbits = max(0, nbits-2)
	assert nbits <= 0xF, "TOO LARGE NUMBER"	
	vs.extend([1, 1, nbits, 0, 0, width*TWIPS_PER_PIXEL])
	bits.extend([1, 1, 4, 1, 1, nbits+2])
	# shape record (straight edge): (width, 0) --> (width, height)
	nbits = calc_nbits(height*TWIPS_PER_PIXEL)
	nbits = max(0, nbits-2)
	assert nbits <= 0xF, "TOO LARGE NUMBER"	
	vs.extend([1, 1, nbits, 0, 1, height*TWIPS_PER_PIXEL])
	bits.extend([1, 1, 4, 1, 1, nbits+2])	
	# shape record (straight edge): (width, height) --> (0, height)
	nbits = calc_nbits(-width*TWIPS_PER_PIXEL)
	nbits = max(0, nbits-2)
	assert nbits <= 0xF, "TOO LARGE NUMBER"	
	vs.extend([1, 1, nbits, 0, 0, -width*TWIPS_PER_PIXEL])
	bits.extend([1, 1, 4, 1, 1, nbits+2])	
	# shape record (straight edge): (0, height) --> (0, 0)
	nbits = calc_nbits(-height*TWIPS_PER_PIXEL)
	nbits = max(0, nbits-2)
	assert nbits <= 0xF, "TOO LARGE NUMBER"	
	vs.extend([1, 1, nbits, 0, 1, -height*TWIPS_PER_PIXEL])
	bits.extend([1, 1, 4, 1, 1, nbits+2])		
	# shape record (end)
	vs.extend([0, 0])
	bits.extend([1, 5])
	
	data += pack_bits(vs, bits)
	
	return make_record_header(32, len(data)) + data	
	
def make_define_shape3_tag_bitmap_simple(shape_id, bitmap_id, width, height, fill_style_type=0x41):
	data = pack_uhalf(shape_id)
	data += pack_rect(0, 0, width, height)
	
	bitmap_matrix = pack_matrix((20.0, 20.0), None, (0, 0))
	fill_style = pack_fill_style(fill_style_type, bitmap_id=bitmap_id, bitmap_matrix=bitmap_matrix)
	
	fill_style_array = pack_fill_style_array((fill_style,))
	data += fill_style_array
	
	line_style_array = pack_line_style_array(())
	data += line_style_array
	
	data += pack_ubyte(0x10)
	
	# shape record (style change) flags
	vs = [0, 0, 0, 1, 0, 0]
	bits = [1, 1, 1, 1, 1, 1]
	# state fill style1
	vs.append(1)	
	bits.append(1)
	# shape record (straight edge): (0, 0) --> (width, 0)
	nbits = calc_nbits(width*TWIPS_PER_PIXEL)
	nbits = max(0, nbits-2)
	assert nbits <= 0xF, "TOO LARGE NUMBER"	
	vs.extend([1, 1, nbits, 0, 0, width*TWIPS_PER_PIXEL])
	bits.extend([1, 1, 4, 1, 1, nbits+2])
	# shape record (straight edge): (width, 0) --> (width, height)
	nbits = calc_nbits(height*TWIPS_PER_PIXEL)
	nbits = max(0, nbits-2)
	assert nbits <= 0xF, "TOO LARGE NUMBER"	
	vs.extend([1, 1, nbits, 0, 1, height*TWIPS_PER_PIXEL])
	bits.extend([1, 1, 4, 1, 1, nbits+2])	
	# shape record (straight edge): (width, height) --> (0, height)
	nbits = calc_nbits(-width*TWIPS_PER_PIXEL)
	nbits = max(0, nbits-2)
	assert nbits <= 0xF, "TOO LARGE NUMBER"	
	vs.extend([1, 1, nbits, 0, 0, -width*TWIPS_PER_PIXEL])
	bits.extend([1, 1, 4, 1, 1, nbits+2])	
	# shape record (straight edge): (0, height) --> (0, 0)
	nbits = calc_nbits(-height*TWIPS_PER_PIXEL)
	nbits = max(0, nbits-2)
	assert nbits <= 0xF, "TOO LARGE NUMBER"	
	vs.extend([1, 1, nbits, 0, 1, -height*TWIPS_PER_PIXEL])
	bits.extend([1, 1, 4, 1, 1, nbits+2])		
	# shape record (end)
	vs.extend([0, 0])
	bits.extend([1, 5])
	
	data += pack_bits(vs, bits)
	
	return make_record_header(32, len(data)) + data
	
def make_set_background_color_tag(r, g, b):
	data = pack_color((r, g, b))
	return make_record_header(9, len(data)) + data
	
def make_define_shape3_tag(id, bounding_rect, shapes):
	data = pack_uhalf(id)
	data += bounding_rect
	data += shapes
	return make_record_header(32, len(data)) + data
	
def make_frame_label_tag(str):
	data = pack_string(str)
	return make_record_header(43, len(data)) + data
	
def make_show_frame_tag():
	return make_record_header(1, 0)
	
def make_file_attributes_tag():
	ret = make_record_header(69, 4)
	ret += struct.pack("<I", 0x0)
	return ret
	
# WARNING: to be completed
def make_place_object2_tag(flags, depth, id=None, matrix=None, 
	color_trans=None, ratio=None, name=None, clip_depth=None, 
	clip_actions=None):
	data = ""
	data += pack_ubyte(flags)
	data += pack_uhalf(depth)
	if flags & PLACE_FLAG_HAS_CHARACTER:
		data += pack_uhalf(id)
	if flags & PLACE_FLAG_HAS_MATRIX:
		data += matrix	
	if flags & PLACE_FLAG_HAS_COLOR_TRANSFORM:
		data += color_trans		
	if flags & PLACE_FLAG_HAS_RATIO:
		data += pack_uhalf(ratio)
	if flags & PLACE_FLAG_HAS_NAME:
		data += pack_string(name)
	if flags & PLACE_FLAG_HAS_CLIP_DEPTH:
		data += pack_uhalf(clip_depth)
	if flags & PLACE_FLAG_HAS_CLIP_ACTIONS:
		data += clip_actions
	return make_record_header(26, len(data)) + data
	
def make_end_tag():
	return make_record_header(0, 0)
	
def make_do_action_tag(action_records):
	data = "".join(action_records)
	data += pack_ubyte(0)
#	print "action_record len %d" % len(data)
	return make_record_header(12, len(data)) + data
	
def make_remove_object2_tag(id):
	ret = make_record_header(28, 2)
	ret += pack_uhalf(id)
	return ret
	
def get_tag_header_size(tag):
	tag_code_and_length, = struct.unpack("<H", tag[:0x2])
if __name__ == "__main__":
#	f, = struct.unpack("<f", "\x00\x00\x70\x42")
#	print repr(pack_fixed16(f))
#	print calc_nbits(0x10000)
#   print len(pack_bits((1, 0, 1, ), (8, 0, 8,)))
	pack_color_transform_with_alpha((0,0,0,0), (1.0,1.0,1.0))