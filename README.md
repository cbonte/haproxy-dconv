# HAProxy Documentation Converter

In its current state, the HAProxy is converting the HAProxy documentation
.txt files into HTML. The purpose of this project is to ultimately convert
the HAProxy documentation into a more generic format (example : ReStructuredText)
that would allow for an easier spreading of various output files (.pdf,
.html, .epub, etc).

# Documentation

## Python version and requirements

At the moment, we use Mako as a templating engine to render the documentation
into HTML format. The current version of the source code is tested against
Python 3.6 and Mako version 1.0.6.

## Quick execute

```shell
# will clone the HAProxy source repository into the './haproxy/' folder
git clone http://git.haproxy.org/git/haproxy.git
# will execute the conversion procedure onto 'haproxy/doc/configuration.txt'
# and output the result into the 'haproxy/doc/configuration.html' file
python dconv.py -g haproxy -o haproxy/doc/ haproxy/doc/configuration.txt
```

## Documentation

A job (see tools/generate-docs.sh)
periodically fetches last commits from HAProxy 1.4 to the latest dev
branch and produces up-to-date documentation.

Links are available at this URL http://cbonte.github.io/haproxy-dconv/

## Contribute

The project now lives by itself, as it is sufficiently useable.
But I'm sure we can do even better.
Feel free to report feature requests or provide patches !

