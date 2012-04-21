<span class="label label-success">${label}</span>
<pre class="prettyprint">
% if desc:
<div class="example-desc">${desc}</div>
% endif
% for line in content:
${line}
% endfor
</pre>