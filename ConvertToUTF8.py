# -*- coding: utf-8 -*-

import sublime, sublime_plugin
import sys
import os
if sys.version_info < (3, 0):
	from chardet.universaldetector import UniversalDetector
	NONE_COMMAND = (None, None, 0)
	ST3 = False
else:
	from .chardet.universaldetector import UniversalDetector
	NONE_COMMAND = ('', None, 0)
	ST3 = True
import codecs
import threading
import json
import time
import hashlib
import shutil

SKIP_ENCODINGS = ('ASCII', 'UTF-8', 'UTF-16LE', 'UTF-16BE')
SUPERSETS = {
	'GB2312': 'GBK',
	'GBK': 'GB18030',
	'BIG5': 'CP950', # CP950 is common in Taiwan
	'CP950': 'BIG5-HKSCS' # HK official Big5 variant
	'CP949': 'EUC-KR' # CP949 is a superset of euc-kr!
}

SETTINGS = {}
REVERTING_FILES = []

CONFIRM_IS_AVAILABLE = ('ok_cancel_dialog' in dir(sublime))

ENCODINGS_NAME = []
ENCODINGS_CODE = []

class EncodingCache(object):
	def __init__(self):
		self.file = os.path.join(sublime.packages_path(), 'User', 'encoding_cache.json')
		self.cache = []
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
		if len(self.cache) > self.max_size:
			self.dirty = True
			del self.cache[self.max_size:]

	def set_max_size(self, max_size):
		self.max_size = max_size
		self.shrink()

	def load(self):
		if not os.path.exists(self.file):
			return
		fp = open(self.file, 'r')
		self.cache = json.load(fp)
		fp.close()
		if len(self.cache) > 0:
			if 'file' in self.cache[0]:
				# old style cache
				new_cache = []
				for item in self.cache:
					new_cache.append({
						item['file']: item['encoding']
					})
				self.cache = new_cache
				self.dirty = True

	def save(self):
		self.shrink()
		fp = open(self.file, 'w')
		json.dump(self.cache, fp)
		fp.close()
		self.dirty = False

	def pop(self, file_name):
		for item in self.cache:
			if file_name in item:
				self.cache.remove(item)
				self.dirty = True
				return item.get(file_name)
		return None

	def set(self, file_name, encoding):
		if self.max_size < 1:
			return
		self.pop(file_name)
		self.cache.insert(0, {
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
	SETTINGS['lazy_reload'] = settings.get('lazy_reload', True)

def get_setting(view, key):
	# read project specific settings first
	return view.settings().get(key, SETTINGS[key]);

TMP_DIR = None

def get_temp_name(name):
	if not name:
		return None
	name = name.encode('UTF-8')
	return hashlib.md5(name).hexdigest()

def clean_temp_folder():
	tmp_files = os.listdir(TMP_DIR)
	for win in sublime.windows():
		for view in win.views():
			file_name = view.file_name()
			tmp_name = get_temp_name(file_name)
			if tmp_name in tmp_files:
				if not view.is_dirty():
					tmp_file = os.path.join(TMP_DIR, tmp_name)
					# check mtime
					mtime1 = os.path.getmtime(file_name)
					mtime2 = os.path.getmtime(tmp_file)
					if mtime1 != mtime2:
						# file was changed outside
						view.settings().erase('prevent_detect')
						continue
					shutil.move(tmp_file, file_name)
				tmp_files.remove(tmp_name)
	for tmp_name in tmp_files:
		tmp_file = os.path.join(TMP_DIR, tmp_name)
		os.unlink(tmp_file)

def init_settings():
	global encoding_cache, TMP_DIR
	encoding_cache = EncodingCache()
	get_settings()
	sublime.load_settings('ConvertToUTF8.sublime-settings').add_on_change('get_settings', get_settings)
	TMP_DIR = os.path.join(sublime.packages_path(), 'User', 'c2u_tmp')
	if not os.path.exists(TMP_DIR):
		os.mkdir(TMP_DIR)

def setup_views():
	clean_temp_folder()
	# check existing views
	for win in sublime.windows():
		for view in win.views():
			if get_setting(view, 'convert_on_load') == 'never':
				break
			if view.is_dirty() or view.settings().get('origin_encoding'):
				show_encoding_status(view)
				continue
			file_name = view.file_name()
			cnt = get_setting(view, 'max_detect_lines')
			threading.Thread(target=lambda: detect(view, file_name, cnt)).start()

def plugin_loaded():
	init_settings()
	setup_views()

def wait_for_ready():
	if sublime.windows():
		setup_views()
	else:
		sublime.set_timeout(wait_for_ready, 100)

if not ST3:
	init_settings()
	wait_for_ready()

def detect(view, file_name, cnt):
	if not file_name or not os.path.exists(file_name):
		return
	encoding = encoding_cache.pop(file_name)
	if encoding:
		sublime.set_timeout(lambda: init_encoding_vars(view, encoding, detect_on_fail=True), 0)
		return
	sublime.set_timeout(lambda: view.set_status('origin_encoding', 'Detecting encoding, please wait...'), 0)
	detector = UniversalDetector()
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
	confidence = detector.result['confidence']
	sublime.set_timeout(lambda: check_encoding(view, encoding, confidence), 0)

def check_encoding(view, encoding, confidence):
	view_encoding = view.encoding()
	result = 'Detected {0} vs {1} with {2:.0%} confidence'.format(encoding, view_encoding, confidence) if encoding else 'Encoding can not be detected'
	view.set_status('origin_encoding', result)
	print(result)
	not_detected = not encoding or confidence < 0.95 or encoding == view_encoding
	# ST can't detect the encoding
	if view_encoding in ('Undefined', view.settings().get('fallback_encoding')):
		if not_detected:
			show_selection(view)
			return
	else:
		if not_detected:
			# using encoding detected by ST
			encoding = view_encoding
		else:
			show_selection(view, [
				['{0} ({1:.0%})'.format(encoding, confidence), encoding],
				['{0}'.format(view_encoding), view_encoding]
			])
			return
	init_encoding_vars(view, encoding)

def show_encoding_status(view):
	encoding = view.settings().get('force_encoding')
	if not encoding:
		encoding = view.settings().get('origin_encoding')
		if not encoding:
			return
	view.set_status('origin_encoding', encoding)

def init_encoding_vars(view, encoding, run_convert=True, stamp=None, detect_on_fail=False):
	if not encoding:
		return
	view.settings().set('origin_encoding', encoding)
	show_encoding_status(view)
	if encoding in SKIP_ENCODINGS or encoding == view.encoding():
		encoding_cache.set(view.file_name(), encoding)
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
	def __init__(self, view, names, codes):
		threading.Thread.__init__(self)
		self.view = view
		self.names = names
		self.codes = codes

	def run(self):
		sublime.set_timeout(self.show_panel, 0)

	def show_panel(self):
		window = self.view.window()
		if window:
			window.show_quick_panel(self.names, self.on_done)

	def on_done(self, selected):
		if selected == -1:
			clean_encoding_vars(self.view)
		else:
			init_encoding_vars(self.view, self.codes[selected])

def show_selection(view, encoding_list = None):
	if encoding_list:
		names = [pair[0] for pair in encoding_list]
		codes = [pair[1] for pair in encoding_list]
	else:
		names = ENCODINGS_NAME
		codes = ENCODINGS_CODE
	EncodingSelection(view, names, codes).start()

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
	def get_branch(self, platform, arch):
		return [{
			'linux-x64': 'master',
			'linux-x32': 'x32',
		}, {
			'linux-x64': 'linux-x64',
			'linux-x32': 'linux-x32',
			'osx-x64': 'osx',
		}][ST3].get(platform + '-' + arch)

	def run(self, edit, encoding, file_name):
		self.view.set_name('ConvertToUTF8 Instructions')
		self.view.set_scratch(True)
		self.view.settings().set("word_wrap", True)
		msg = 'Oops! The file {0} is detected as {1} which is not supported by your Sublime Text.\n\nPlease check whether it is in the list of Python\'s Standard Encodings (http://docs.python.org/library/codecs.html#standard-encodings) or not.\n\nIf yes, '.format(file_name, encoding)
		branch = self.get_branch(sublime.platform(), sublime.arch())
		if branch:
			ver = '33' if ST3 else '26'
			msg = msg + 'please install Codecs{0} (https://github.com/seanliang/Codecs{0}/tree/{1}) and restart Sublime Text to make ConvertToUTF8 work properly. If it is still not working, '.format(ver, branch)

		import platform
		msg = msg + 'please kindly send the following information to sunlxy (at) yahoo.com:\n====== Debug Information ======\nVersion: {0}-{1}\nPlatform: {2}\nPath: {3}\nEncoding: {4}\n'.format(
			sublime.version(), sublime.arch(), platform.platform(), sys.path, encoding
		)
		self.view.insert(edit, 0, msg)
		self.view.set_read_only(True)
		self.view.window().focus_view(self.view)

class ConvertToUtf8Command(sublime_plugin.TextCommand):
	def run(self, edit, encoding=None, stamp=None, detect_on_fail=False):
		view = self.view
		if encoding:
			view.settings().set('force_encoding', encoding)
			origin_encoding = view.settings().get('origin_encoding')
			# convert only when ST can't load file properly
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
			view.window().new_file().run_command('py_instruction', {'encoding': encoding, 'file_name': file_name})
			return
		except UnicodeDecodeError as e:
			if detect_on_fail:
				detect(view, file_name, get_setting(view, 'max_detect_lines'))
				return
			superset = SUPERSETS.get(encoding)
			if superset:
				print('Try encoding {0} instead of {1}.'.format(superset, encoding))
				init_encoding_vars(view, superset, True, stamp)
				return
			if CONFIRM_IS_AVAILABLE:
				if sublime.ok_cancel_dialog(u'Errors occurred while converting {0} with {1} encoding.\n\n'
						'WARNING: Continue to load this file using {1}, malformed data will be ignored.'
						'\n\nPress "Cancel" to choose another encoding manually.'.format
						(os.path.basename(file_name), encoding)):
					fp.close()
					fp = codecs.open(file_name, 'rb', encoding, errors='ignore')
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
		# write content to temporary file
		tmp_name = os.path.join(TMP_DIR, get_temp_name(file_name))
		fp = open(tmp_name, 'wb')
		fp.write(contents)
		fp.close()
		if not get_setting(view, 'lazy_reload'):
			# os.rename has "Invalid cross-device link" issue
			shutil.move(tmp_name, file_name)
		else:
			# copy the timestamp from original file
			mtime = os.path.getmtime(file_name)
			os.utime(tmp_name, (mtime, mtime))
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
		if get_setting(view, 'default_encoding_on_create'):
			init_encoding_vars(view, get_setting(view, 'default_encoding_on_create'), False)

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
		encoding = view.encoding()
		if encoding == 'Hexadecimal' or encoding.endswith(' BOM'):
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
		if get_setting(view, 'convert_on_load') == 'never':
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
		cnt = get_setting(view, 'max_detect_lines')
		threading.Thread(target=lambda: detect(view, file_name, cnt)).start()

	def perform_action(self, view, file_name, times):
		if get_setting(view, 'preview_action') != 'convert_and_open' and self.is_preview(view):
			if times > 0:
				# give it another chance before everything is ready
				sublime.set_timeout(lambda: self.perform_action(view, file_name, times - 1), 100)
				return
			view.settings().set('is_preview', True)
			return
		view.settings().erase('is_preview')
		cnt = get_setting(view, 'max_detect_lines')
		threading.Thread(target=lambda: detect(view, file_name, cnt)).start()

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
				detect(view, file_name, get_setting(view, 'max_detect_lines'))
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
					cnt = get_setting(view, 'max_detect_lines')
					threading.Thread(target=lambda: detect(view, file_name, cnt)).start()
		else:
			view.set_scratch(False)

	def undo_me(self, view):
		view.settings().erase('prevent_detect')
		view.run_command('undo')
		# st3 will reload file immediately
		if view.settings().get('revert_to_scratch') or (ST3 and not get_setting(view, 'lazy_reload')):
			view.set_scratch(True)

	def on_deactivated(self, view):
		# st2 will reload file when on_deactivated
		if view.settings().get('prevent_detect'):
			file_name = view.file_name()
			if get_setting(view, 'lazy_reload'):
				tmp_name = os.path.join(TMP_DIR, get_temp_name(file_name))
				shutil.move(tmp_name, file_name)
			remove_reverting(file_name)
			view.settings().set('revert_to_scratch', not view.is_dirty())
			# make ST stop asking about reloading
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
		if get_setting(view, 'convert_on_save') == 'never':
			return
		# file was saved with other encoding
		if view_encoding != 'UTF-8':
			clean_encoding_vars(view)
			return
		view.run_command('convert_from_utf8')
