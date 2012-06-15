Description
------------------

This plug-in for Sublime Text 2 aims to help people view and edit text files which encoding is rather than ASCII and UTF-8, such as GB2312, GBK, BIG5, etc.

It will:
* finds the proper encoding of current file when a file is loaded
* converts and reloads the file content for user viewing and editing
* converts the file content to original encoding when the file is saved

Q & A
------------------
* Q: Which encodings are supported?
  A: Any encoding your system supported should be fine.

* Q: Why does the content become a mess when the window is re-activated?
  A: Sublime Text will reload the file when it's changed outside. Please disable the autoReloadChanged setting of Sublime Text, or re-open the file.

* Q: What does "Decode Failed: [123, 456]" in status bar mean?
  A: It means the line numbers which can't be decode correctly, those lines will be decoded to ISO-8859-1.

* Q: When saving the file, Sublime Text tells me the file is saved as UTF-8, why?
  A: Don't worry, the plug-in will convert your file to original encoding.

Contact me
------------------
Please visit me if you have any question or suggestion at: http://weibo.com/seanliang
