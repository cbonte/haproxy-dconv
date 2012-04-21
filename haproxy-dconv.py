#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2012 Cyril Bonté
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
TODO : ability to split chapters into several files
TODO : manage keyword locality (server/proxy/global ; ex : maxconn)
TODO : Remove global variables where possible
'''
import os
import subprocess
import sys
import cgi
import re
import time
import datetime

from optparse import OptionParser
from mako.template import Template

VERSION = ""
DATE = ""
HAPROXY_GIT_VERSION = False

class PContext:
    def __init__(self, content):
        self.lines = content.split("\n")
        self.nblines = len(self.lines)
        self.i = 0
        self.stop = False

    def get_lines(self):
        return self.lines

    def eat_lines(self):
        count = 0
        while self.lines[self.i].strip():
            count += 1
            self.next()
        return count

    def eat_empty_lines(self):
        count = 0
        while not self.lines[self.i].strip():
            count += 1
            self.next()
        return count

    def next(self, count=1):
        self.i += count

    def has_more_lines(self, offset=0):
        return self.i + offset < self.nblines

    def get_line(self, offset=0):
        return self.lines[self.i + offset].rstrip()

class ArgumentParser:
    def parse(self, pctxt, line):
        line = re.sub(r'(Arguments :)', r'<span class="label label-info">\1</span>', line)
        return line

class SeeAlsoParser:
    def parse(self, pctxt, line):
        line = re.sub(r'(See also *:)', r'<span class="label label-see-also">\1</span>', line)
        return line

class NextLineParser:
    def parse(self, pctxt, line):
        pctxt.next()
        return line

class ExampleParser:
    def parse(self, pctxt, line):
        res = ""
        if re.search(r'Examples? *:', line):
            # Detect examples blocks
            desc_indent = False
            desc = re.sub(r'.*Examples? *:', '', line).strip()

            # Some examples have a description
            if desc:
                desc_indent = len(line) - len(desc)

            line = re.sub(r'(Examples? *:)', r'<span class="label label-success">\1</span>', line)
            indent = get_indent(line)

            if desc:
                res += line[:len(line) - len(desc)]
                # And some description are on multiple lines
                while pctxt.get_line(1) and get_indent(pctxt.get_line(1)) == desc_indent:
                    desc += " " + pctxt.get_line(1).strip()
                    pctxt.next()
            else:
                res += line

            pctxt.next()
            add_empty_line = pctxt.eat_empty_lines()

            if get_indent(pctxt.get_line()) > indent:
                res += '<pre class="prettyprint">'
                if desc:
                    desc = desc[0].upper() + desc[1:]
                    res += '<div class="example-desc">%s</div>' % desc
                add_empty_line = 0
                while pctxt.has_more_lines() and ((not pctxt.get_line()) or (get_indent(pctxt.get_line()) > indent)):
                    if pctxt.get_line():
                        for j in xrange(0, add_empty_line):
                            res += "\n"
                        line = re.sub(r'(#.*)$', r'<span class="comment">\1</span>', pctxt.get_line())
                        res += line + '\n'
                        add_empty_line = 0
                    else:
                        add_empty_line += 1
                    pctxt.next()
                res += "</pre>"
            elif get_indent(pctxt.get_line()) == indent:
                # Simple example that can't have empty lines
                res += '<pre class="prettyprint">'
                if add_empty_line:
                        # This means that the example was on the same line as the 'Example' tag
                    res += " " * indent + desc
                else:
                    while pctxt.has_more_lines() and (get_indent(pctxt.get_line()) == indent):
                        res += pctxt.get_line()
                        pctxt.next()
                    pctxt.eat_empty_lines() # Skip empty remaining lines
                res += "</pre>"
            pctxt.stop = True
        else:
            res = line
        return res

class UnderlineParser:
    def parse(self, pctxt, line):
        if pctxt.has_more_lines(1):
            nextline = pctxt.get_line(1)
            if (len(line) > 0) and (len(nextline) > 0) and (nextline[0] == '-') and ("-" * len(line) == nextline):
                # Detect underlines
                line = '<h5>%s</h5>' % line
                pctxt.next(2)
                pctxt.eat_empty_lines()
                pctxt.stop = True

        return line

class TableParser:
    def __init__(self):
        self.tablePattern = re.compile(r'^ *(-+\+)+-+')

    def parse(self, pctxt, line):
        global document, keywords, keywordsCount, chapters, keyword_conflicts
        global details, context

        res = ""

        if pctxt.has_more_lines(1):
            nextline = pctxt.get_line(1)
        else:
            nextline = ""

        if context['headers']['subtitle'] == 'Configuration Manual' and self.tablePattern.match(nextline):
            # activate table rendering only for the Configuration Manual
            lineSeparator = nextline
            nbColumns = nextline.count("+") + 1
            extraColumns = 0
            print >> sys.stderr, "Entering table mode (%d columns)" % nbColumns
            table = []
            if line.find("|") != -1:
                row = []
                while pctxt.has_more_lines():
                    line = pctxt.get_line()
                    if pctxt.has_more_lines(1):
                        nextline = pctxt.get_line(1)
                    else:
                        nextline = ""
                    if line == lineSeparator:
                        # New row
                        table.append(row)
                        row = []
                        if nextline.find("|") == -1:
                            break # End of table
                    else:
                        # Data
                        columns = line.split("|")
                        for j in xrange(0, len(columns)):
                            try:
                                if row[j]:
                                    row[j] += "<br />"
                                row[j] += columns[j].strip()
                            except:
                                row.append(columns[j].strip())
                    pctxt.next()
            else:
                row = []
                headers = nextline
                while pctxt.has_more_lines():
                    line = pctxt.get_line()
                    if pctxt.has_more_lines(1):
                        nextline = pctxt.get_line(1)
                    else:
                        nextline = ""

                    if nextline == "":
                        if row: table.append(row)
                        break # End of table

                    if (line != lineSeparator) and (line[0] != "-"):
                        start = 0

                        if row and not line.startswith(" "):
                            # Row is complete, parse a new one
                            table.append(row)
                            row = []

                        tmprow = []
                        while start != -1:
                            end = headers.find("+", start)
                            if end == -1:
                                end = len(headers)

                            realend = end
                            if realend == len(headers):
                                realend = len(line)
                            else:
                                while realend < len(line) and line[realend] != " ":
                                    realend += 1
                                    end += 1

                            tmprow.append(line[start:realend])

                            start = end + 1
                            if start >= len(headers):
                                start = -1
                        for j in xrange(0, nbColumns):
                            try:
                                row[j] += tmprow[j].strip()
                            except:
                                row.append(tmprow[j].strip())

                        deprecated = row[0].endswith("(deprecated)")
                        if deprecated:
                            row[0] = row[0][: -len("(deprecated)")].rstrip()

                        nooption = row[1].startswith("(*)")
                        if nooption:
                            row[1] = row[1][len("(*)"):].strip()

                        if deprecated or nooption:
                            extraColumns = 1
                            extra = ""
                            if deprecated:
                                extra += '<span class="label label-warning">(deprecated)</span>'
                            if nooption:
                                extra += '<span>(*)</span>'
                            row.append(extra)

                    pctxt.next()
            print >> sys.stderr, "Leaving table mode"
            res = renderTable(table, nbColumns, details["toplevel"])
            pctxt.next() # skip useless next line
            pctxt.stop = True
        elif line.find("May be used in sections") != -1:
            nextline = pctxt.get_line(1)
            rows = []
            headers = line.split(":")
            rows.append(headers[1].split("|"))
            rows.append(nextline.split("|"))
            table = {
                    "rows": rows,
                    "title": headers[0]
            }
            print rows
            res = renderTable(table)
            pctxt.next(2)  # skip this previous table
            pctxt.stop = True
        else:
            res = line

        return res

class KeywordParser:
    def __init__(self):
        self.keywordPattern = re.compile(r'^(%s%s)(%s)' % (
            '([a-z][a-z0-9\-_\.]*[a-z0-9\-_)])', # keyword
            '( [a-z0-9\-_]+)*',                  # subkeywords
            '(\((&lt;[a-z0-9]+&gt;/?)+\))?'      # arg (ex: (<backend>), (<frontend>/<backend>), ...
        ))

    def parse(self, pctxt, line):
        global document, keywords, keywordsCount, chapters, keyword_conflicts
        global details

        res = ""

        if line != "" and not re.match(r'^ ', line):
            parsed = self.keywordPattern.match(line)
            if parsed != None:

                keyword = parsed.group(1)
                arg     = parsed.group(4)
                parameters = line[len(keyword) + len(arg):]
                if parameters != "" and not re.match("^ +(&lt;|\[|\{|/|\(deprecated\))", parameters):
                    keyword = False
                else:
                    splitKeyword = keyword.split(" ")
                parameters = arg + parameters
            else:
                keyword = False

            if keyword and (len(splitKeyword) <= 5):
                toplevel = details["toplevel"]
                for j in xrange(0, len(splitKeyword)):
                    subKeyword = " ".join(splitKeyword[0:j + 1])
                    if subKeyword != "no":
                        if not subKeyword in keywords:
                            keywords[subKeyword] = set()
                        keywords[subKeyword].add(toplevel)
                    res += '<a name="%s"></a>' % subKeyword
                    res += '<a name="%s-%s"></a>' % (toplevel, subKeyword)
                    res += '<a name="%s-%s"></a>' % (details["chapter"], subKeyword)
                    res += '<a name="%s (%s)"></a>' % (subKeyword, chapters[toplevel]['title'])
                    res += '<a name="%s (%s)"></a>' % (subKeyword, chapters[details["chapter"]]['title'])

                deprecated = parameters.find("(deprecated)")
                if deprecated != -1:
                    prefix = ""
                    suffix = ""
                    parameters = parameters.replace("(deprecated)", '<span class="label label-warning">(deprecated)</span>')
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


                parameters = colorize(parameters)

                res += '<div class="keyword">%s<b><a name="%s"></a><a href="#%s-%s">%s</a></b>%s%s</div>' % (prefix, keyword, toplevel, keyword, keyword, parameters, suffix)
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


def main():
    global VERSION, DATE, HAPROXY_GIT_VERSION

    VERSION = get_git_version()
    DATE = get_git_date()
    if not VERSION or not DATE:
        sys.exit(1)

    usage="Usage: %prog --infile <infile> --outfile <outfile>"

    parser = OptionParser(description='Generate HTML Document from HAProxy configuation.txt',
                          version=VERSION,
                          usage=usage)
    parser.add_option('--infile', '-i', help='Input file mostly the configuration.txt')
    parser.add_option('--outfile','-o', help='Output file')
    (option, args) = parser.parse_args()

    if not (option.infile  and option.outfile) or len(args) > 0:
        parser.print_help()
        exit(1)

    HAPROXY_GIT_VERSION = get_haproxy_git_version(os.path.dirname(option.infile))

    convert(option.infile, option.outfile)


# Temporarily determine the version from git to follow which commit generated
# the documentation
def get_git_version():
    if not os.path.isdir(".git"):
        print >> sys.stderr, "This does not appear to be a Git repository."
        return
    try:
        p = subprocess.Popen(["git", "describe", "--tags", "--match", "v*"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except EnvironmentError:
        print >> sys.stderr, "Unable to run git"
        return
    version = p.communicate()[0]
    if p.returncode != 0:
        print >> sys.stderr, "Unable to run git"
        return

    if len(version) < 2:
        return

    version = version[1:].strip()
    return version

# Temporarily determine the last commit date from git
def get_git_date():
    if not os.path.isdir(".git"):
        print >> sys.stderr, "This does not appear to be a Git repository."
        return
    try:
        p = subprocess.Popen(["git", "log", "-1", '--format=%ct'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except EnvironmentError:
        print >> sys.stderr, "Unable to run git"
        return
    date = p.communicate()[0]
    if p.returncode != 0:
        print >> sys.stderr, "Unable to run git"
        return

    return date

def get_haproxy_git_version(path):
    try:
        p = subprocess.Popen(["git", "describe", "--tags", "--match", "v*"], cwd=path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except EnvironmentError:
        return False
    version = p.communicate()[0]

    if p.returncode != 0:
        return False

    if len(version) < 2:
        return False

    version = version[1:].strip()
    version = re.sub(r'-g.*', '', version)
    return version

def getTitleDetails(string):
    array = string.split(".")

    title    = array.pop().strip()
    chapter  = ".".join(array)
    level    = max(1, len(array))
    if array:
        toplevel = array[0]
    else:
        toplevel = False

    return {
            "title"   : title,
            "chapter" : chapter,
            "level"   : level,
            "toplevel": toplevel
    }

# Parse the whole document to insert links on keywords
def createLinks():
    global document, keywords, keywordsCount, keyword_conflicts, chapters

    print >> sys.stderr, "Generating keywords links..."

    for keyword in keywords:
        keywordsCount[keyword] = document.count('&quot;' + keyword + '&quot;')
        if (keyword in keyword_conflicts) and (not keywordsCount[keyword]):
            # The keyword is never used, we can remove it from the conflicts list
            del keyword_conflicts[keyword]

        if keyword in keyword_conflicts:
            chapter_list = ""
            for chapter in keyword_conflicts[keyword]:
                chapter_list += '<li><a href="#%s (%s)">%s</a></li>' % (keyword, chapters[chapter]['title'], chapters[chapter]['title'])
            document = document.replace('&quot;' + keyword + '&quot;',
                    '&quot;<span class="dropdown">' +
                    '<a class="dropdown-toggle" data-toggle="dropdown" href="#">' +
                    keyword +
                    '<span class="caret"></span>' +
                    '</a>' +
                    '<ul class="dropdown-menu">' +
                    '<div>This keyword is available in sections :</div>' +
                    chapter_list +
                    '</ul>' +
                    '</span>&quot;')
        else:
            document = document.replace('&quot;' + keyword + '&quot;', '&quot;<a href="#' + keyword + '">' + keyword + '</a>&quot;')
        if keyword.startswith("option "):
            shortKeyword = keyword[len("option "):]
            keywordsCount[shortKeyword] = document.count('&quot;' + shortKeyword + '&quot;')
            if (shortKeyword in keyword_conflicts) and (not keywordsCount[shortKeyword]):
            # The keyword is never used, we can remove it from the conflicts list
                del keyword_conflicts[shortKeyword]
            document = document.replace('&quot;' + shortKeyword + '&quot;', '&quot;<a href="#' + keyword + '">' + shortKeyword + '</a>&quot;')

def documentAppend(text, retline = True):
    global document
    document += text
    if retline:
        document += "\n"

# Render tables detected by the conversion parser
def renderTable(table, maxColumns = 0, hasKeywords = False):
    res = ""

    title = None
    if isinstance(table, dict):
        title = table["title"]
        table = table["rows"]

    if not maxColumns:
        maxColumns = len(table[0])

    if title:
        res += '<p>%s :' % title

    res += '<table class=\"table table-bordered\" border="0" cellspacing="0" cellpadding="0">'
    mode = "th"
    headerLine = ""
    i = 0
    for row in table:
        line = ""

        if i == 0:
            line += '<thead>'
        elif i > 1 and (i  - 1) % 20 == 0:
            # Repeat headers periodically for long tables
            line += headerLine

        line += '<tr>'

        j = 0
        for column in row:
            if j >= maxColumns:
                break
            data = column.strip()
            if data in ['yes']:
                open = '<%s class="alert-success"><div class="pagination-centered">' % mode
                close = '</div></%s>' % mode
            elif data in ['no']:
                open = '<%s class="alert-error"><div class="pagination-centered">' % mode
                close = '</div></%s>' % mode
            elif data in ['X', '-']:
                open = '<%s><div class="pagination-centered">' % mode
                close = '</div></%s>' % mode
            else:
                open = '<%s>' % mode
                close = '</%s>' % mode
            keyword = column
            if j == 0 and i != 0 and hasKeywords:
                if keyword.startswith("[no] "):
                    keyword = keyword[len("[no] "):]
                open += '<a href="#%s-%s">' % (hasKeywords, keyword)
                close = '</a>' + close
            if j == 0 and len(row) > maxColumns:
                for k in xrange(maxColumns, len(row)):
                    open = open + '<span class="pull-right">' + row[k] + '</span>'
            line += '%s%s%s' % (open, data, close)
            j += 1
        mode = "td"
        line += '</tr>'

        if i == 0:
            line += '</thead>'
            headerLine = line

        res += line

        i += 1
    res += '</table>'

    if title:
        res += '</p>'

    return res

# Used to colorize keywords parameters
# TODO : use CSS styling
def colorize(text):
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

def get_indent(line):
    i = 0
    length = len(line)
    while i < length and line[i] == ' ':
        i += 1
    return i

# The parser itself
# TODO : simplify the parser ! Make it clearer and modular.
def convert(infile, outfile):
    global document, keywords, keywordsCount, chapters, keyword_conflicts
    global details, context

    data = []
    fd = file(infile,"r")
    for line in fd:
        line.replace("\t", " " * 8)
        line = line.rstrip()
        data.append(line)
    fd.close()

    context = {
            'headers':      {},
            'document':     ""
    }

    sections = []
    currentSection = {
            "details": getTitleDetails(""),
            "content": "",
    }

    chapters = {}

    keywords = {}
    keywordsCount = {}

    specialSections = {
            "default": {
                    "hasKeywords": True,
            },
            "4.1": {
                    "hasKeywords": True,
            },
    }

    print >> sys.stderr, "Importing %s..." % infile

    nblines = len(data)
    i = j = 0
    while i < nblines:
        line = data[i].rstrip()
        if i < nblines - 1:
            next = data[i + 1].rstrip()
        else:
            next = ""
        if (line == "Summary" or re.match("^[0-9].*", line)) and (len(next) > 0) and (next[0] == '-') and ("-" * len(line) == next):
            sections.append(currentSection)
            currentSection = {
                "details": getTitleDetails(line),
                "content": "",
            }
            j = 0
            i += 1 # Skip underline
            while not data[i + 1].rstrip():
                i += 1 # Skip empty lines

        else:
            if len(line) > 80:
                print >> sys.stderr, "Line `%i' exceeds 80 columns" % (i + 1)

            currentSection["content"] = currentSection["content"] + line + "\n"
            j += 1
            if currentSection["details"]["title"] == "Summary" and line != "":
                # Learn chapters from the summary
                details = getTitleDetails(line)
                if details["chapter"]:
                    chapters[details["chapter"]] = details
        i += 1
    sections.append(currentSection)

    chapterIndexes = sorted(chapters.keys())

    document = ""
    for section in sections:
        details = section["details"]
        level = details["level"]
        title = details["title"]
        content = section["content"].rstrip()

        print >> sys.stderr, "Parsing chapter %s..." % title

        if title == "Summary":
            continue

        if title:
            fulltitle = title
            if details["chapter"]:
                documentAppend("<a name=\"%s\"></a>" % details["chapter"])
                fulltitle = details["chapter"] + ". " + title
                if not details["chapter"] in chapters:
                    print >> sys.stderr, "Adding '%s' to the summary" % details["title"]
                    chapters[details["chapter"]] = details
                    chapterIndexes = sorted(chapters.keys())
            if level == 1:
                documentAppend("<div class=\"page-header\">", False)
            documentAppend("<h%d><small>%s.</small> %s</h%d>" % (level, details["chapter"], cgi.escape(title, True), level))
            if level == 1:
                documentAppend("</div>", False)

        if content:
            if False and title:
                # Display a navigation bar
                documentAppend('<ul class="well pager">')
                documentAppend('<li><a href="#top">Top</a></li>', False)
                index = chapterIndexes.index(details["chapter"])
                if index > 0:
                    documentAppend('<li class="previous"><a href="#%s">Previous</a></li>' % chapterIndexes[index - 1], False)
                if index < len(chapterIndexes) - 1:
                    documentAppend('<li class="next"><a href="#%s">Next</a></li>' % chapterIndexes[index + 1], False)
                documentAppend('</ul>', False)
            content = cgi.escape(content, True)
            content = re.sub(r'section ([0-9]+(.[0-9]+)*)', r'<a href="#\1">section \1</a>', content)

            pctxt = PContext(content)

            if not title:
                lines = pctxt.get_lines()
                context['headers'] = {
                        'title':        lines[1].strip(),
                        'subtitle':     lines[2].strip(),
                        'version':      lines[4].strip(),
                        'author':       lines[5].strip(),
                        'date':         lines[6].strip()
                }
                if HAPROXY_GIT_VERSION:
                    context['headers']['version'] = 'version ' + HAPROXY_GIT_VERSION

                # Skip header lines
                pctxt.eat_lines()
                pctxt.eat_empty_lines()

            documentAppend('<pre>', False)

            parsers = [
                ArgumentParser(),
                SeeAlsoParser(),
                ExampleParser(),
                TableParser(),
                UnderlineParser(),
                KeywordParser(),
                NextLineParser(),
            ]

            while pctxt.has_more_lines():
                try:
                    specialSection = specialSections[details["chapter"]]
                except:
                    specialSection = specialSections["default"]

                line = pctxt.get_line()
                if i < nblines - 1:
                    nextline = pctxt.get_line(1)
                else:
                    nextline = ""

                pctxt.stop = False
                for parser in parsers:
                    line = parser.parse(pctxt, line)
                    if pctxt.stop:
                        break
                documentAppend(line, not pctxt.stop)
            documentAppend('</pre><br />')
    # Log warnings for keywords defined in several chapters
    keyword_conflicts = {}
    for keyword in keywords:
        keyword_chapters = list(keywords[keyword])
        keyword_chapters.sort()
        if len(keyword_chapters) > 1:
            print >> sys.stderr, 'Multi section keyword : "%s" in chapters %s' % (keyword, list(keyword_chapters))
            keyword_conflicts[keyword] = keyword_chapters

    keywords = list(keywords)
    keywords.sort()

    createLinks()

    # Add the keywords conflicts to the keywords list to make them available in the search form
    # And remove the original keyword which is now useless
    for keyword in keyword_conflicts:
        sections = keyword_conflicts[keyword]
        offset = keywords.index(keyword)
        for section in sections:
            keywords.insert(offset, "%s (%s)" % (keyword, chapters[section]['title']))
            offset += 1
        keywords.remove(keyword)

    print >> sys.stderr, "Exporting to %s..." % outfile

    template = Template(filename=os.path.join(os.path.dirname(__file__), 'templates', 'template.html'))

    fd = open(outfile,'w')

    print >> fd, template.render(
            headers = context['headers'],
            document = document,
            chapters = chapters,
            chapterIndexes = chapterIndexes,
            keywords = keywords,
            keywordsCount = keywordsCount,
            keyword_conflicts = keyword_conflicts,
            version = VERSION,
            date = datetime.datetime.fromtimestamp(int(DATE)).strftime("%Y/%m/%d")
    )
    fd.close()

if __name__ == '__main__':
    main()
