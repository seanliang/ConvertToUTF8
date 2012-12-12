# -*- coding: utf-8 -*-

import sublime, sublime_plugin
import sys
import os
from chardet.universaldetector import UniversalDetector
import codecs
import threading
import json
import time

SKIP_ENCODINGS = ('ASCII', 'UTF-8', 'UTF-16LE', 'UTF-16BE')

SETTINGS = {}
REVERTING_FILES = []

CONFIRM_IS_AVAILABLE = (sublime.version() > '2186')

ENCODINGS_NAME = []
ENCODINGS_CODE = []

class EncodingCache(object):
	def __init__(self):
		self.cache_file = os.path.join(sublime.packages_path(), 'User', 'encoding_cache.json')
		self.encoding_cache = []
		self.max_size = -1
		self.dirty = False
		self.load()
		self.save_on_dirty()

	def save_on_dirty(self):
		if self.dirty:
			self.save()
		sublime.set_timeout(self.save_on_dirty, 10000)

	def shrink(self):
		if self.max_size < 0:
			return
		if len(self.encoding_cache) > self.max_size:
			self.dirty = True
			del self.encoding_cache[self.max_size:]

	def set_max_size(self, max_size):
		self.max_size = max_size
		self.shrink()

	def load(self):
		if not os.path.exists(self.cache_file):
			return
		fp = file(self.cache_file, 'rb')
		self.encoding_cache = json.load(fp)
		fp.close()

	def save(self):
		self.shrink()
		fp = file(self.cache_file, 'wb')
		json.dump(self.encoding_cache, fp)
		fp.close()
		self.dirty = False

	def pop(self, file_name):
		for item in self.encoding_cache:
			if item['file'] == file_name:
				self.encoding_cache.remove(item)
				self.dirty = True
				return item['encoding']
		return None

	def set(self, file_name, encoding):
		if self.max_size < 1:
			return
		self.pop(file_name)
		self.encoding_cache.insert(0, {
			'file': file_name,
			'encoding': encoding
		})
		self.dirty = True

encoding_cache = EncodingCache()

def get_settings():
	global ENCODINGS_NAME, ENCODINGS_CODE
	settings = sublime.load_settings('ConvertToUTF8.sublime-settings')
	encoding_list = settings.get('encoding_list', [])
	ENCODINGS_NAME = [pair[0] for pair in encoding_list]
	ENCODINGS_CODE = [pair[1] for pair in encoding_list]
	encoding_cache.set_max_size(settings.get('max_cache_size', 100))
	SETTINGS['max_detect_lines'] = settings.get('max_detect_lines', 600)
	SETTINGS['preview_action'] = settings.get('preview_action', 'no_action')
	SETTINGS['default_encoding_on_create'] = settings.get('default_encoding_on_create', '')
	SETTINGS['convert_on_load'] = settings.get('convert_on_load', 'always')
	SETTINGS['convert_on_save'] = settings.get('convert_on_save', 'always')

def init_settings():
	get_settings()
	sublime.load_settings('ConvertToUTF8.sublime-settings').add_on_change('get_settings', get_settings)

init_settings()

def detect(view, file_name, encoding):
	if not os.path.exists(file_name):
		return
	if not encoding.endswith(' with BOM'):
		encoding = encoding_cache.pop(file_name)
	if encoding:
		sublime.set_timeout(lambda: init_encoding_vars(view, encoding, detect_on_fail=True), 0)
		return
	sublime.set_timeout(lambda: view.set_status('origin_encoding', 'Detecting encoding, please wait...'), 0)
	detector = UniversalDetector()
	cnt = SETTINGS['max_detect_lines']
	fp = file(file_name, 'rb')
	for line in fp:
		# cut MS-Windows CR code
		line = line.replace('\r','')
		detector.feed(line)
		cnt -= 1
		if detector.done or cnt == 0:
			break
	fp.close()
	detector.close()
	encoding = detector.result['encoding']
	confidence = detector.result['confidence']
	sublime.set_timeout(lambda: check_encoding(view, encoding, confidence), 0)

def check_encoding(view, encoding, confidence):
	if not encoding or confidence < 0.8:
		view_encoding = view.encoding()
		if view_encoding == view.settings().get('fallback_encoding'):
			# show error only when the ST2 can't detect the encoding either
			view.set_status('origin_encoding', 'Encoding can not be detected, please choose one manually. (%s/%.2f)' % (encoding, confidence))
			show_selection(view)
			return
		else:
			# using encoding detected by ST2
			encoding = view_encoding
	else:
		encoding = encoding.upper()
	if encoding == 'BIG5':
		encoding = 'BIG5-HKSCS'
	elif encoding == 'GB2312':
		encoding = 'GBK'
	init_encoding_vars(view, encoding)

def show_encoding_status(view):
	encoding = view.settings().get('force_encoding')
	if not encoding:
		encoding = view.settings().get('origin_encoding')
	view.set_status('origin_encoding', encoding)

def init_encoding_vars(view, encoding, run_convert=True, stamp=None, detect_on_fail=False):
	if not encoding:
		return
	view.settings().set('origin_encoding', encoding)
	show_encoding_status(view)
	if encoding in SKIP_ENCODINGS or encoding == view.encoding():
		encoding_cache.pop(view.file_name())
		return
	view.settings().set('in_converting', True)
	if run_convert:
		if stamp == None:
			stamp = '%r' % time.time()
		translate_tabs_to_spaces = view.settings().get('translate_tabs_to_spaces')
		view.settings().set('translate_tabs_to_spaces', False)
		view.run_command('convert_to_utf8', {'detect_on_fail': detect_on_fail, 'stamp': stamp})
		view.settings().set('translate_tabs_to_spaces', translate_tabs_to_spaces)

def clean_encoding_vars(view):
	view.settings().erase('in_converting')
	view.settings().erase('origin_encoding')
	view.erase_status('origin_encoding')
	view.set_scratch(False)
	encoding_cache.pop(view.file_name())

def remove_reverting(file_name):
	while file_name in REVERTING_FILES:
		REVERTING_FILES.remove(file_name)

class EncodingSelection(threading.Thread):
	def __init__(self, view):
		threading.Thread.__init__(self)
		self.view = view

	def run(self):
		sublime.set_timeout(self.show_panel, 0)

	def show_panel(self):
		window = self.view.window()
		if window:
			window.show_quick_panel(ENCODINGS_NAME, self.on_done)

	def on_done(self, selected):
		if selected == -1:
			clean_encoding_vars(self.view)
		else:
			init_encoding_vars(self.view, ENCODINGS_CODE[selected])

def show_selection(view):
	EncodingSelection(view).start()

stamps = {}

class ConvertToUtf8Command(sublime_plugin.TextCommand):
	def run(self, edit, encoding=None, stamp=None, detect_on_fail=False):
		view = self.view
		if encoding:
			view.settings().set('force_encoding', encoding)
			origin_encoding = view.settings().get('origin_encoding')
			# convert only when ST2 can't load file properly
			run_convert = (view.encoding() == view.settings().get('fallback_encoding'))
			if origin_encoding:
				if origin_encoding == encoding:
					return
				view.set_scratch(False)
				run_convert = False
			init_encoding_vars(view, encoding, run_convert, stamp)
			return
		else:
			encoding = view.settings().get('origin_encoding')
		if not encoding:
			return
		file_name = view.file_name()
		if not (file_name and os.path.exists(file_name)):
			return
		# try fast decode
		fp = None
		try:
			fp = codecs.open(file_name, 'rb', encoding, errors='strict')
			contents = fp.read()
		except UnicodeDecodeError, e:
			if detect_on_fail:
				detect(view, file_name, view.encoding())
				return
			if CONFIRM_IS_AVAILABLE:
				if sublime.ok_cancel_dialog('Errors occurred while converting %s file with %s encoding.\n\n'
						'Continue to load this file using %s encoding (malformed data will be replaced by a marker)?'
						'\n\nPress "Cancel" to choose another encoding manually.' %
						(os.path.basename(file_name), encoding, encoding)):
					fp.close()
					fp = codecs.open(file_name, 'rb', encoding, errors='replace')
					contents = fp.read()
				else:
					show_selection(view)
					return
			else:
				view.set_status('origin_encoding', 'Errors occurred while converting %s file with %s encoding' %
						(os.path.basename(file_name), encoding))
				show_selection(view)
				return
		finally:
			if fp:
				fp.close()
		encoding_cache.set(file_name, encoding)
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
		stamps[file_name] = stamp
		sublime.status_message('%s -> UTF8' % encoding)

	def description(self):
		encoding = self.view.settings().get('origin_encoding')
		if not encoding:
			return
		return '%s -> UTF8' % encoding

	def is_enabled(self):
		return self.view.encoding() != 'Hexadecimal'

class ConvertFromUtf8Command(sublime_plugin.TextCommand):
	def run(self, edit):
		view = self.view
		encoding = view.settings().get('force_encoding')
		if not encoding:
			encoding = view.settings().get('origin_encoding')
		file_name = view.file_name()
		if not encoding or encoding == 'UTF-8':
			encoding_cache.pop(file_name)
			return
		fp = None
		try:
			fp = file(file_name, 'rb')
			contents = codecs.EncodedFile(fp, encoding, 'UTF-8').read()
		except UnicodeEncodeError, e:
			sublime.error_message('Can not convert file encoding of %s to %s, it was saved as UTF-8 instead.' %
					(os.path.basename(file_name), encoding))
			return
		finally:
			if fp:
				fp.close()
		fp = file(file_name, 'wb')
		fp.write(contents)
		fp.close()
		encoding_cache.set(file_name, encoding)
		view.settings().set('prevent_detect', True)
		sublime.status_message('UTF8 -> %s' % encoding)

	def description(self):
		encoding = self.view.settings().get('origin_encoding')
		if not encoding:
			return
		return 'UTF8 -> %s' % encoding

class ConvertToUTF8Listener(sublime_plugin.EventListener):
	def check_clones(self, view):
		clone_numbers = view.settings().get('clone_numbers', 0)
		if clone_numbers:
			check_times = view.settings().get('check_times', clone_numbers)
			if check_times:
				view.settings().set('check_times', check_times - 1)
				return True
			view.settings().erase('check_times')
		return False

	def on_new(self, view):
		if SETTINGS['default_encoding_on_create']:
			init_encoding_vars(view, SETTINGS['default_encoding_on_create'], False)

	def on_clone(self, view):
		clone_numbers = view.settings().get('clone_numbers', 0)
		view.settings().set('clone_numbers', clone_numbers + 1)
		encoding = view.settings().get('origin_encoding')
		if encoding:
			view.set_status('origin_encoding', encoding)

	def on_close(self, view):
		clone_numbers = view.settings().get('clone_numbers', 0)
		if clone_numbers:
			view.settings().set('clone_numbers', clone_numbers - 1)
		else:
			remove_reverting(view.file_name())

	def on_load(self, view):
		if view.encoding() == 'Hexadecimal':
			return
		file_name = view.file_name()
		if not file_name:
			return
		if self.check_clones(view):
			return
		encoding = view.settings().get('origin_encoding')
		if encoding and not view.get_status('origin_encoding'):
			view.set_status('origin_encoding', encoding)
			# file is reloading
			if view.settings().get('prevent_detect'):
				if view.is_dirty():
					# changes have not been saved
					sublime.set_timeout(lambda: self.on_deactivated(view), 0)
					return
				else:
					# treat as a new file
					sublime.set_timeout(lambda: self.clean_reload(view, file_name), 250)
					return
			else:
				return
		if SETTINGS['convert_on_load'] == 'never':
			return
		self.perform_action(view, file_name, 5)

	def on_activated(self, view):
		if view.is_loading():
			return
		if view.encoding() == 'Hexadecimal':
			return
		file_name = view.file_name()
		if not file_name:
			return
		if self.check_clones(view):
			return
		if view.settings().get('origin_encoding'):
			return
		if SETTINGS['convert_on_load'] == 'never':
			return
		if view.settings().get('is_preview'):
			self.perform_action(view, file_name, 3)

	def is_preview(self, view):
		window = view.window()
		if not window:
			return True
		view_index = window.get_view_index(view)
		return view_index[1] == -1

	def clean_reload(self, view, file_name):
		window = view.window()
		if not window:
			sublime.set_timeout(lambda: self.clean_reload(view, file_name), 100)
			return
		for v in window.views():
			if v.file_name() == file_name:
				v.settings().erase('prevent_detect')
		encoding = view.encoding()
		threading.Thread(target=lambda: detect(view, file_name, encoding)).start()

	def perform_action(self, view, file_name, times):
		if SETTINGS['preview_action'] != 'convert_and_open' and self.is_preview(view):
			if times > 0:
				# give it another chance before everything is ready
				sublime.set_timeout(lambda: self.perform_action(view, file_name, times - 1), 100)
				return
			view.settings().set('is_preview', True)
			return
		view.settings().erase('is_preview')
		encoding = view.encoding()
		threading.Thread(target=lambda: detect(view, file_name, encoding)).start()

	def on_modified(self, view):
		encoding = view.encoding()
		if encoding == 'Hexadecimal':
			return
		file_name = view.file_name()
		if not file_name or view.is_loading():
			return
		if not view.settings().get('in_converting'):
			if view.settings().get('is_preview'):
				view.settings().erase('is_preview')
				detect(view, file_name, encoding)
			return
		if self.check_clones(view):
			return
		command = view.command_history(0)
		command1 = view.command_history(1)
		if command == (None, None, 0):
			if command1[0] == 'convert_to_utf8':
				view.run_command('redo')
		elif command[0] == 'convert_to_utf8':
			if stamps.has_key(file_name):
				if stamps[file_name] == command[1].get('stamp'):
					view.set_scratch(True)
		elif command[0] == 'revert':
			if command1 == (None, None, 0):
				# on_modified will be invoked twice for each revert
				if file_name not in REVERTING_FILES:
					REVERTING_FILES.insert(0, file_name)
					return
				remove_reverting(file_name)
				if view.settings().get('prevent_detect'):
					sublime.set_timeout(lambda: self.undo_me(view), 0)
				else:
					threading.Thread(target=lambda: detect(view, file_name, encoding)).start()
		else:
			view.set_scratch(False)

	def undo_me(self, view):
		view.settings().erase('prevent_detect')
		view.run_command('undo')
		if view.settings().get('revert_to_scratch'):
			view.set_scratch(True)

	def on_deactivated(self, view):
		if view.settings().get('prevent_detect'):
			remove_reverting(view.file_name())
			view.settings().set('revert_to_scratch', not view.is_dirty())
			view.run_command('revert')

	def on_pre_save(self, view):
		if view.encoding() == 'Hexadecimal':
			return
		force_encoding = view.settings().get('force_encoding')
		if force_encoding == 'UTF-8':
			view.set_encoding(force_encoding)
			return
		if not view.settings().get('in_converting'):
			return
		if self.check_clones(view):
			return
		view.set_encoding('UTF-8')

	def on_post_save(self, view):
		view_encoding = view.encoding()
		if view_encoding == 'Hexadecimal':
			return
		if not view.settings().get('in_converting'):
			return
		if self.check_clones(view):
			return
		file_name = view.file_name()
		if stamps.has_key(file_name):
			del stamps[file_name]
		if SETTINGS['convert_on_save'] == 'never':
			return
		# file was saved with other encoding
		if view_encoding != 'UTF-8':
			clean_encoding_vars(view)
			return
		view.run_command('convert_from_utf8')
