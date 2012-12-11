Description (中文说明见[README.zh_CN.md](https://github.com/seanliang/ConvertToUTF8/blob/master/README.zh_CN.md))
------------------
With this plugin, you can edit and save the files which encodings are not supported by Sublime Text currently, especially for those used by CJK users, such as GB2312, GBK, BIG5, EUC-KR, EUC-JP, etc.

![ConvertToUTF8](http://dl.dropbox.com/u/31937639/ConvertToUTF8/ConvertToUTF8.gif)

Installation
------------------
Using [Package Control](http://wbond.net/sublime_packages/package_control) to find, install and upgrade *ConvertToUTF8* is the recommended method to install this plug-in.

Otherwise, you can download this repository as a zip file, unzip it, and rename the new folder to *ConvertToUTF8*, then move this folder to *Packages* folder of Sublime Text (You can find the *Packages* folder by clicking "Preferences > Browse Packages" menu entry in Sublime Text).

Your folder hierarchy should look like this:

![Folder Hierarchy](http://dl.dropbox.com/u/31937639/ConvertToUTF8/hierarchy.png)

Configuration
------------------
Please check ConvertToUTF8.sublime-settings file for details. You should save your personal settings in a file named "ConvertToUTF8.sublime-settings" under "User" folder.

* encoding_list: encoding selection list when detection is failed
* max_cache_size: maximum encoding cache size, 0 means no cache (default: 100)
* max_detect_lines: maximum detection lines, 0 means unlimited (default: 600)
* preview_action: specific the action when previewing a file, available options: no_action, convert_and_open (default: no_action)
* default_encoding_on_create: specific the default encoding for newly created file (such as "GBK"), empty value means using sublime text's "default_encoding" setting (default: empty)
* convert_on_load: enable/disable convert file content to UTF-8 when it is loaded, available options: always, never (default: always)
* convert_on_save: enable/disable convert file from UTF-8 to a specific encoding when it is saved, available options: always, never (default: always)

Usage
------------------
In most cases, this plug-in will take care of encoding issues automatically.

You can also use the "File > Set File Encoding to" menu entry to transform between different encodings. For example, you can open a UTF-8 file, and save it to GBK, and vice versa.

Note:
* if "convert_on_save" is set to never, the file will *NEVER* be saved to the selected encoding
* please do not edit the file before the encoding detection process is finished
* please try either increasing the value of max_detect_lines or set the encoding manually if the detection result is not accurate


Q & A
------------------
* Q: It is not working after installation, how do I fix it?

  A: Please try the following steps:
  1. Restart Sublime Text
  2. Make sure the plug-in folder is named "ConvertToUTF8" (skip this step if you install via "Package Control")
  3. Install Python 2.6 manually if you are running Ubuntu 64bit
<code>  
sudo add-apt-repository ppa:fkrull/deadsnakes  
sudo apt-get update  
sudo apt-get install python2.6  
sudo ln -s /usr/lib/python2.6 /PATH_TO_ST2/lib  
</code>
  4. Disable other encoding related plug-ins
  5. Contact me

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
Please send me your questions or suggestions: sunlxy (at) yahoo.com or http://weibo.com/seanliang
