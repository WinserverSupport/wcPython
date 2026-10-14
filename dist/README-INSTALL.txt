wcPAPI (wcpapi) - Wildcat! Python API
========================================

Version: 10.0.500.3

This package is distributed via the AUP for manual application by
sysops/developers who want to use wcPython scripting against their
Wildcat! server (wcat-agents, wcTools, custom AI/automation scripts).
It is intentionally NOT auto-unzipped by AutoUpdate - install it
yourself when ready.

Install
-------

  pip install wcpapi-10.0.500.3-py3-none-any.whl

or, from source:

  pip install wcpapi-10.0.500.3.tar.gz

Source
------

https://github.com/WinserverSupport/wcPython

Requires Python 3.6+. Connects to your Wildcat! server via wcsrv2.dll
(the wcSDK RPC client), same mechanism as the C++/Delphi wcSDK clients.

REQUIRES wcsrv2.dll 10.0.500.3 OR LATER.

wcPAPI binds every SDK export when the package is imported, so an older
wcsrv2.dll that lacks a newer function fails at "import wcpapi" rather
than at the call.  If you see

    AttributeError: function 'WcFreeMemory' not found

your wcsrv2.dll predates this package.  Update the Wildcat! server, or
install the matching older wcPAPI.

Output string buffers
---------------------

A function that fills a char buffer you supply, for example

    WcGetUserPublicKey(userid, index, dest, destsize)

needs a real writable buffer.  Pass ctypes.create_string_buffer(n),
never a Python bytes or str object -- the DLL writes into it:

    buf = ctypes.create_string_buffer(SSH_MAX_KEY_LEN + 1)
    if WcGetUserPublicKey(userid, 1, buf, len(buf)):
        key = buf.value.decode()

