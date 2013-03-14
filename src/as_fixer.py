# -*- coding: gbk -*-

# Fix action script bytecode stored in tag F005.
# Procedure:
#	1. split a sequence of bytecode into a list of action script record, and 
#		save the offset of each record as well.
#	2. for each record, if it has a field for a null-terminated string, which
#		will be a ref idx in LM file. So replace the ref idx with string.
#	3. for each record, if it has a field for a double value, swap the first 
#		and the last 2 bytes.
#	4. for each record, if 2 or 3 is applied, fix the 'size' field if any.
#	5. Save all fixed record and their fixed offset in a list.
#	6. for jump, branch, fix the offset. for define function, fix code size.
#	7. Add a constant pool at the head.

import struct

def split(abc):
	rec_list = []
	off_list = []
	
	off = 0x0
	while abc:
		action_code, = struct.unpack("<B", abc[:0x1])
		
		if action_code < 0x80:
			record = abc[:1]
		else:
			length = struct.unpack("<H", abc[0x1:0x3])[0] + 3
			record = abc[:length]
		
		off_list.append(off)
		rec_list.append(record)
		
		off += len(record)
		abc = abc[len(record):]
		
	return rec_list, off_list
	
def fix_record(abc, symbol_list):
	action_code, = struct.unpack("<B", abc[:0x1])
	if action_code < 0x80:
		return abc
		
	# ActionDefineFunction
	if action_code == 0x9B:
		func_name_idx, num_params = struct.unpack("<H", abc[0x3:0x7])
		func_name = symbol_list[func_name_idx]
		param_name_idx_list = struct.unpack("<" + "H" * num_params, abc[0x7: 0x7 + num_params * 2])
		
		fixed = abc[:0x3]
		fixed += func_name + "\x00"
		fixed += abc[0x5: 0x7]
		for i in xrange(num_params):
			fixed += symbol_list[param_name_idx_list[i]] + "\x00"
		fixed += abc[-0x2:]
		
	# ActionDefineFunction2
	elif action_code == 0x8E:

		func_name_idx, = struct.unpack("<H", abc[0x3:0x5])
		func_name = symbol_list[func_name_idx]
		func_name_len = len(func_name)
		
		register_params = []
		num_params, = struct.unpack("<H", abc[0x5:0x7])
		for i in xrange(num_params):
			register, param_name_idx = struct.unpack("<BH", 
				record[0xa+i*0x3: 0xa+i*0x3+0x3])
			param_name = symbol_list[param_name_idx]
			register_params.append((register, param_name))
		
		fixed = abc[:0x3]
		fixed += func_name + "\x00"
		fixed += abc[0x5:0xa]
		for register, param_name in register_params:
			fixed_record += struct.pack("<B", register)
			fixed_record += param_name + "\x00"
		fixed += abc[-0x2:]
	
	# ActionSetTarget
	elif action_code == 0x8B:
		target_name_idx, = struct.unpack("<H", abc[0x3: 0x5])
		target_name = symbol_list[target_name_idx]
		print "target_name_idx = %s" % target_name_idx
		print "target_name = %s" % target_name
		print
		fixed = abc[:0x3]
		fixed += target_name + "\x00"
		
	# ActionGoToLabel
	elif action_code == 0x8C:
		label_name_idx, = struct.unpack("<H", abc[0x3: 0x5])
		label_name = symbol_list[label_name_idx]
		fixed = abc[:0x3]
		fixed += label_name + "\x00"
			
	# ActionPush
	elif action_code == 0x96:
		raw_items = abc[0x3:]
		fixed = abc[:0x3]
		while raw_items:
			push_type, = struct.unpack("<B", raw_items[0x0:0x1])
			if push_type in (0x4, 0x5, 0x8):
				bytes = raw_items[0x1:0x2]
				off = 0x1
			elif push_type in (0x9,):
				bytes = raw_items[0x1:0x3]
				off = 0x2
			elif push_type in (0x1, 0x7):
				bytes = raw_items[0x1:0x5]
				off = 0x4
			elif push_type in (0x6,):   # swap for double type
				bytes = raw_items[0x5:0x9] + raw_items[0x1:0x5]
				off = 0x8
			elif push_type == 0x0:  # look up raw string in symbol_list
				str_idx, = struct.unpack("<H", raw_items[0x1:0x3])
				_str = symbol_list[str_idx]
				bytes = _str + "\x00"
				off = 0x2
			elif push_type == 0x2:
				bytes = ""
				off = 0x0
			else:
				assert False, "not supported push type %x" % push_type
			fixed += raw_items[0x0:0x1] + bytes
			raw_items = raw_items[off + 1:]

	# Do Nothing
	elif action_code in (0x87, 0x9F, 0x83, 0x81, 0x99, 0x9D):
		fixed = abc
		
	# Not checked by me yet!
	else:
		assert False, "New Action Code = 0x%x" % action_code
	
	# update record size	
	fixed = fixed[:0x1] + struct.pack("<H", len(fixed)-3) + fixed[0x3:]
	return fixed
	
def fix_offset(rec_list, off_list, frec_list, foff_list):

	fixed2_list = []
	
	for i, frec in enumerate(frec_list):
		action_code, = struct.unpack("<B", frec[:0x1])
			
		if action_code in (0x9B, 0x8E):
			old_code_size, = struct.unpack("<H", frec[-2:])
			j = i + 1
			new_code_size = 0
			while old_code_size > 0:
				new_code_size += len(frec_list[j])
				old_code_size -= len(rec_list[j])
				j += 1
			
			fixed = frec[:-2] + struct.pack("<H", new_code_size)
			
		elif action_code in (0x99, 0x9D):
			old_branch_off, = struct.unpack("<h", frec[-2:])
			if old_branch_off > 0:
				j = i + 1
				new_branch_off = 0
				while old_branch_off > 0:
					new_branch_off += len(frec_list[j])
					old_branch_off -= len(rec_list[j])
					j += 1
			else:
				j = i - 1
				new_branch_off = -5
				old_branch_off += 5
				while old_branch_off < 0:
					old_branch_off += len(rec_list[j])
					new_branch_off -= len(frec_list[j])
					j -= 1
			
			fixed = frec[:-2] + struct.pack("<h", new_branch_off)
			
		else:
			fixed = frec
		
		fixed2_list.append(fixed)

	return fixed2_list					
	
def build_constant_pool(symbol_table):
	constant_pool = "".join([str+"\x00" for str in symbol_table])
	action_constant_pool = struct.pack("<BHH", 0x88, 2+len(constant_pool), 
		len(symbol_table)) + constant_pool
	return action_constant_pool
	
def fix(abc, symbol_list, format):
	rec_list, off_list = split(abc)
	frec_list, foff_list = [], [0,]
	for rec in rec_list:
		frec = fix_record(rec, symbol_list)
		frec_list.append(frec)
		foff_list.append(foff_list[-1] + len(frec))
	foff_list = foff_list[:-1]
	
	fixed2_list = fix_offset(rec_list, off_list, frec_list, foff_list)
	constant_pool = build_constant_pool(symbol_list)
	
	return constant_pool + "".join(fixed2_list)