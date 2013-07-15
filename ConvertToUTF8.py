# -*- coding: utf-8 -*-

import sublime, sublime_plugin
import sys
import os
if sys.version_info < (3, 0):
	from chardet.universaldetector import UniversalDetector
	NONE_COMMAND = (None, None, 0)
else:
	from .chardet.universaldetector import UniversalDetector
	NONE_COMMAND = ('', None, 0)
import codecs
import threading
import json
import time

SKIP_ENCODINGS = ('ASCII', 'UTF-8', 'UTF-16LE', 'UTF-16BE')

SETTINGS = {}
REVERTING_FILES = []

CONFIRM_IS_AVAILABLE = ('ok_cancel_dialog' in dir(sublime))

ENCODINGS_NAME = []
ENCODINGS_CODE = []

PKG_PATH = None

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
		fp = open(self.cache_file, 'r')
		self.encoding_cache = json.load(fp)
		fp.close()
		if len(self.encoding_cache) > 0:
			if 'file' in self.encoding_cache[0]:
				# old style cache
				new_cache = []
				for item in self.encoding_cache:
					new_cache.append({
						item['file']: item['encoding']
					})
				self.encoding_cache = new_cache
				self.dirty = True

	def save(self):
		self.shrink()
		fp = open(self.cache_file, 'w')
		json.dump(self.encoding_cache, fp)
		fp.close()
		self.dirty = False

	def pop(self, file_name):
		for item in self.encoding_cache:
			if file_name in item:
				self.encoding_cache.remove(item)
				self.dirty = True
				return item.get(file_name)
		return None

	def set(self, file_name, encoding):
		if self.max_size < 1:
			return
		self.pop(file_name)
		self.encoding_cache.insert(0, {
			file_name: encoding
		})
		self.dirty = True

encoding_cache = None

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
	global encoding_cache, PKG_PATH
	encoding_cache = EncodingCache()
	PKG_PATH = os.path.join(sublime.packages_path(), 'ConvertToUTF8')
	get_settings()
	sublime.load_settings('ConvertToUTF8.sublime-settings').add_on_change('get_settings', get_settings)

if 'sublime_api' in dir(sublime):
	def plugin_loaded():
		init_settings()
else:
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
	fp = open(file_name, 'rb')
	for line in fp:
		# cut MS-Windows CR code
		line = line.replace(b'\r',b'')
		detector.feed(line)
		cnt -= 1
		if detector.done or cnt == 0:
			break
	fp.close()
	detector.close()
	encoding = detector.result['encoding']
	if encoding:
		encoding = encoding.upper()
		if encoding == 'BIG5':
			encoding = 'BIG5-HKSCS'
		elif encoding == 'GB2312':
			encoding = 'GBK'
	confidence = detector.result['confidence']
	sublime.set_timeout(lambda: check_encoding(view, encoding, confidence), 0)

def check_encoding(view, encoding, confidence):
	view.set_status('origin_encoding', ('Detected {0} with {1:.0%} confidence'.format(encoding, confidence)) if encoding else 'Encoding can not be detected')
	if not encoding or confidence < 0.95:
		view_encoding = view.encoding()
		if view_encoding == view.settings().get('fallback_encoding'):
			# show error only when the ST2 can't detect the encoding either
			show_selection(view)
			return
		else:
			# using encoding detected by ST2
			if view_encoding == 'Undefined':
				view_encoding = 'ASCII'
			encoding = view_encoding
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
			stamp = '{0}'.format(time.time())
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

class ReloadWithEncoding(threading.Thread):
    def __init__(self, view, encoding):
        threading.Thread.__init__(self)
        self.view = view
        self.encoding = encoding

    def run(self):
        sublime.set_timeout(self.reload, 0)

    def reload(self):
        init_encoding_vars(self.view, self.encoding)

def reload_encoding(view, encoding):
    ReloadWithEncoding(view, encoding).start()

stamps = {}

class ShowEncodingSelectionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        show_selection(self.view)

class ReloadWithEncodingCommand(sublime_plugin.TextCommand):
    def run(self, edit, encoding):
        reload_encoding(self.view, encoding)

class PyInstructionCommand(sublime_plugin.TextCommand):
	def run(self, edit, encoding):
		self.view.set_name('ConvertToUTF8 Instructions')
		self.view.set_scratch(True)
		self.view.settings().set("word_wrap", True)
		fp = open(os.path.join(PKG_PATH, 'python26.txt'), 'r')
		msg = fp.read()
		fp.close()
		msg += 'Version: {0}\nPlatform: {1}\nArch: {2}\nPath: {3}\nEncoding: {4}\n'.format(
			sublime.version(), sublime.platform(), sublime.arch(), sys.path, encoding
		)
		self.view.insert(edit, 0, msg)

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
		except LookupError as e:
			clean_encoding_vars(view)
			sublime.error_message('Encoding {0} is not supported.'.format(encoding))
			view.window().new_file().run_command('py_instruction', {'encoding': encoding})
			return
		except UnicodeDecodeError as e:
			if detect_on_fail:
				detect(view, file_name, view.encoding())
				return
			if CONFIRM_IS_AVAILABLE:
				if sublime.ok_cancel_dialog(u'Errors occurred while converting {0} with {1} encoding.\n\n'
						'Continue to load this file using {1} (malformed data will be replaced by a marker)?'
						'\n\nPress "Cancel" to choose another encoding manually.'.format
						(os.path.basename(file_name), encoding)):
					fp.close()
					fp = codecs.open(file_name, 'rb', encoding, errors='replace')
					contents = fp.read()
				else:
					show_selection(view)
					return
			else:
				view.set_status('origin_encoding', u'Errors occurred while converting {0} with {1} encoding'.format
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
		view.replace(edit, regions, contents)
		sel.clear()
		for x in rs:
			sel.add(sublime.Region(x.a, x.b))
		view.set_viewport_position(vp)
		stamps[file_name] = stamp
		sublime.status_message('{0} -> UTF8'.format(encoding))

	def description(self):
		encoding = self.view.settings().get('origin_encoding')
		if not encoding:
			return
		return '{0} -> UTF8'.format(encoding)

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
			fp = open(file_name, 'rb')
			contents = codecs.EncodedFile(fp, encoding, 'UTF-8').read()
		except (LookupError, UnicodeEncodeError) as e:
			sublime.error_message(u'Can not convert file encoding of {0} to {1}, it was saved as UTF-8 instead:\n\n{2}'.format
					(os.path.basename(file_name), encoding, e))
			return
		finally:
			if fp:
				fp.close()
		fp = open(file_name, 'wb')
		fp.write(contents)
		fp.close()
		encoding_cache.set(file_name, encoding)
		view.settings().set('prevent_detect', True)
		sublime.status_message('UTF8 -> {0}'.format(encoding))

	def description(self):
		encoding = self.view.settings().get('origin_encoding')
		if not encoding:
			return
		return 'UTF8 -> {0}'.format(encoding)

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
		if view.settings().get('is_preview'):
			self.perform_action(view, view.file_name(), 3)

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
		if command == NONE_COMMAND:
			if command1[0] == 'convert_to_utf8':
				view.run_command('redo')
		elif command[0] == 'convert_to_utf8':
			if file_name in stamps:
				if stamps[file_name] == command[1].get('stamp'):
					view.set_scratch(True)
		elif command[0] == 'revert':
			if command1 == NONE_COMMAND:
				# on_modified will be invoked twice for each revert
				if file_name not in REVERTING_FILES:
					REVERTING_FILES.insert(0, file_name)
					return
				remove_reverting(file_name)
				if view.settings().get('prevent_detect'):
					sublime.set_timeout(lambda: self.undo_me(view), 0)
				else:
					# file was modified outside
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
		if file_name in stamps:
			del stamps[file_name]
		if SETTINGS['convert_on_save'] == 'never':
			return
		# file was saved with other encoding
		if view_encoding != 'UTF-8':
			clean_encoding_vars(view)
			return
		view.run_command('convert_from_utf8')
