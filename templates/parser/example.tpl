<div class="separator">
<span class="label label-success">${label}</span>
<pre class="prettyprint">
% if desc:
<div class="example-desc">${desc}</div>\
% endif
<code>\
% for line in content:
${line}
% endfor
</code></pre>
</div>