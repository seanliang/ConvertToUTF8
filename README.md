Description (中文说明见README.zh_CN.md)
------------------
This Sublime Text 2 plug-in aims to help people view and edit text files which encodings are not supported currently by Sublime Text, especially for CJK users who using GB2312, GBK, BIG5, EUC-KR, EUC-JP, etc.

It will:
* finds the proper encoding of current file when a file is loaded
* converts and reloads the file content for user viewing and editing
* converts the file content to original encoding when the file is saved

Installation
------------------
Using [Package Control](http://wbond.net/sublime_packages/package_control) to find, install and upgrade *ConvertToUTF8* is the recommended method to install this plug-in.

Otherwise, you can download this repository as a zip file, unzip it, and rename the new folder to *ConvertToUTF8*, then move this folder to *Packages* folder of Sublime Text (You can find the *Packages* folder by clicking "Preferences > Browse Packages" menu entry in Sublime Text).

Configuration
------------------
Please check [Configuration file](ConvertToUTF8.sublime-settings) for details.
* max_cache_size: maximum size of encoding cache, 0 means no cache (default: 100)
* max_detect_lines: maximum lines to detect, 0 means unlimited (default: 600)
* convert_on_load: if set to never, the file will not be decoded when opening (default: always)
* convert_on_save: if set to never, the file will be encoded as UTF-8 when saving (default: always)

Usage
------------------
The plug-in will detect the encoding of opening files, then convert them to UTF-8 for viewing and editing, and convert them back to original encoding when saving.

ConvertToUTF8 creates an entry "Set File Encoding to" under "File" menu. You can use it to translate between different encodings. For example, you can open a UTF-8 file, and save it to GBK, and vice versa.

Note:
* if "convert_on_load" is set to never, ConvertToUTF8 will decode the file using selected encoding
* if "convert_on_save" is set to never, the file will *NEVER* be saved to selected encoding
* please do not edit the file before the encoding detection process is finished
* please try either increasing the value of max_detect_lines or set the encoding manually if the detection result is not accurate


Q & A
------------------
* Q: Which encodings are supported?

  A: Any encoding your system supported should be fine.

* Q: Why does the content become a mess when the window is re-activated?

  A: This is caused by reloading and has been fixed, please update your *ConvertToUTF8* to latest version.

* Q: Why does ST2 ask me that file "Has changed on disk. Do you want to reload it?" when the window is re-activated.

  A: Same reason as above. Please choose "Cancel" if you have unsaved changes to the file.

* Q: When saving the file, Sublime Text tells me the file is saved as UTF-8, why?

  A: Don't worry, the plug-in will convert your file to original encoding.

Contact me
------------------
Please visit me if you have any question or suggestion at: http://weibo.com/seanliang
