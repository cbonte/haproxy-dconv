<tr>
    % for col in columns:
        <% data = col['data'] %>\
        <%
            style = ''
            if data in ['yes']:
                style = ' class="alert-success pagination-centered"'
            elif data in ['no']:
                style = ' class="alert-error pagination-centered"'
            elif data in ['X', '-', '*']:
                style = ' class="pagination-centered"'
            else:
                try:
                    int(data.strip())
                    style = ' class="pagination-right"'
                except:
                    pass
        %>\
<td${style}>\
            % if "keyword" in col:
<a href="#${col['toplevel']}-${col['keyword']}">\
                % for extra in col['extra']:
<span class="pull-right">${extra}</span>\
                % endfor
${data}</a>\
            % else:
${data}\
            % endif
</td>
    % endfor
</tr>
