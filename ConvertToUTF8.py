# -*- coding: utf-8 -*-

import sublime, sublime_plugin
import sys
import os
# sys.path.append(os.path.join(sublime.packages_path(), 'ConvertToUTF8', 'chardet'))
from chardet.universaldetector import UniversalDetector
import codecs

def detect(file_name):
	detector = UniversalDetector()
	cnt = 0
	for line in file(file_name):
		detector.feed(line)
		cnt += 1
		if detector.done or cnt > 200:
			break
	detector.close()
	encoding = detector.result['encoding']
	if not encoding:
		return
	encoding = encoding.upper()
	if encoding in ('ASCII', 'UTF-8', 'UTF-16LE', 'UTF-16BE'):
		return
	if detector.result['confidence'] < 0.7:
		return
	if encoding == 'BIG5':
		encoding = 'BIG5-HKSCS'
	elif encoding == 'GB2312':
		encoding = 'GBK'
	return encoding

class ConvertToUtf8Command(sublime_plugin.TextCommand):
	def run(self, edit):
		view = self.view
		encoding = view.settings().get('origin_encoding')
		if not encoding:
			return
		file_name = view.file_name()
		# try fast decode
		try:
			contents = codecs.open(file_name, 'r', encoding, errors='strict').read()
		except UnicodeDecodeError, e:
			# try decode line by line
			contents = ''
			fp = file(file_name, 'r')
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
		if view.line_endings() == 'Windows':
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
		encoding = view.settings().get('origin_encoding')
		if not encoding:
			return
		file_name = view.file_name()
		try:
			contents = codecs.EncodedFile(file(file_name, 'r'), encoding, 'UTF-8').read()
		except UnicodeEncodeError, e:
			fp = file(file_name, 'r')
			contents = ''
			for line in fp:
				try:
					contents += line.decode('UTF-8').encode(encoding)
				except UnicodeEncodeError, e:
					contents += line.decode('UTF-8').encode('ISO-8859-1')
			fp.close()
		fp = file(view.file_name(), 'w')
		fp.write(contents)
		fp.close()
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

	def clean_vars(self, view):
		view.settings().erase('origin_encoding')
		view.erase_status('origin_encoding')
		view.erase_status('decode_fail_line')
		view.set_scratch(False)

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
		view.settings().set('origin_encoding', encoding)
		view.settings().set('prevent_undo', True)
		view.set_status('origin_encoding', encoding)
		view.set_encoding('UTF-8')

	def on_modified(self, view):
		if not view.file_name() or view.is_loading():
			return
		if not view.settings().get('origin_encoding'):
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
							view.settings().set('origin_encoding', encoding)
							view.set_status('origin_encoding', encoding)
					else:
						sublime.error_message('The encoding of this file has been changed outside, which is not supported by ConvertToUTF8. Please close and open this file again if the content is mess up.')
						self.clean_vars(view)
						return
				view.settings().set('prevent_undo', True)
				reverted = True
			else:
				# revert will call on_modified twice
				view.settings().set('reverting', True)
				return
		if reverted:
			if view.settings().get('prevent_undo'):
				self.convert_to_utf8(view)
		else:
			view.set_scratch(False)

	def on_pre_save(self, view):
		if not view.settings().get('origin_encoding'):
			return
		view.set_encoding('UTF-8')

	def on_post_save(self, view):
		if not view.settings().get('origin_encoding'):
			return
		if self.check_clones(view):
			return
		settings = sublime.load_settings('ConvertToUTF8.sublime-settings')
		save_setting = settings.get('convert_on_save', 'always')
		if save_setting == 'never':
			self.clean_vars(view)
			return
		view.settings().set('prevent_detect', True)
		self.convert_from_utf8(view)
