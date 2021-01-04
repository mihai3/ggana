__module_name__ = "xchat-ggana" 
__module_version__ = "1.0" 
__module_description__ = "Automatically corrects declension errors in German - needs API server to run"

import xchat
import random
import re
import json
import urllib
import urllib2
import traceback
from collections import deque

def ggana_fetch_data(text):
    data = json.load(urllib2.urlopen("http://localhost:7314/?"+urllib.urlencode({
            "text": text,
            "mode": "irc"
        })))

    return data["result"] if data["changed"] else None

ggana_history = deque()

def output_fixed(text):
    try:
        result = ggana_fetch_data(text)
        if result:
            xchat.command("say \002\002%s" % result.encode("utf-8"))
            return True
        else:
            return False
    except:
        traceback.print_exc()
        return False

def xchat_ggana_cb(word, word_eol, userdata):
    global ggana_history
    nick, user, host = word[0][1:].replace('!', '@').split('@')
    text = word_eol[3][1:]

    # privmsg filter 
    if not re.match("[#&]", xchat.get_info("channel")[0]):
        return xchat.EAT_NONE
    
    if text.split(" ")[0] == "!fix":
        param = text[4:].strip()
        if param:
            # fix sentence
            success = output_fixed(param)
            if not success:
                xchat.command("say \002\002"+param+" "+u"\u2714".encode("utf-8"))
        else:
            # try stuff from history
            for line in reversed(ggana_history):
                success = output_fixed(line)
                if success: break
            else:
                xchat.command("say Nichts gefunden!")
        return xchat.EAT_PLUGIN

    elif not text.startswith("!"):
        ggana_history.append(text)
        if len(ggana_history) > 5:
            ggana_history.popleft()
    
    return xchat.EAT_NONE

xchat.hook_server("PRIVMSG", xchat_ggana_cb)