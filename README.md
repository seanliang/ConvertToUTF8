Description (中文说明见README.zh_CN.md)
------------------
This Sublime Text 2 plug-in aims to help people view and edit text files which encodings are not supported currently by Sublime Text, especially for CJK users who using GB2312, GBK, BIG5, etc.

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
* convert_on_load: if set to never, the file will not be decoded when opening
* convert_on_save: if set to never, the file will be encoded as UTF-8 when saving

Q & A
------------------
* Q: Which encodings are supported?

  A: Any encoding your system supported should be fine.

* Q: Why does the content become a mess when the window is re-activated?

  A: This is caused by reloading and has been fixed, please update your *ConvertToUTF8* to latest version.

* Q: What does "Decode Failed: [123, 456]" in status bar mean?

  A: It means the line numbers which can't be decode correctly, those lines will be decoded to ISO-8859-1.

* Q: When saving the file, Sublime Text tells me the file is saved as UTF-8, why?

  A: Don't worry, the plug-in will convert your file to original encoding.

Contact me
------------------
Please visit me if you have any question or suggestion at: http://weibo.com/seanliang
