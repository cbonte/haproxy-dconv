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
from mako.exceptions import TopLevelLookupException

from parser import PContext
from parser import remove_indent
from parser import *

from urllib import quote

VERSION = ""
HAPROXY_GIT_VERSION = False

def main():
    global VERSION, HAPROXY_GIT_VERSION

    usage="Usage: %prog --infile <infile> --outfile <outfile>"

    optparser = OptionParser(description='Generate HTML Document from HAProxy configuation.txt',
                          version=VERSION,
                          usage=usage)
    optparser.add_option('--infile', '-i', help='Input file mostly the configuration.txt')
    optparser.add_option('--outfile','-o', help='Output file')
    optparser.add_option('--base','-b', default = '', help='Base directory for relative links')
    (option, args) = optparser.parse_args()

    if not (option.infile  and option.outfile) or len(args) > 0:
        optparser.print_help()
        exit(1)

    option.infile = os.path.abspath(option.infile)
    option.outfile = os.path.abspath(option.outfile)

    os.chdir(os.path.dirname(__file__))

    VERSION = get_git_version()
    if not VERSION:
        sys.exit(1)

    HAPROXY_GIT_VERSION = get_haproxy_git_version(os.path.dirname(option.infile))

    convert(option.infile, option.outfile, option.base)


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
    version = re.sub(r'-g.*', '', version)
    return version

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

    delimiters = [
        dict(start='&quot;', end='&quot;', multi=True ),
        dict(start='- '    , end='\n'    , multi=False),
    ]

    for keyword in keywords:
        keywordsCount[keyword] = 0
        for delimiter in delimiters:
            keywordsCount[keyword] += document.count(delimiter['start'] + keyword + delimiter['end'])
        if (keyword in keyword_conflicts) and (not keywordsCount[keyword]):
            # The keyword is never used, we can remove it from the conflicts list
            del keyword_conflicts[keyword]

        if keyword in keyword_conflicts:
            chapter_list = ""
            for chapter in keyword_conflicts[keyword]:
                chapter_list += '<li><a href="#%s">%s</a></li>' % (quote("%s (%s)" % (keyword, chapters[chapter]['title'])), chapters[chapter]['title'])
            for delimiter in delimiters:
                if delimiter['multi']:
                    document = document.replace(delimiter['start'] + keyword + delimiter['end'],
                            delimiter['start'] + '<span class="dropdown">' +
                            '<a class="dropdown-toggle" data-toggle="dropdown" href="#">' +
                            keyword +
                            '<span class="caret"></span>' +
                            '</a>' +
                            '<ul class="dropdown-menu">' +
                            '<li class="dropdown-header">This keyword is available in sections :</li>' +
                            chapter_list +
                            '</ul>' +
                            '</span>' + delimiter['end'])
                else:
                    document = document.replace(delimiter['start'] + keyword + delimiter['end'], delimiter['start'] + '<a href="#' + quote(keyword) + '">' + keyword + '</a>' + delimiter['end'])
        else:
            for delimiter in delimiters:
                document = document.replace(delimiter['start'] + keyword + delimiter['end'], delimiter['start'] + '<a href="#' + quote(keyword) + '">' + keyword + '</a>' + delimiter['end'])
        if keyword.startswith("option "):
            shortKeyword = keyword[len("option "):]
            keywordsCount[shortKeyword] = 0
            for delimiter in delimiters:
                keywordsCount[keyword] += document.count(delimiter['start'] + shortKeyword + delimiter['end'])
            if (shortKeyword in keyword_conflicts) and (not keywordsCount[shortKeyword]):
            # The keyword is never used, we can remove it from the conflicts list
                del keyword_conflicts[shortKeyword]
            for delimiter in delimiters:
                document = document.replace(delimiter['start'] + shortKeyword + delimiter['start'], delimiter['start'] + '<a href="#' + quote(keyword) + '">' + shortKeyword + '</a>' + delimiter['end'])

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
def convert(infile, outfile, base=''):
    global document, keywords, keywordsCount, chapters, keyword_conflicts

    if len(base) > 0 and base[:-1] != '/':
        base += '/'

    hasSummary = False

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
                'templates'
            ]
        )
    )

    parsers = init_parsers(pctxt)

    pctxt.context = {
            'headers':  {},
            'document': "",
            'base':     base,
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
        if (line == "Summary" or re.match("^[0-9].*", line)) and (len(next) > 0) and (next[0] == '-') \
                and ("-" * len(line)).startswith(next):  # Fuzzy underline length detection
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
                hasSummary = True
                # Learn chapters from the summary
                details = getTitleDetails(line)
                if details["chapter"]:
                    chapters[details["chapter"]] = details
        i += 1
    sections.append(currentSection)

    chapterIndexes = sorted(chapters.keys())

    document = ""

    # Complete the summary
    for section in sections:
        details = section["details"]
        title = details["title"]
        if title:
            fulltitle = title
            if details["chapter"]:
                #documentAppend("<a name=\"%s\"></a>" % details["chapter"])
                fulltitle = details["chapter"] + ". " + title
                if not details["chapter"] in chapters:
                    print >> sys.stderr, "Adding '%s' to the summary" % details["title"]
                    chapters[details["chapter"]] = details
                    chapterIndexes = sorted(chapters.keys())

    for section in sections:
        details = section["details"]
        pctxt.details = details
        level = details["level"]
        title = details["title"]
        content = section["content"].rstrip()

        print >> sys.stderr, "Parsing chapter %s..." % title

        if (title == "Summary") or (title and not hasSummary):
            summaryTemplate = pctxt.templates.get_template('summary.html')
            documentAppend(summaryTemplate.render(
                pctxt = pctxt,
                chapters = chapters,
                chapterIndexes = chapterIndexes,
            ))
            if title and not hasSummary:
                hasSummary = True
            else:
                continue

        if title:
            documentAppend('<a class="anchor" id="%s" name="%s"></a>' % (details["chapter"], details["chapter"]))
            if level == 1:
                documentAppend("<div class=\"page-header\">", False)
            documentAppend('<h%d id="chapter-%s" data-target="%s"><small><a class="small" href="#%s">%s.</a></small> %s</h%d>' % (level, details["chapter"], details["chapter"], details["chapter"], details["chapter"], cgi.escape(title, True), level))
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
                    'title':    '',
                    'subtitle': '',
                    'version':  '',
                    'author':   '',
                    'date':     ''
                }
                if re.match("^-+$", pctxt.get_line().strip()):
                    # Try to analyze the header of the file, assuming it follows
                    # those rules :
                    # - it begins with a "separator line" (several '-' chars)
                    # - then the document title
                    # - an optional subtitle
                    # - a new separator line
                    # - the version
                    # - the author
                    # - the date
                    pctxt.next()
                    pctxt.context['headers']['title'] = pctxt.get_line().strip()
                    pctxt.next()
                    subtitle = ""
                    while not re.match("^-+$", pctxt.get_line().strip()):
                        subtitle += " " + pctxt.get_line().strip()
                        pctxt.next()
                    pctxt.context['headers']['subtitle'] += subtitle.strip()
                    if not pctxt.context['headers']['subtitle']:
                        # No subtitle, try to guess one from the title if it
                        # starts with the word "HAProxy"
                        if pctxt.context['headers']['title'].startswith('HAProxy '):
                            pctxt.context['headers']['subtitle'] = pctxt.context['headers']['title'][8:]
                            pctxt.context['headers']['title'] = 'HAProxy'
                    pctxt.next()
                    pctxt.context['headers']['version'] = pctxt.get_line().strip()
                    pctxt.next()
                    pctxt.context['headers']['author'] = pctxt.get_line().strip()
                    pctxt.next()
                    pctxt.context['headers']['date'] = pctxt.get_line().strip()
                    pctxt.next()
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
                    while delay and delay[-1].strip() == "":
                        del delay[-1]
                    if delay:
                        remove_indent(delay)
                        documentAppend('<pre class="text">%s\n</pre>' % "\n".join(delay), False)
                    delay = []
                    documentAppend(line, False)
                else:
                    while delay and delay[-1].strip() == "":
                        del delay[-1]
                    if delay:
                        remove_indent(delay)
                        documentAppend('<pre class="text">%s\n</pre>' % "\n".join(delay), False)
                    delay = []
                    documentAppend(line, True)
                    pctxt.next()

            while delay and delay[-1].strip() == "":
                del delay[-1]
            if delay:
                remove_indent(delay)
                documentAppend('<pre class="text">%s\n</pre>' % "\n".join(delay), False)
            delay = []
            documentAppend('</div>')

    if not hasSummary:
        summaryTemplate = pctxt.templates.get_template('summary.html')
        print chapters
        document = summaryTemplate.render(
            pctxt = pctxt,
            chapters = chapters,
            chapterIndexes = chapterIndexes,
        ) + document


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

    template = pctxt.templates.get_template('template.html')
    try:
        footerTemplate = pctxt.templates.get_template('footer.html')
        footer = footerTemplate.render(
            pctxt = pctxt,
            headers = pctxt.context['headers'],
            document = document,
            chapters = chapters,
            chapterIndexes = chapterIndexes,
            keywords = keywords,
            keywordsCount = keywordsCount,
            keyword_conflicts = keyword_conflicts,
            version = VERSION,
            date = datetime.datetime.now().strftime("%Y/%m/%d"),
        )
    except TopLevelLookupException:
        footer = ""

    fd = open(outfile,'w')

    print >> fd, template.render(
            pctxt = pctxt,
            headers = pctxt.context['headers'],
            base = base,
            document = document,
            chapters = chapters,
            chapterIndexes = chapterIndexes,
            keywords = keywords,
            keywordsCount = keywordsCount,
            keyword_conflicts = keyword_conflicts,
            version = VERSION,
            date = datetime.datetime.now().strftime("%Y/%m/%d"),
            footer = footer
    )
    fd.close()

if __name__ == '__main__':
    main()
