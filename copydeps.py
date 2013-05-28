#!/usr/bin/python

#
# This source file is part of appleseed.
# Visit http://appleseedhq.net/ for additional information and resources.
#
# This software is released under the MIT license.
#
# Copyright (c) 2012-2013 Jonathan Topf
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import os
import shutil
import sys
import xml.dom.minidom as xml


#--------------------------------------------------------------------------------------------------
# Extract dependencies from project files.
#--------------------------------------------------------------------------------------------------

def get_project_files(directory):
    project_files = []

    for entry in os.listdir(directory):
        filepath = os.path.join(directory, entry)
        if os.path.isfile(filepath):
            if os.path.splitext(filepath)[1] == '.appleseed':
                project_files.append(filepath)

    return project_files

def convert_path_to_local(path):
    if os.name == "nt":
        return path.replace('/', '\\')
    else:
        return path.replace('\\', '/')

def extract_project_deps(project_filepath):
    try:
        with open(project_filepath, 'r') as file:
            contents = file.read()
    except:
        log.warning("failed to acquire {0}.".format(project_filepath))
        return False, set()

    deps = set()
    directory = os.path.split(project_filepath)[0]

    for node in xml.parseString(contents).getElementsByTagName('parameter'):
        if node.getAttribute('name') == 'filename':
            filepath = node.getAttribute('value')
            filepath = convert_path_to_local(filepath)
            filepath = os.path.join(directory, filepath)
            deps.add(filepath)

    for node in xml.parseString(contents).getElementsByTagName('parameters'):
        if node.getAttribute('name') == 'filename':
            for child in node.childNodes:
                if child.nodeType == xml.Node.ELEMENT_NODE:
                    filepath = child.getAttribute('value')
                    filepath = convert_path_to_local(filepath)
                    filepath = os.path.join(directory, filepath)
                    deps.add(filepath)

    return True, deps


#--------------------------------------------------------------------------------------------------
# Entry point.
#--------------------------------------------------------------------------------------------------

def main():
    dest_root_dir = sys.argv[1]

    already_copied = set()

    for project_file in get_project_files("."):
        print("copying assets of {0}: ".format(project_file))

        success, deps = extract_project_deps(project_file)
        copied = 0

        for dep in deps:
            dest_filepath = os.path.join(dest_root_dir, dep)
            
            if dest_filepath in already_copied:
                print("already copied {0}...".format(dest_filepath))
                continue

            already_copied.add(dest_filepath)

            if os.path.isfile(dest_filepath):
                print("skipping {0}...".format(dest_filepath))
                continue

            dest_dir = os.path.dirname(dest_filepath)

            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            print("copying {0} to {1}...".format(dep, dest_filepath))
            shutil.copyfile(dep, dest_filepath)

            copied += 1

        print("copied {0} asset files.".format(copied))

if __name__ == '__main__':
    main()
