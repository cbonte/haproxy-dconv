"""
This module is made of the various high-level method used to effectively
convert the Haproxy documentation into a suitable form
"""


import os
import re
import sys
import html
import datetime
import time
import io



from urllib.parse import quote

from mako.lookup import TemplateLookup
from mako.exceptions import TopLevelLookupException

import parser
import parser.arguments
import parser.underline
import parser.keyword
import parser.example
import parser.table
import parser.seealso


# Pre-compiled regex patterns for performance
_PATTERN_SECTION = re.compile(r'section ([0-9]+(.[0-9]+)*)')
_PATTERN_HEADER_SEP = re.compile(r'^-+$')

def getBuildTime():
    return datetime.datetime.utcfromtimestamp(
        int(os.environ.get('SOURCE_DATE_EPOCH', time.time()))
    )


def getTitleDetails(string):
    array = string.split(".")

    title = array.pop().strip()
    chapter = ".".join(array)
    level = max(1, len(array))
    if array:
        toplevel = array[0]
    else:
        toplevel = False

    return {"title": title, "chapter": chapter,
            "level": level, "toplevel": toplevel}

def html_escape(s):
    """
    Same as html.escape() but without escaping single quotes.
    """
    s = html.escape(s, False)
    s = s.replace('"', "&quot;")
    return s

# Pre-compiled keyword regex and replacement cache
_keyword_regex_cache = {}

def _build_keyword_regex(keywords_list):
    """Build a single regex pattern to match all keywords."""
    escaped = [re.escape(k) for k in keywords_list]
    return re.compile('(' + '|'.join(escaped) + ')')

def _keyword_replacer(match, keyword_conflicts, chapters, keywordsCount):
    """Replace matched keyword with appropriate link."""
    keyword = match.group(1)
    
    # Count this occurrence
    if keyword not in keywordsCount:
        keywordsCount[keyword] = 0
    keywordsCount[keyword] += 1
    
    if keyword in keyword_conflicts:
        # Build dropdown for conflicting keywords
        chapter_list = ""
        for chapter in keyword_conflicts[keyword]:
            chapter_list += '<li><a href="#%s">%s</a></li>' % (
                quote("%s (%s)" % (keyword, chapters[chapter]['title'])),
                chapters[chapter]['title']
            )
        return ('<span class="dropdown">' +
                '<a class="dropdown-toggle" data-toggle="dropdown" href="#">' +
                keyword +
                '<span class="caret"></span>' +
                '</a>' +
                '<ul class="dropdown-menu">' +
                '<li class="dropdown-header">This keyword is available in sections :</li>' +
                chapter_list +
                '</ul>' +
                '</span>')
    else:
        return '<a href="#' + quote(keyword) + '">' + keyword + '</a>'

# Parse the whole document to insert links on keywords
def createLinks():
    global document, keywords, keywordsCount, keyword_conflicts, chapters
    print("Generating keywords links...", file=sys.stderr)

    # Process "..." delimited keywords (multi=True)
    pattern = _build_keyword_regex(keywords)
    
    def replacer(match):
        return _keyword_replacer(match, keyword_conflicts, chapters, keywordsCount)
    
    # Replace keywords in "..." context
    def replace_in_quotes(m):
        inner = m.group(1)
        # Check if inner content is a keyword
        if inner in keywords or inner in keyword_conflicts:
            return '"' + replacer(type('Match', (), {'group': lambda self, n: inner})()) + '"'
        return m.group(0)
    
    document = re.sub(r'"([^&]+?)"', replace_in_quotes, document)
    
    # Process - ... context (until newline)
    def replace_in_dash_context(m):
        prefix = m.group(1)
        rest = m.group(2)
        # Find keywords at start of rest
        for keyword in sorted(keywords, key=len, reverse=True):
            if rest.startswith(keyword):
                kw_len = len(keyword)
                link = replacer(type('Match', (), {'group': lambda self, n: keyword})())
                return prefix + link + rest[kw_len:]
        return m.group(0)
    
    document = re.sub(r'(\n- )([^\n]+)', replace_in_dash_context, document)
    
    # Handle "option X" short keywords
    for keyword in keywords:
        if keyword.startswith("option "):
            shortKeyword = keyword[len("option "):]
            if shortKeyword in keywordsCount:
                keywordsCount[shortKeyword] = keywordsCount.get(shortKeyword, 0)

# Global StringIO buffer for document building
_document_buffer = None

def documentAppend(text, retline = True):
    global _document_buffer
    _document_buffer.write(text)
    if retline:
        _document_buffer.write("\n")

def _get_document():
    """Get the current document content as a string."""
    global _document_buffer
    return _document_buffer.getvalue()

def _reset_document():
    """Reset the document buffer for a new conversion."""
    global _document_buffer
    _document_buffer = io.StringIO()

def init_parsers(pctxt):
    return [
        parser.underline.UnderlineParser(pctxt),
        parser.arguments.ArgumentParser(pctxt),
        parser.seealso.SeeAlsoParser(pctxt),
        parser.example.ExampleParser(pctxt),
        parser.table.TableParser(pctxt),
        parser.keyword.KeyWordParser(pctxt),
    ]

# The parser itself

def convert_all(infiles, outdir, base='', version='', haproxy_version=''):
    converted = []
    menu = []
    for infile in infiles:
        basefile = os.path.basename(infile).replace(".txt", ".html")
        outfile = os.path.join( outdir, basefile )

        pctxt = parser.PContext(
            TemplateLookup(
                directories=[
                    'templates'
                ],
                filesystem_checks=False
            )
        )
        data = convert(pctxt, infile, outfile, base, version, haproxy_version)
        converted.append((outfile, data))

        menu.append((basefile, data['pctxt'].context['headers']['subtitle']))

    for item in converted:
        outfile, data = item
        data['menu'] = menu

        print("Exporting to %s..." % outfile, file=sys.stderr)
        template = pctxt.templates.get_template('template.html')
        with open(outfile,'w') as fd:
            print(template.render(**data), file=fd)


def convert(pctxt, infile, outfile, base='', version='', haproxy_version=''):
    global document, keywords, keywordsCount, chapters, keyword_conflicts

    if base and base[:-1] != '/':
        base += '/'

    hasSummary = False

    # read data from the input file,
    # store everything as a list of string
    # after replacing tabulation characters
    # with 8 spaces
    with open(infile) as fd:
        data = [line.replace("\t", " "*8).rstrip() for line in fd.readlines()]

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

    print("Importing %s..." % infile, file=sys.stderr)

    nblines = len(data)
    i = j = 0
    while i < nblines:
        line = data[i].rstrip()
        if i < nblines - 1:
            next = data[i + 1].rstrip()
        else:
            next = ""
        if (line == "Summary" or re.match("^[0-9].*", line)) and (len(next) > 0) and (next[0] == '-'):
            #    and ("-" * len(line)).startswith(next):  # Fuzzy underline length detection
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
                print("Line `%i' exceeds 80 columns" % (i + 1), file=sys.stderr)

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

    _reset_document()

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
                    print("Adding '%s' to the summary" % details["title"], file=sys.stderr)
                    chapters[details["chapter"]] = details

    chapterIndexes = sorted(list(chapters.keys()), key=lambda chapter: list(map(int, chapter.split('.'))))

    for section in sections:
        details = section["details"]
        pctxt.details = details
        level = details["level"]
        title = details["title"]
        content = section["content"].rstrip()

        print("Parsing chapter %s..." % title, file=sys.stderr)

        if (title == "Summary") or (title and not hasSummary):
            summaryTemplate = pctxt.templates.get_template('summary.html')
            documentAppend(summaryTemplate.render(
                pctxt=pctxt,
                chapters=chapters,
                chapterIndexes=chapterIndexes,
            ))
            if title and not hasSummary:
                hasSummary = True
            else:
                continue

        if title:
            documentAppend('<a class="anchor" id="%s" name="%s"></a>' % (details["chapter"], details["chapter"]))
            if level == 1:
                documentAppend("<div class=\"page-header\">", False)
            documentAppend('<h%d id="chapter-%s" data-target="%s"><small><a class="small" href="#%s">%s.</a></small> %s</h%d>' % (level, details["chapter"], details["chapter"], details["chapter"], details["chapter"], html_escape(title), level))
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
            content = html_escape(content)
            content = _PATTERN_SECTION.sub(r'<a href="#\1">section \1</a>', content)

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
                if _PATTERN_HEADER_SEP.match(pctxt.get_line().strip()):
                    # Try to analyze the header of the file, assuming it follows
                    # those rules :
                    # - it begins with a "separator line" (several '-' chars)
                    # - then the document title
                    # - an optional subtitle
                    # - a new separator line
                    # - the version
                    # - the author
                    # - the date
                    pctxt.next()
                    pctxt.context['headers']['title'] = pctxt.get_line().strip()
                    pctxt.next()
                    subtitle = ""
                    while not _PATTERN_HEADER_SEP.match(pctxt.get_line().strip()):
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
                    if haproxy_version:
                        pctxt.context['headers']['version'] = 'version ' + haproxy_version

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
                for one_parser in parsers:
                    line = one_parser.parse(line)
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
                        parser.remove_indent(delay)
                        documentAppend('<pre class="text">%s\n</pre>' % "\n".join(delay), False)
                    delay = []
                    documentAppend(line, False)
                else:
                    while delay and delay[-1].strip() == "":
                        del delay[-1]
                    if delay:
                        parser.remove_indent(delay)
                        documentAppend('<pre class="text">%s\n</pre>' % "\n".join(delay), False)
                    delay = []
                    documentAppend(line, True)
                    pctxt.next()

            while delay and delay[-1].strip() == "":
                del delay[-1]
            if delay:
                parser.remove_indent(delay)
                documentAppend(
                    "<pre class=\"text\">{}\n</pre>".format("\n".join(delay)),
                    False
                )
            delay = []
            documentAppend('</div>')

    if not hasSummary:
        summaryTemplate = pctxt.templates.get_template('summary.html')
        print(chapters)
        summary = summaryTemplate.render(
            pctxt=pctxt,
            chapters=chapters,
            chapterIndexes=chapterIndexes,
        )
        _reset_document()
        _document_buffer.write(summary)

    # Get the document string from the buffer
    document = _get_document()

    # Log warnings for keywords defined in several chapters
    keyword_conflicts = {}
    for keyword in keywords:
        keyword_chapters = list(keywords[keyword])
        keyword_chapters.sort()
        if len(keyword_chapters) > 1:
            print("Multi section keyword : \"{}\" in chapters {}".
                  format(keyword, list(keyword_chapters)), file=sys.stderr)
            keyword_conflicts[keyword] = keyword_chapters

    keywords = list(keywords)
    keywords.sort()

    createLinks()

    # Add the keywords conflicts to the keywords list to make
    # them available in the search form and remove the original
    # keyword which is now useless
    for keyword in keyword_conflicts:
        sections = keyword_conflicts[keyword]
        offset = keywords.index(keyword)
        for section in sections:
            keywords.insert(offset, "{} ({})".format(keyword, chapters[section]['title']))
            offset += 1
        keywords.remove(keyword)

    try:
        footerTemplate = pctxt.templates.get_template('footer.html')
        footer = footerTemplate.render(
            pctxt=pctxt,
            headers=pctxt.context['headers'],
            document=document,
            chapters=chapters,
            chapterIndexes=chapterIndexes,
            keywords=keywords,
            keywordsCount=keywordsCount,
            keyword_conflicts=keyword_conflicts,
            version=version,
            date=getBuildTime().strftime("%Y/%m/%d"),
        )
    except TopLevelLookupException:
        footer = ""

    return {
            'pctxt': pctxt,
            'headers': pctxt.context['headers'],
            'base': base,
            'document': document,
            'chapters': chapters,
            'chapterIndexes': chapterIndexes,
            'keywords': keywords,
            'keywordsCount': keywordsCount,
            'keyword_conflicts': keyword_conflicts,
            'version': version,
            'haproxy_major_version': re.match(r'(\d+\.\d+)', haproxy_version).group(1) if haproxy_version else None,
            'date': getBuildTime().strftime("%Y/%m/%d"),
            'footer': footer
    }
