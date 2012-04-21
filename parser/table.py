import re
import sys

class Parser:
    def __init__(self):
        self.tablePattern = re.compile(r'^ *(-+\+)+-+')

    def parse(self, pctxt, line):
        global document, keywords, keywordsCount, chapters, keyword_conflicts

        res = ""

        if pctxt.has_more_lines(1):
            nextline = pctxt.get_line(1)
        else:
            nextline = ""

        if pctxt.context['headers']['subtitle'] == 'Configuration Manual' and self.tablePattern.match(nextline):
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
            res = self.renderTable(table, nbColumns, pctxt.details["toplevel"])
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
            res = self.renderTable(table)
            pctxt.next(2)  # skip this previous table
            pctxt.stop = True
        else:
            res = line

        return res

    # Render tables detected by the conversion parser
    def renderTable(self, table, maxColumns = 0, hasKeywords = False):
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
