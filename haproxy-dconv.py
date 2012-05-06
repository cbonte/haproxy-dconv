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
from mako.lookup import TemplateLookup

from parser import PContext
from parser import get_indent
from parser import remove_indent
from parser import *

VERSION = ""
DATE = ""
HAPROXY_GIT_VERSION = False

def main():
    global VERSION, DATE, HAPROXY_GIT_VERSION

    VERSION = get_git_version()
    DATE = get_git_date()
    if not VERSION or not DATE:
        sys.exit(1)

    usage="Usage: %prog --infile <infile> --outfile <outfile>"

    optparser = OptionParser(description='Generate HTML Document from HAProxy configuation.txt',
                          version=VERSION,
                          usage=usage)
    optparser.add_option('--infile', '-i', help='Input file mostly the configuration.txt')
    optparser.add_option('--outfile','-o', help='Output file')
    (option, args) = optparser.parse_args()

    if not (option.infile  and option.outfile) or len(args) > 0:
        optparser.print_help()
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

def init_parsers(pctxt):
    return [
        underline.Parser(pctxt),
        arguments.Parser(pctxt),
        seealso.Parser(pctxt),
        example.Parser(pctxt),
        table.Parser(pctxt),
        underline.Parser(pctxt),
        keyword.Parser(pctxt),
    ]


# The parser itself
def convert(infile, outfile):
    global document, keywords, keywordsCount, chapters, keyword_conflicts

    data = []
    fd = file(infile,"r")
    for line in fd:
        line.replace("\t", " " * 8)
        line = line.rstrip()
        data.append(line)
    fd.close()

    pctxt = PContext(
        TemplateLookup(
            directories=[
                os.path.join(os.path.dirname(__file__), 'templates')
            ]
        )
    )

    parsers = init_parsers(pctxt)

    pctxt.context = {
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

    pctxt.keywords = keywords
    pctxt.keywordsCount = keywordsCount
    pctxt.chapters = chapters

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
        pctxt.details = details
        level = details["level"]
        title = details["title"]
        content = section["content"].rstrip()

        print >> sys.stderr, "Parsing chapter %s..." % title

        if title == "Summary":
            continue

        if title:
            fulltitle = title
            if pctxt.details["chapter"]:
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

            pctxt.set_content(content)

            if not title:
                lines = pctxt.get_lines()
                pctxt.context['headers'] = {
                        'title':        lines[1].strip(),
                        'subtitle':     lines[2].strip(),
                        'version':      lines[4].strip(),
                        'author':       lines[5].strip(),
                        'date':         lines[6].strip()
                }
                if HAPROXY_GIT_VERSION:
                    pctxt.context['headers']['version'] = 'version ' + HAPROXY_GIT_VERSION

                # Skip header lines
                pctxt.eat_lines()
                pctxt.eat_empty_lines()

            documentAppend('<div>', False)

            delay = []
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

                oldline = line
                pctxt.stop = False
                for parser in parsers:
                    line = parser.parse(line)
                    if pctxt.stop:
                        break
                if oldline == line:
                    # nothing has changed,
                    # delays the rendering
                    if delay or line != "":
                        delay.append(line)
                    pctxt.next()
                elif pctxt.stop:
                    documentAppend("\n".join(render_delayed(delay)), False)
                    documentAppend(line, False)
                else:
                    documentAppend("\n".join(render_delayed(delay)), False)
                    documentAppend(line, True)
                    pctxt.next()

            documentAppend("\n".join(render_delayed(delay)), False)
            documentAppend('</div>')

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
            toplevel = section.split(".")[0]
            title = chapters[toplevel]['title']
            if title != chapters[section]['title']:
                title += " - " + chapters[section]['title']
            keywords.insert(offset, "%s (%s)" % (keyword, title))
            offset += 1
        keywords.remove(keyword)

    print >> sys.stderr, "Exporting to %s..." % outfile

    template = pctxt.templates.get_template('template.html')

    fd = open(outfile,'w')

    print >> fd, template.render(
            headers = pctxt.context['headers'],
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


def render_delayed(delay, list=False):
    while delay and not delay[-1].strip():
        del delay[-1]

    rendered = []
    if delay:
        paragraph = []
        indent = -1
        previous_line = None
        for i, line in enumerate(delay):
            line_indent = get_indent(line)
            if not line:
                remove_indent(paragraph)
                if paragraph:
                    format = False
                    for s in paragraph:
                        if s.find("  ") != -1:
                            format = True
                            break
                    if format:
                        open = '<pre><code>'
                        close = '</code></pre>'
                    else:
                        open = '<div class="text separator">\n'
                        close = '\n</div>'

                    rendered.append('%s%s%s' % (open, "\n".join(paragraph), close))
                    del paragraph[:]
                    indent = -1
                    previous_line = None
                if line:
                    paragraph.append(line)
            elif list == line.strip()[0]:
                type = line.strip()[0]
                j = i
                while j < len(delay) and (not delay[j] or get_indent(delay[j]) >= line_indent or (get_indent(delay[j]) == line_indent and delay[j][line_indent] == type)):
                    j += 1
                subdelay = delay[i:j]
                del delay[i:j]
                #remove_indent(subdelay, 1)
                paragraph.append("<li>")
                paragraph += render_delayed(subdelay, True)
                paragraph.append("</li>")
            elif not list and line.strip()[0] in ['-', '*']:
                type = line.strip()[0]
                j = i
                while j < len(delay) and (not delay[j] or get_indent(delay[j]) >= line_indent or (get_indent(delay[j]) == line_indent and delay[j][line_indent] in line.strip()[0] in ['-', '*'])):
                    j += 1
                subdelay = delay[i:j]
                del delay[i:j]
                #print subdelay
                #sys.exit(1)
                #remove_indent(subdelay, 1)
                paragraph.append("<ul>")
                paragraph += render_delayed(subdelay, type)
                paragraph.append("</ul>")
                '''
                paragraph.append("<ul>")
                for listitem in subdelay:
                    paragraph.append("<li>%s</li>" % listitem)
                paragraph.append("</ul>")
                '''
                indent = line_indent
                previous_line = line
            elif (indent >= 0 and line_indent > indent):
                if previous_line and previous_line[indent] != ' ' and previous_line[indent - 1] == ' ':
                    paragraph.append(line)
                else:
                    j = i
                    while j < len(delay) and (not delay[j] or get_indent(delay[j]) > indent):
                        j += 1
                    subdelay = delay[i:j]
                    del delay[i:j]
                    paragraph += render_delayed(subdelay)
                indent = line_indent
                previous_line = line
            else:
                paragraph.append(line)
                indent = line_indent
                previous_line = line

        if paragraph:
            remove_indent(paragraph)
            format = False
            for s in paragraph:
                if s.find("  ") != -1:
                    format = True
                    break
            if format:
                open = '<pre><code>'
                close = '</code></pre>'
            else:
                open = '<div class="text separator">\n'
                close = '\n</div>'

            rendered.append('%s%s%s' % (open, "\n".join(paragraph), close))

    del delay[:]

    return rendered

if __name__ == '__main__':
    main()
