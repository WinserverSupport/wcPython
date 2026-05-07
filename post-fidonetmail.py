#!/usr/bin/env python
# post-fidonetmail.py -- Example: post an FTN netmail via wcPAPI
#
# Covers what PostingMessages.wcc and fidomsg.wcc do NOT show:
# the TMsgHeader.Fido* fields required for mtFidoNetmail conferences.
#
# Sources / references:
#   wctype_h.py        -- TMsgHeader, TFidoAddress bindings
#   wctype.pas         -- field definitions, mfXxx / TFidoAddress
#   pxtype.pas         -- _obXxx FidoFlags constants
#   fidomsg.wcc        -- FidoFrom/FidoTo/FidoFlags pattern
#   PostingMessages.wcc -- AddMessage, attachment, body patterns
#   pxedit/ReadMail.pas -- UpdateMessageFidoInfo, mtFidoNetmail=3
#
# FidoFlags bit definitions (pxtype.pas _obXxx):
#   0x0001  Hold        -- hold for remote to pick up
#   0x0002  Immediate   -- call immediately after posting
#   0x0004  Direct      -- do not route, send direct
#   0x0010  KillMsg     -- delete netmail after sent
#   0x0020  KillFile    -- delete file attach after sent
#   0x0080  FileReq     -- Subject = file request list (FREQ)
#   0x0100  FileAtt     -- Subject = file attach path (FTN-style attach)
#   0x0400  Crash       -- crash mail (high priority)
#
# Attachment types:
#   WC-style:  CopyFile(src, "wc:\\temp\\" + fname)
#              msg.Attachment = fname  (short filename only)
#              AddMessage moves it from wc:\temp\ to server attach store
#
#   FTN-style: msg.Subject = full_dos_path_of_file
#              msg.FidoFlags |= 0x0100  (_obFileAtt)
#              File must exist at that path when PXECHO sends it
#
# After AddMessage, signal PXECHO to scan + export the new netmail:
#   CreateSemaFile(SemaphorePath, 0, 'NET')
#
# 500.2  26.5.7  SSI - Initial

import ctypes
import sys
import os

sys.path.insert(0, r'c:\local\wcPython')
import wcpapi
from wcpapi.wcserver_h import *
from wcpapi.wcserror_h import *
from wcpapi.wctype_h   import *
from wcpapi.wctype_constants_h import *

# ---------------------------------------------------------------------------
# FidoFlags bit constants  (from pxtype.pas _obXxx)
# ---------------------------------------------------------------------------

obHold      = 0x00000001   # Hold for pickup
obImmed     = 0x00000002   # Call immediately
obDirect    = 0x00000004   # Direct, do not route
obKillMsg   = 0x00000010   # Kill msg when sent
obKillFile  = 0x00000020   # Kill file when sent
obFileReq   = 0x00000080   # File request (subject = .REQ list)
obFileAtt   = 0x00000100   # FTN-style file attach (subject = file path)
obCrash     = 0x00000400   # Crash mail

# mtFidoNetmail conference type (wctype.pas)
mtFidoNetmail = 3

SERVER   = 'NTBBS'

# ---------------------------------------------------------------------------
# Helper: find mtFidoNetmail conference number
# ---------------------------------------------------------------------------

def find_fido_netmail_conf():
    """Return the first conference with MailType = mtFidoNetmail, or 0."""
    cd = TConfDesc()
    num = 1
    while GetConfDesc(num, ctypes.byref(cd)):
        if cd.MailType == mtFidoNetmail:
            return num
        num += 1
    return 0

# ---------------------------------------------------------------------------
# Helper: decode char array to string
# ---------------------------------------------------------------------------

def decode_wc(b):
    if isinstance(b, (bytes, bytearray)):
        return b.decode('cp437', errors='replace').rstrip('\x00').strip()
    return str(b).strip()

# ---------------------------------------------------------------------------
# post_fidonetmail
#
# Post a crash netmail from from_addr to to_addr in the FidoNetmail conference.
# from_addr / to_addr format: (zone, net, node)  or  (zone, net, node, point)
#
# attach_wc:  filename only (e.g. 'REGION54.128') -- file must be pre-copied
#             to wc:\temp\ before calling this function  (WC-style attach)
#
# attach_ftn: full DOS path (e.g. r'T:\pxw\makenl\net633.128') -- subject
#             is set to this path and obFileAtt flag is added  (FTN-style)
#
# flags:      FidoFlags to set in addition to Crash+Direct+KillMsg defaults
# ---------------------------------------------------------------------------

def post_fidonetmail(from_addr, to_addr,
                     to_name, from_name,
                     subject, body,
                     conf_num=0,
                     flags=0,
                     attach_wc='',
                     attach_ftn='',
                     semaphore_path=''):

    # Resolve conference
    if conf_num == 0:
        conf_num = find_fido_netmail_conf()
    if conf_num == 0:
        print('ERROR: no mtFidoNetmail conference found')
        return False

    msg = TMsgHeader()

    # Basic header
    msg.Conference = conf_num
    msg.From.Name  = from_name[:SIZE_USER_NAME-1]
    msg.To.Name    = to_name[:SIZE_USER_NAME-1]
    msg.Private    = 0             # FidoNetmail is not WC-private
    msg.Reference  = 0

    # FTN addresses
    msg.FidoFrom.Zone  = from_addr[0]
    msg.FidoFrom.Net   = from_addr[1]
    msg.FidoFrom.Node  = from_addr[2]
    msg.FidoFrom.Point = from_addr[3] if len(from_addr) > 3 else 0

    msg.FidoTo.Zone    = to_addr[0]
    msg.FidoTo.Net     = to_addr[1]
    msg.FidoTo.Node    = to_addr[2]
    msg.FidoTo.Point   = to_addr[3] if len(to_addr) > 3 else 0

    # Default FTN flags: Crash + Direct + KillMsg
    msg.FidoFlags = obCrash | obDirect | obKillMsg | flags

    # WC-style file attachment: file must be in wc:\temp\ already
    if attach_wc:
        msg.Attachment = os.path.basename(attach_wc)[:SIZE_ATTACH_FILE_NAME-1]

    # FTN-style file attachment: full path goes in Subject, obFileAtt flag set
    if attach_ftn:
        msg.Subject    = attach_ftn[:SIZE_MESSAGE_SUBJECT-1]
        msg.FidoFlags |= obFileAtt
    else:
        msg.Subject    = subject[:SIZE_MESSAGE_SUBJECT-1]

    # Body as string (LF-delimited) or wc:\ path
    ok = AddMessage(ctypes.byref(msg), body)
    if not ok:
        err = ctypes.GetLastError()
        print('ERROR: AddMessage failed {:08X}'.format(err))
        return False

    print('Posted netmail #{} to {} ({}:{}/{}) in conf {}'.format(
        msg.Number, to_name,
        to_addr[0], to_addr[1], to_addr[2],
        conf_num))

    # Signal PXECHO netmail scanner to export immediately
    if semaphore_path:
        CreateSemaFile(semaphore_path, 0, 'NET')
        print('  $NET.0 semaphore fired -- PXECHO will scan + export')

    return True

# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

def main():
    if not WildcatServerConnectSpecific(None, SERVER):
        print('ERROR: Cannot connect to', SERVER)
        sys.exit(1)
    if not WildcatServerCreateContext():
        print('ERROR: WildcatServerCreateContext failed')
        sys.exit(1)
    try:
        if not LoginSystem():
            print('ERROR: LoginSystem failed')
            sys.exit(1)

        # -- Example 1: simple crash netmail (Immed+Direct+KillMsg)
        #    fidomsg.wcc pattern: FidoFlags = 2+4+16 = Immed+Direct+KillMsg
        post_fidonetmail(
            from_addr = (99, 1, 1),
            to_addr   = (99, 1, 999),
            from_name = 'Winserver Support',
            to_name   = 'Hector Santos',
            subject   = 'Test FidoNetmail from wcPython',
            body      = 'This is a crash netmail posted via wcPAPI.\n\nHector\n',
            flags     = obImmed,            # add Immediate on top of Crash+Direct+KillMsg
        )

        # -- Example 2: crash netmail with WC-style attachment
        #    File must be copied to wc:\temp\ before calling AddMessage.
        #    WC moves it from wc:\temp\ to the server attach store.
        #
        #    CopyFile(src, 'wc:\\temp\\' + filename)  -- via GetText/PutText or wcPAPI
        #
        # post_fidonetmail(
        #     from_addr  = (99, 1, 1),
        #     to_addr    = (3, 712, 1321),
        #     from_name  = 'Winserver Support',
        #     to_name    = 'Terry Roati',
        #     subject    = 'Beta 24 update',
        #     body       = 'See attached.\n\nHector\n',
        #     attach_wc  = 'pxonline-beta24.zip',  # pre-copied to wc:\temp\
        # )

        # -- Example 3: FTN-style file attach (MakeNL segment pattern)
        #    Subject = file path; obFileAtt flag signals FTN file attach.
        #    PXECHO sends the file via BinkP when polling the destination.
        #
        # post_fidonetmail(
        #     from_addr  = (3, 712, 1321),
        #     to_addr    = (3, 712, 848),
        #     from_name  = 'Makenl 3.5.0',
        #     to_name    = 'Coordinator',
        #     subject    = 'REGION54.128',      # subject = FTN-style attach path
        #     body       = '',
        #     flags      = obImmed,
        #     attach_ftn = r'T:\pxw\makenl\REGION54.128',  # full path in Subject
        # )

    finally:
        WildcatServerDeleteContext()

if __name__ == '__main__':
    main()
