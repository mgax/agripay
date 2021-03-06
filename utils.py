import re, htmlentitydefs


def html_unescape(text):
    # http://effbot.org/zone/re-sub.htm#unescape-html
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)


import os
import logging

LOG_FORMAT = "[%(asctime)s] %(name)s %(levelname)s %(message)s"


def set_up_logging():
    stderr = logging.StreamHandler()
    stderr.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(stderr)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
