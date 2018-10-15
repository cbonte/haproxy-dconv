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

import os
from optparse import OptionParser

from parser import converter, git_parser


def main():
    """
    Main script to execute the conversion process
    """

    usage = "Usage: %prog [options] file..."

    optparser = OptionParser(
        description='Generate HTML Document from HAProxy configuration.txt',
        usage=usage
    )
    optparser.add_option(
        '--git-directory', '-g',
        help='Optional git directory for input files, '
        'to determine haproxy details'
    )
    optparser.add_option(
        '--output-directory', '-o', default='.',
        help='Destination directory to store files, '
        'instead of the current working directory'
    )
    optparser.add_option(
        '--base', '-b', default='', help='Base directory for relative links'
    )
    (option, files) = optparser.parse_args()

    if not files:
        optparser.print_help()
        exit(1)

    option.output_directory = os.path.abspath(option.output_directory)
    if option.git_directory:
        option.git_directory = os.path.abspath(option.git_directory)

    os.chdir(os.path.dirname(__file__))
    # check the haproxy-dconv repository version
    dconv_version = git_parser.get_git_version_from_cwd()
    if not dconv_version:
        sys.exit(1)
    haproxy_version = git_parser.get_git_version_in_path(
                            option.git_directory
                      )
    converter.convert_all(files, option.output_directory, option.base,
                          version=dconv_version, haproxy_version=haproxy_version)


if __name__ == '__main__':
    main()
