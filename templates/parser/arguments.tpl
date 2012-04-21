<span class="label label-info">${label}</span>\
% if desc:
 ${desc}
% endif
% if content:
<pre class="prettyprint alert-info">
% for line in content:
${line}
% endfor
</pre>
% else:
<%doc>Empty line to separate text</%doc>
% endif