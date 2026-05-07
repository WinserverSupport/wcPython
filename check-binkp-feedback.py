#!/usr/bin/env python
# check-binkp-feedback.py -- Poll list-pxwin (conf 137) for new messages
#                            related to BinkP / beta feedback.
#
# Usage:
#   python "c:\local\claude\wcBinkp\check-binkp-feedback.py" [--reset] [--all]
#
#   --reset   Mark all current messages as read and exit (first-run baseline)
#   --all     Show all new messages, not just BinkP-related ones
#
# State: last-read message number stored in check-binkp-feedback.state
#        alongside this script.
#
# 500.2  26.5.6  SSI - Initial

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
# Config
# ---------------------------------------------------------------------------

CONFERENCES = [
    (3,   'Fidonet Netmail'),
    (137, 'list-pxwin'),
]
SERVER    = 'NTBBS'
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'check-binkp-feedback.state')

# Keywords that flag a message as BinkP-related
BINKP_KEYWORDS = [
    'binkp', 'bink', 'pxonline', 'b23', 'b22', 'b21', 'beta 23', 'beta 22',
    'tic', 'freq', 'nodelist', 'fidonet', 'ftn', 'terry',
]

TERRY_NAME = 'Terry Roati'

# ---------------------------------------------------------------------------
# State file: one line per conference "cnum=lastread"
# ---------------------------------------------------------------------------

def load_state():
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    k, v = line.split('=', 1)
                    try:
                        state[int(k)] = int(v)
                    except ValueError:
                        pass
    return state

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        for k, v in sorted(state.items()):
            f.write('{}={}\n'.format(k, v))

# ---------------------------------------------------------------------------
# Helpers (same pattern as wcat-agent.py)
# ---------------------------------------------------------------------------

def decode_wc(b):
    if isinstance(b, (bytes, bytearray)):
        return b.decode('cp437', errors='replace').rstrip('\x00').strip()
    return str(b).strip()

def get_body(msg):
    buf_size = max(msg.MsgSize + 1, 256)
    wcfn = 'wc:\\conf({})\\message({})'.format(msg.Conference, msg.Id)
    buf  = ctypes.create_string_buffer(buf_size)
    ret  = DWORD(0)
    if not GetText(wcfn, buf, buf_size, ctypes.byref(ret)):
        return ''
    return buf.raw[:ret.value].decode('cp437', errors='replace')

def get_body_by_id(cnum, msgid, buf_size=8192):
    wcfn = 'wc:\\conf({})\\message({})'.format(cnum, msgid)
    buf  = ctypes.create_string_buffer(buf_size)
    ret  = DWORD(0)
    if not GetText(wcfn, buf, buf_size, ctypes.byref(ret)):
        return ''
    return buf.raw[:ret.value].decode('cp437', errors='replace')

def is_binkp_related(from_name, subject, body):
    text = (from_name + ' ' + subject + ' ' + body).lower()
    for kw in BINKP_KEYWORDS:
        if kw in text:
            return True
    if TERRY_NAME.lower() in from_name.lower():
        return True
    return False

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    reset    = '--reset' in sys.argv
    show_all = '--all' in sys.argv

    # --state <file>: use alternate state file (so wcTaskMgr polling never
    # advances the CC session's last-read pointer; both run independently)
    global STATE_FILE
    if '--state' in sys.argv:
        idx = sys.argv.index('--state')
        if idx + 1 < len(sys.argv):
            STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      sys.argv[idx + 1])

    # Connect and login as system (full access to all conferences/private mail)
    if not WildcatServerConnectSpecific(None, SERVER):
        print('ERROR: Cannot connect to {}'.format(SERVER))
        sys.exit(1)
    if not WildcatServerCreateContext():
        print('ERROR: WildcatServerCreateContext failed')
        sys.exit(1)

    try:
        if not LoginSystem():
            print('ERROR: LoginSystem failed ({:08X})'.format(ctypes.GetLastError()))
            sys.exit(1)

        state = load_state()

        if reset:
            for cnum, cname in CONFERENCES:
                high = GetHighMessageNumber(cnum)
                state[cnum] = high
                print('Reset conf {} ({}) -- last-read set to {}'.format(cnum, cname, high))
            save_state(state)
            return

        total_found = 0

        for cnum, cname in CONFERENCES:
            high = GetHighMessageNumber(cnum)
            low  = GetLowMessageNumber(cnum)
            last_read = state.get(cnum, 0)
            start     = last_read + 1

            print()
            print('Conf {} {}  low={} high={}  last-read={} next={}'.format(
                cnum, cname, low, high, last_read, start))

            if start > high:
                print('  No new messages.')
                continue

            found    = 0
            new_last = last_read

            for num in range(start, high + 1):
                msgid = GetMsgIdFromNumber(cnum, num)
                if not msgid:
                    continue
                new_last = num

                msg = TMsgHeader()
                if not GetMessageById(cnum, msgid, ctypes.byref(msg)):
                    continue
                from_name = decode_wc(msg.From.Name)
                to_name   = decode_wc(msg.To.Name)
                subject   = decode_wc(msg.Subject)
                body      = get_body(msg)

                if show_all or is_binkp_related(from_name, subject, body):
                    found += 1
                    total_found += 1
                    print()
                    print('  ' + '=' * 58)
                    print('  Msg #{:6}  From: {}  To: {}'.format(
                        num, from_name, to_name))
                    print('  Subject : {}'.format(subject))
                    print('  ' + '-' * 58)
                    lines = body.splitlines()
                    for line in lines:
                        print('  ' + line)
                    #if len(lines) > 40:
                    #    print('  ... ({} more lines)'.format(len(lines) - 40))

            state[cnum] = new_last
            scanned = new_last - last_read
            if found:
                print()
                print('  {} relevant / {} scanned. Last-read -> {}.'.format(
                    found, scanned, new_last))
            else:
                print('  No BinkP-related messages in {} scanned. Last-read -> {}.'.format(
                    scanned, new_last))

        save_state(state)
        print()
        print('Done. {} relevant message(s) total.'.format(total_found))

    finally:
        WildcatServerDeleteContext()

if __name__ == '__main__':
    main()
