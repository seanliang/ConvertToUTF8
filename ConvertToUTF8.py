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
	return detector.result

class ConvertToUtf8Command(sublime_plugin.TextCommand):
	def run(self, edit):
		view = self.view
		encoding = view.settings().get('origin_encoding')
		if not encoding:
			return
		# try fast decode
		try:
			contents = codecs.open(view.file_name(), 'r', encoding, errors='strict').read()
		except UnicodeDecodeError, e:
			# try decode line by line
			contents = ''
			fp = file(view.file_name())
			line = fp.readline()
			fails = []
			cnt = 0
			while line != '':
				cnt += 1
				try:
					contents += line.decode(encoding)
				except:
					contents += line.decode('ISO-8859-1')
					fails.append(cnt)
				line = fp.readline()
			fp.close()
			view.set_status('decode_fail_line', 'Decode Failed: %r' % fails)
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
		regions = sublime.Region(0, view.size())
		try:
			contents = view.substr(regions).encode(encoding)
		except UnicodeEncodeError, e:
			contents = ''
			for region in view.split_by_newlines(regions):
				line = view.substr(view.full_line(region))
				try:
					contents += line.encode(encoding)
				except UnicodeEncodeError, e:
					contents += line.encode('ISO-8859-1')
		f = file(view.file_name(), 'w')
		f.write(contents)
		f.close()
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

	def on_load(self, view):
		encoding = view.settings().get('origin_encoding')
		if encoding:
			view.settings().erase('prevent_undo')
			view.set_status('origin_encoding', encoding)
			return
		load_setting = sublime.load_settings('ConvertToUTF8.sublime-settings').get('convert_on_load', 'always')
		if load_setting == 'never':
			return
		result = detect(view.file_name())
		encoding = result['encoding'].upper()
		confidence = result['confidence']
		if confidence < 0.7 or encoding in ('ASCII', 'UTF-8', 'UTF-16LE', 'UTF-16BE'):
			return
		# It's more compatible to use HKSCS instead of Big5
		if encoding == 'BIG5':
			encoding = 'BIG5-HKSCS'
		view.settings().set('origin_encoding', encoding)
		view.settings().set('prevent_undo', True)
		view.set_status('origin_encoding', encoding)
		view.set_encoding('UTF-8')

	def on_modified(self, view):
		if not view.file_name() or view.is_loading():
			return
		if not view.settings().get('origin_encoding'):
			return
		if view.settings().get('scratch_flag'):
			view.set_scratch(True)
			view.settings().erase('scratch_flag')
			return
		# reach origin content
		if view.command_history(0) == (None, None, 0):
			if view.settings().get('prevent_undo'):
				self.convert_to_utf8(view)
		else:
			view.set_scratch(False)

	def on_pre_save(self, view):
		if not view.settings().get('origin_encoding'):
			return
		settings = sublime.load_settings('ConvertToUTF8.sublime-settings')
		save_setting = settings.get('convert_on_save', 'always')
		if save_setting == 'never':
			# Extra line will be created for each line if it's Windows format
			view.set_line_endings('Unix')

	def on_post_save(self, view):
		if not view.settings().get('origin_encoding'):
			return
		settings = sublime.load_settings('ConvertToUTF8.sublime-settings')
		save_setting = settings.get('convert_on_save', 'always')
		if save_setting == 'never':
			return
		self.convert_from_utf8(view)
