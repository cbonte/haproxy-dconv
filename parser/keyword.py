import re
import parser
from urllib.parse import quote

class KeyWordParser(parser.Parser):
    def __init__(self, pctxt):
        parser.Parser.__init__(self, pctxt)
        self.keywordPattern = re.compile(r'^(%s%s)(%s)' % (
            '([a-z0-9\-\+_\.]*[a-z0-9\-\+_)])', # keyword
            '( [a-z0-9\-_]+)*',                  # subkeywords
            '(\([^ ]*\))?',   # arg (ex: (<backend>), (<frontend>/<backend>), (<offset1>,<length>[,<offset2>]) ...
        ))

    def parse(self, line):
        pctxt = self.pctxt
        keywords = pctxt.keywords
        keywordsCount = pctxt.keywordsCount
        chapters = pctxt.chapters

        res = ""

        if line != "" and not re.match(r'^ ', line):
            parsed = self.keywordPattern.match(line)
            if parsed != None:
                keyword = parsed.group(1)
                arg     = parsed.group(4)
                parameters = line[len(keyword) + len(arg):]
                if (parameters != "" and not re.match("^ +(/?(&lt;|\[|\{).*|(: [a-z0-9 +]+))?(\(deprecated\))?$", parameters)):
                    # Dirty hack
                    # - parameters should only start with the character "<", "[", "{", and in rare cases with an extra "/"
                    # - or a column (":") followed by a alpha keywords to identify fetching samples (optionally separated by the character "+")
                    # - or the string "(deprecated)" at the end
                    keyword = False
                else:
                    splitKeyword = keyword.split(" ")

                parameters = arg + parameters
            else:
                keyword = False

            if keyword and (len(splitKeyword) <= 4):
                toplevel = pctxt.details["toplevel"]
                for j in range(0, len(splitKeyword)):
                    subKeyword = " ".join(splitKeyword[0:j + 1])
                    if subKeyword != "no":
                        if not subKeyword in keywords:
                            keywords[subKeyword] = set()
                        keywords[subKeyword].add(pctxt.details["chapter"])
                    res += '<a class="anchor" name="%s"></a>' % subKeyword
                    res += '<a class="anchor" name="%s-%s"></a>' % (toplevel, subKeyword)
                    res += '<a class="anchor" name="%s-%s"></a>' % (pctxt.details["chapter"], subKeyword)
                    res += '<a class="anchor" name="%s (%s)"></a>' % (subKeyword, chapters[toplevel]['title'])
                    res += '<a class="anchor" name="%s (%s)"></a>' % (subKeyword, chapters[pctxt.details["chapter"]]['title'])

                deprecated = parameters.find("(deprecated)")
                if deprecated != -1:
                    prefix = ""
                    suffix = ""
                    parameters = parameters.replace(
                        "(deprecated)",
                        '<span class="label label-warning">(deprecated)</span>'
                    )
                else:
                    prefix = ""
                    suffix = ""

                nextline = pctxt.get_line(1)

                while nextline.startswith("   "):
                    # Found parameters on the next line
                    parameters += "\n" + nextline
                    pctxt.next()
                    if pctxt.has_more_lines(1):
                        nextline = pctxt.get_line(1)
                    else:
                        nextline = ""


                parameters = self.colorize(parameters)
                res += '<div class="keyword">%s<b><a class="anchor" name="%s"></a><a href="#%s">%s</a></b>%s%s</div>' % (prefix, keyword, quote("%s-%s" % (pctxt.details["chapter"], keyword)), keyword, parameters, suffix)
                pctxt.next()
                pctxt.stop = True
            elif line.startswith("/*"):
                # Skip comments in the documentation
                while not pctxt.get_line().endswith("*/"):
                    pctxt.next()
                pctxt.next()
            else:
                # This is probably not a keyword but a text, ignore it
                res += line
        else:
            res += line

        return res

    # Used to colorize keywords parameters
    # TODO : use CSS styling
    def colorize(self, text):
        colorized = ""
        tags = [
                [ "["   , "]"   , "#008" ],
                [ "{"   , "}"   , "#800" ],
                [ "&lt;", "&gt;", "#080" ],
        ]
        heap = []
        pos = 0
        while pos < len(text):
            substring = text[pos:]
            found = False
            for tag in tags:
                if substring.startswith(tag[0]):
                    # Opening tag
                    heap.append(tag)
                    colorized += '<span style="color: %s">%s' % (tag[2], substring[0:len(tag[0])])
                    pos += len(tag[0])
                    found = True
                    break
                elif substring.startswith(tag[1]):
                    # Closing tag

                    # pop opening tags until the corresponding one is found
                    openingTag = False
                    while heap and openingTag != tag:
                        openingTag = heap.pop()
                        if openingTag != tag:
                            colorized += '</span>'
                    # all intermediate tags are now closed, we can display the tag
                    colorized += substring[0:len(tag[1])]
                    # and the close it if it was previously opened
                    if openingTag == tag:
                        colorized += '</span>'
                    pos += len(tag[1])
                    found = True
                    break
            if not found:
                colorized += substring[0]
                pos += 1
        # close all unterminated tags
        while heap:
            tag = heap.pop()
            colorized += '</span>'

        return colorized


