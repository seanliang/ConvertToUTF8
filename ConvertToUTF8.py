# -*- coding: utf-8 -*-

import sublime, sublime_plugin
import sys
import os
# sys.path.append(os.path.join(sublime.packages_path(), 'ConvertToUTF8', 'chardet'))
from chardet.universaldetector import UniversalDetector
import codecs
import threading

SKIP_ENCODINGS = ('Hexadecimal', 'ASCII', 'UTF-8', 'UTF-16LE', 'UTF-16BE')

SETTINGS = {}

def get_settings():
	settings = sublime.load_settings('ConvertToUTF8.sublime-settings')
	SETTINGS['max_detect_lines'] = settings.get('max_detect_lines', 600)
	SETTINGS['convert_on_load'] = settings.get('convert_on_load', 'always')
	SETTINGS['convert_on_save'] = settings.get('convert_on_save', 'always')

def init_settings():
	get_settings()
	sublime.load_settings('ConvertToUTF8.sublime-settings').add_on_change('get_settings', get_settings)

init_settings()

def detect(view, file_name, callback=None):
	if not os.path.exists(file_name):
		return
	sublime.set_timeout(lambda: view.set_status('origin_encoding', 'Detecting encoding, please wait...'), 0)
	detector = UniversalDetector()
	cnt = SETTINGS['max_detect_lines']
	fp = file(file_name, 'rb')
	for line in fp:
		detector.feed(line)
		cnt -= 1
		if detector.done or cnt == 0:
			break
	fp.close()
	detector.close()
	encoding = detector.result['encoding']
	confidence = detector.result['confidence']
	if not encoding or confidence < 0.7:
		sublime.set_timeout(lambda: view.set_status('origin_encoding', 'Encoding can not be detected, please choose one manually. (%s/%.2f)' % (encoding, confidence)), 0)
		return
	encoding = encoding.upper()
	if encoding == 'BIG5':
		encoding = 'BIG5-HKSCS'
	elif encoding == 'GB2312':
		encoding = 'GBK'
	if callback:
		sublime.set_timeout(lambda: callback(view, encoding), 0)
	return encoding

def show_encoding_status(view):
	encoding = view.settings().get('force_encoding')
	if not encoding:
		encoding = view.settings().get('origin_encoding')
	view.set_status('origin_encoding', encoding)

def init_encoding_vars(view, encoding, run_convert=True):
	if not encoding:
		return
	view.settings().set('origin_encoding', encoding)
	show_encoding_status(view)
	if encoding in SKIP_ENCODINGS or encoding == view.encoding():
		return
	view.settings().set('in_converting', True)
	if view.encoding() in SKIP_ENCODINGS:
		return
	view.settings().set('prevent_undo', True)
	if run_convert:
		view.run_command('convert_to_utf8')

def clean_encoding_vars(view):
	view.settings().erase('in_converting')
	view.settings().erase('origin_encoding')
	view.erase_status('origin_encoding')
	view.set_scratch(False)

class ConvertToUtf8Command(sublime_plugin.TextCommand):
	def run(self, edit, encoding=None):
		view = self.view
		if encoding:
			view.settings().set('force_encoding', encoding)
			origin_encoding = view.settings().get('origin_encoding')
			run_convert = True
			if origin_encoding:
				if origin_encoding == encoding:
					return
				view.set_scratch(False)
				run_convert = False
			init_encoding_vars(view, encoding, run_convert)
			return
		else:
			encoding = view.settings().get('origin_encoding')
		if not encoding:
			return
		file_name = view.file_name()
		if not (file_name and os.path.exists(file_name)):
			return
		# try fast decode
		try:
			fp = codecs.open(file_name, 'rb', encoding, errors='strict')
			contents = fp.read()
		except UnicodeDecodeError, e:
			clean_encoding_vars(view)
			sublime.error_message('Can not convert file %s with %s, please try another encoding.' % (file_name, encoding))
			return
		finally:
			fp.close()
		contents = contents.replace('\r\n', '\n').replace('\r', '\n')
		regions = sublime.Region(0, view.size())
		sel = view.sel()
		rs = [x for x in sel]
		vp = view.viewport_position()
		view.set_viewport_position(tuple([0, 0]))
		edit = view.begin_edit()
		view.replace(edit, regions, contents)
		view.end_edit(edit)
		sel.clear()
		for x in rs:
			sel.add(sublime.Region(x.a, x.b))
		view.set_viewport_position(vp)
		view.settings().set('scratch_flag', True)
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
		except UnicodeEncodeError, e:
			sublime.error_message('Can not convert file encoding of %s to %s, it was saved as UTF-8 instead.' %  (file_name, encoding))
			return
		finally:
			fp.close()
		fp = file(file_name, 'wb')
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
		if SETTINGS['convert_on_load'] == 'never':
			return
		view_encoding = view.encoding()
		if view_encoding != 'Undefined' and view_encoding != sublime.load_settings('Preferences.sublime-settings').get('fallback_encoding'):
			return
		threading.Thread(target=lambda: detect(view, file_name, init_encoding_vars)).start()

	def on_modified(self, view):
		file_name = view.file_name()
		if not file_name or view.is_loading():
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
			if not hasattr(self, 'in_reverting'):
				self.in_reverting = False
			if view.command_history(1)[0] == 'convert_to_utf8':
				reverted = True
			elif self.in_reverting:
				self.in_reverting = False
				if view.settings().get('prevent_detect'):
					view.settings().erase('prevent_detect')
				else:
					view_encoding = view.encoding()
					if view_encoding != 'Undefined' and view_encoding != sublime.load_settings('Preferences.sublime-settings').get('fallback_encoding'):
						return
					threading.Thread(target=lambda: detect(view, file_name, init_encoding_vars)).start()
					return
				view.settings().set('prevent_undo', True)
				reverted = True
			else:
				# revert will call on_modified twice
				self.in_reverting = True
				return
		if reverted:
			if view.settings().get('prevent_undo'):
				self.convert_to_utf8(view)
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
		if SETTINGS['convert_on_save'] == 'never':
			clean_encoding_vars(view)
			return
		self.convert_from_utf8(view)
