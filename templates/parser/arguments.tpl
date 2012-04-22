<div class="separator">
<span class="label label-info">${label}</span>\
% if desc:
 ${desc}
% endif
% if content:
<pre class="prettyprint arguments">${"\n".join(content)}</pre>
% endif
</div>
