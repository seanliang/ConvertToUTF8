# -*- coding: utf-8 -*-

import sublime, sublime_plugin
import sys
import os
# sys.path.append(os.path.join(sublime.packages_path(), 'ConvertToUTF8', 'chardet'))
from chardet.universaldetector import UniversalDetector
import codecs

def detect(file_name):
	if not os.path.exists(file_name):
		return
	detector = UniversalDetector()
	cnt = 0
	fp = file(file_name, 'rb')
	for line in fp:
		detector.feed(line)
		cnt += 1
		if detector.done or cnt > 200:
			break
	fp.close()
	detector.close()
	encoding = detector.result['encoding']
	if not encoding:
		return
	if detector.result['confidence'] < 0.7:
		return
	encoding = encoding.upper()
	if encoding == 'BIG5':
		encoding = 'BIG5-HKSCS'
	elif encoding == 'GB2312':
		encoding = 'GBK'
	return encoding

def show_encoding_status(view):
	encoding = view.settings().get('force_encoding')
	if not encoding:
		encoding = view.settings().get('origin_encoding')
	view.set_status('origin_encoding', encoding)

def init_encoding_vars(view, encoding):
	view.settings().set('origin_encoding', encoding)
	show_encoding_status(view)
	if encoding in ('ASCII', 'UTF-8', 'UTF-16LE', 'UTF-16BE'):
		return
	view.settings().set('in_converting', True)
	view.settings().set('prevent_undo', True)
	view.set_encoding('UTF-8')

def clean_encoding_vars(view):
	view.settings().erase('in_converting')
	view.settings().erase('origin_encoding')
	view.erase_status('origin_encoding')
	view.erase_status('decode_fail_line')
	view.set_scratch(False)

class ConvertToUtf8Command(sublime_plugin.TextCommand):
	def run(self, edit, encoding=None):
		view = self.view
		if encoding:
			view.settings().set('force_encoding', encoding)
			origin_encoding = view.settings().get('origin_encoding')
			if origin_encoding and origin_encoding != encoding:
				view.set_scratch(False)
			init_encoding_vars(view, encoding)
			return
		else:
			encoding = view.settings().get('origin_encoding')
		if not encoding:
			return
		view.erase_status('decode_fail_line')
		file_name = view.file_name()
		if not (file_name and os.path.exists(file_name)):
			return
		# try fast decode
		try:
			fp = codecs.open(file_name, 'rb', encoding, errors='strict')
			contents = fp.read()
			fp.close()
		except UnicodeDecodeError, e:
			# try decode line by line
			contents = ''
			fp = file(file_name, 'rb')
			fails = []
			cnt = 0
			for line in fp:
				cnt += 1
				try:
					contents += line.decode(encoding)
				except:
					contents += line.decode('ISO-8859-1')
					fails.append(cnt)
			fp.close()
			view.set_status('decode_fail_line', 'Decode Failed: %r' % fails)
		contents = contents.replace('\r\n', '\n').replace('\r', '\n')
		regions = sublime.Region(0, view.size())
		edit = view.begin_edit()
		view.replace(edit, regions, contents)
		view.end_edit(edit)
		sublime.status_message('%s -> UTF8' % encoding)

	def description(self):
		encoding = self.view.settings().get('origin_encoding')
		if not encoding:
			return
		return '%s -> UTF8' % encoding

class ConvertFromUtf8Command(sublime_plugin.TextCommand):
	def run(self, edit):
		view = self.view
		encoding = view.settings().get('force_encoding')
		if not encoding:
			encoding = view.settings().get('origin_encoding')
		if not encoding or encoding == 'UTF-8':
			return
		file_name = view.file_name()
		try:
			fp = file(file_name, 'rb')
			contents = codecs.EncodedFile(fp, encoding, 'UTF-8').read()
			fp.close()
		except UnicodeEncodeError, e:
			fp = file(file_name, 'rb')
			contents = ''
			for line in fp:
				try:
					contents += line.decode('UTF-8').encode(encoding)
				except UnicodeEncodeError, e:
					contents += line.decode('UTF-8').encode('ISO-8859-1')
			fp.close()
		fp = file(view.file_name(), 'wb')
		fp.write(contents)
		fp.close()
		view.settings().set('prevent_detect', True)
		sublime.status_message('UTF8 -> %s' % encoding)

	def description(self):
		encoding = self.view.settings().get('origin_encoding')
		if not encoding:
			return
		return 'UTF8 -> %s' % encoding

class ConvertToUTF8Listener(sublime_plugin.EventListener):
	def convert_to_utf8(self, view):
		view.settings().set('scratch_flag', True)
		view.run_command('convert_to_utf8')

	def convert_from_utf8(self, view):
		view.run_command('convert_from_utf8')

	def check_clones(self, view):
		clone_numbers = view.settings().get('clone_numbers', 0)
		if clone_numbers:
			check_times = view.settings().get('check_times', clone_numbers)
			if check_times:
				view.settings().set('check_times', check_times - 1)
				return True
			view.settings().erase('check_times')
		return False

	def on_clone(self, view):
		clone_numbers = view.settings().get('clone_numbers', 0)
		view.settings().set('clone_numbers', clone_numbers + 1)

	def on_close(self, view):
		clone_numbers = view.settings().get('clone_numbers', 0)
		if clone_numbers:
			view.settings().set('clone_numbers', clone_numbers - 1)

	def on_load(self, view):
		file_name = view.file_name()
		if not file_name:
			return
		if self.check_clones(view):
			return
		encoding = view.settings().get('origin_encoding')
		if encoding:
			view.settings().erase('prevent_undo')
			view.set_status('origin_encoding', encoding)
			return
		load_setting = sublime.load_settings('ConvertToUTF8.sublime-settings').get('convert_on_load', 'always')
		if load_setting == 'never':
			return
		encoding = detect(view.file_name())
		if not encoding:
			return
		init_encoding_vars(view, encoding)

	def on_modified(self, view):
		if not view.file_name() or view.is_loading():
			return
		if not view.settings().get('in_converting'):
			return
		if self.check_clones(view):
			return
		if view.settings().get('scratch_flag'):
			view.set_scratch(True)
			view.settings().erase('scratch_flag')
			return
		# reach origin content
		command = view.command_history(0)
		reverted = (command == (None, None, 0))
		if command[0] == 'revert':
			if view.command_history(1)[0] == 'convert_to_utf8':
				reverted = True
			elif view.settings().get('reverting'):
				view.settings().erase('reverting')
				if view.settings().get('prevent_detect'):
					view.settings().erase('prevent_detect')
				else:
					encoding = detect(view.file_name())
					if encoding:
						if encoding != view.settings().get('origin_encoding'):
							init_encoding_vars(view, encoding)
					else:
						sublime.error_message('The encoding of this file has been changed outside, which is not supported by ConvertToUTF8. Please set the encoding if the content is mess up.')
						clean_encoding_vars(view)
						return
				view.settings().set('prevent_undo', True)
				reverted = True
			else:
				# revert will call on_modified twice
				view.settings().set('reverting', True)
				vp = view.viewport_position()
				view.settings().set('vp', [vp[0], vp[1]])
				return
		if reverted:
			if view.settings().get('prevent_undo'):
				self.convert_to_utf8(view)
				vp = view.settings().get('vp')
				if vp:
					view.set_viewport_position(tuple(vp))
		else:
			view.set_scratch(False)

	def on_pre_save(self, view):
		force_encoding = view.settings().get('force_encoding')
		if force_encoding == 'UTF-8':
			view.set_encoding(force_encoding)
			return
		if not view.settings().get('in_converting'):
			return
		view.set_encoding('UTF-8')

	def on_post_save(self, view):
		if not view.settings().get('in_converting'):
			return
		if self.check_clones(view):
			return
		settings = sublime.load_settings('ConvertToUTF8.sublime-settings')
		save_setting = settings.get('convert_on_save', 'always')
		if save_setting == 'never':
			clean_encoding_vars(view)
			return
		self.convert_from_utf8(view)
