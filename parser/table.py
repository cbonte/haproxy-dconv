import re
import sys
import parser

class TableParser(parser.Parser):
    def __init__(self, pctxt):
        parser.Parser.__init__(self, pctxt)
        self.table1Pattern = re.compile(r'^ *(-+\+)+-+')
        self.table2Pattern = re.compile(r'^ *\+(-+\+)+')

    def parse(self, line):
        global document, keywords, keywordsCount, chapters, keyword_conflicts

        pctxt = self.pctxt

        if pctxt.context['headers']['subtitle'] != 'Configuration Manual':
            # Quick exit
            return line
        elif pctxt.details['chapter'] == "4":
            # BUG: the matrix in chapter 4. Proxies is not well displayed, we skip this chapter
            return line

        if pctxt.has_more_lines(1):
            nextline = pctxt.get_line(1)
        else:
            nextline = ""

        if self.table1Pattern.match(nextline):
            # activate table rendering only for the Configuration Manual
            lineSeparator = nextline
            nbColumns = nextline.count("+") + 1
            extraColumns = 0
            print("Entering table mode (%d columns)" % nbColumns, file=sys.stderr)
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
                        for j in range(0, len(columns)):
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
                        for j in range(0, nbColumns):
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
            print("Leaving table mode", file=sys.stderr)
            pctxt.next() # skip useless next line
            pctxt.stop = True

            return self.renderTable(table, nbColumns, pctxt.details["toplevel"])
        # elif self.table2Pattern.match(line):
        #    return self.parse_table_format2()
        elif line.find("May be used in sections") != -1 or line.find("Usable in:") != -1:
            nextline = pctxt.get_line(1)
            rows = []
            headers = line.split(":")
            rows.append(headers[1].split("|"))
            rows.append(nextline.split("|"))
            table = {
                    "rows": rows,
                    "title": headers[0]
            }
            pctxt.next(2)  # skip this previous table
            pctxt.stop = True

            return self.renderTable(table)

        return line


    def parse_table_format2(self):
        pctxt = self.pctxt

        linesep = pctxt.get_line()
        rows = []

        pctxt.next()
        maxcols = 0
        while pctxt.get_line().strip().startswith("|"):
            row = pctxt.get_line().strip()[1:-1].split("|")
            rows.append(row)
            maxcols = max(maxcols, len(row))
            pctxt.next()
            if pctxt.get_line() == linesep:
                # TODO : find a way to define a special style for next row
                pctxt.next()
        pctxt.stop = True

        return self.renderTable(rows, maxcols)

    # Render tables detected by the conversion parser
    def renderTable(self, table, maxColumns = 0, toplevel = None):
        pctxt  = self.pctxt
        template = pctxt.templates.get_template("parser/table.tpl")

        res = ""

        title = None
        if isinstance(table, dict):
            title = table["title"]
            table = table["rows"]

        if not maxColumns:
            maxColumns = len(table[0])

        rows = []

        mode = "th"
        headerLine = ""
        hasKeywords = False
        i = 0
        for row in table:
            line = ""

            if i == 0:
                row_template = pctxt.templates.get_template("parser/table/header.tpl")
            else:
                row_template = pctxt.templates.get_template("parser/table/row.tpl")

            if i > 1 and (i  - 1) % 20 == 0 and len(table) > 50:
                # Repeat headers periodically for long tables
                rows.append(headerLine)

            j = 0
            cols = []
            for column in row:
                if j >= maxColumns:
                    break

                tplcol = {}

                data = column.strip()
                keyword = column
                if j == 0 and i == 0 and keyword == 'keyword':
                    hasKeywords = True
                if j == 0 and i != 0 and hasKeywords:
                    if keyword.startswith("[no] "):
                        keyword = keyword[len("[no] "):]
                    tplcol['toplevel'] = toplevel
                    tplcol['keyword'] = keyword
                tplcol['extra'] = []
                if j == 0 and len(row) > maxColumns:
                    for k in range(maxColumns, len(row)):
                        tplcol['extra'].append(row[k])
                tplcol['data'] = data
                cols.append(tplcol)
                j += 1
            mode = "td"

            line = row_template.render(
                pctxt=pctxt,
                columns=cols
            ).strip()
            if i == 0:
                headerLine = line

            rows.append(line)

            i += 1

        return template.render(
            pctxt=pctxt,
            title=title,
            rows=rows,
        )
