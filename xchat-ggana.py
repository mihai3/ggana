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

def ggana_fetch_data(text):
    data = json.load(urllib2.urlopen("http://localhost:7314/?"+urllib.urlencode({
            "text": text,
            "mode": "irc"
        })))

    return data["result"] if data["changed"] else None

def xchat_ggana_cb(word, word_eol, userdata):
    nick, user, host = word[0][1:].replace('!', '@').split('@')
    text = word_eol[3][1:]

    # privmsg filter 
    if not re.match("[#&]", xchat.get_info("channel")[0]) or text.startswith("!"):
        return xchat.EAT_NONE

    try:
        result = ggana_fetch_data(text)
        if result:
            xchat.command("say \002\002%s" % result.encode("utf-8"))
            return xchat.EAT_PLUGIN
    except:
        traceback.print_exc()
        pass

    

xchat.hook_server("PRIVMSG", xchat_ggana_cb)