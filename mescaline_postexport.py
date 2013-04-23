
#
# Copyright (c) 2013 Francois Beaune
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

import xml.etree.ElementTree as xml
import os
import sys


#--------------------------------------------------------------------------------------------------
# Load/write a given project file to/from memory.
#--------------------------------------------------------------------------------------------------

def load_project_file(filepath):
    tree = xml.ElementTree()

    try:
        tree.parse(filepath)
    except IOError:
        print("Failed to load project file {0}.".format(filepath))
        sys.exit(1)

    return tree

def write_project_file(filepath, tree):
    try:
        tree.write(filepath)
    except IOError:
        print("Failed to write project file {0}.".format(filepath))
        sys.exit(1)


#--------------------------------------------------------------------------------------------------
# Process a given project file.
#--------------------------------------------------------------------------------------------------

NEW_ROOT_HAIR_BRDF_NAME = "h_hair_mat_brdf_root"

def assign_render_layers(nodes):
    for node in nodes:
        name = node.attrib['name']
        if node.find("parameter[@name='render_layer']") is None:
            print("Assigning entity {0} to a render layer of the same name...".format(name))
            param = xml.Element('parameter')
            param.attrib['name'] = "render_layer"
            param.attrib['value'] = name
            node.insert(0, param)
        else:
            print("Entity {0} already is already assigned to a render layer.".format(name))

def fixup_hair_material(assembly, material):
    bsdf_param = material.find("parameter[@name='bsdf']")
    old_bsdf_name = bsdf_param.attrib['value']
    print("Assigning BSDF {0} to material {1} (was: {2})...".format(NEW_ROOT_HAIR_BRDF_NAME, material.attrib['name'], old_bsdf_name))
    bsdf_param.attrib['value'] = NEW_ROOT_HAIR_BRDF_NAME
    return old_bsdf_name

def add_param(entity, name, value):
    param = xml.Element('parameter')
    param.attrib['name'] = name
    param.attrib['value'] = value
    entity.insert(0, param)
    
def add_hair_bsdf_network(assembly, old_bsdf_name):
    print("Adding BSDF {0} to assembly {1}...".format(NEW_ROOT_HAIR_BRDF_NAME, assembly.attrib['name']))

    root_brdf = xml.Element('bsdf')
    root_brdf.attrib['name'] = NEW_ROOT_HAIR_BRDF_NAME
    root_brdf.attrib['model'] = "bsdf_mix"
    add_param(root_brdf, "bsdf0", old_bsdf_name)
    add_param(root_brdf, "weight0", "0.0")
    add_param(root_brdf, "bsdf1", "h_hair_mat_glossy_brdf")
    add_param(root_brdf, "weight1", "0.1")
    assembly.append(root_brdf)

    glossy_brdf = xml.Element('bsdf')
    glossy_brdf.attrib['name'] = "h_hair_mat_glossy_brdf"
    glossy_brdf.attrib['model'] = "microfacet_brdf"
    add_param(glossy_brdf, "fresnel_multiplier", "0.0")
    add_param(glossy_brdf, "mdf", "ward")
    add_param(glossy_brdf, "mdf_parameter", "0.8")
    add_param(glossy_brdf, "reflectance", old_bsdf_name + ".reflectance")
    add_param(glossy_brdf, "reflectance_multiplier", "1.0")
    assembly.append(glossy_brdf)

def replace_hair_shader(root):
    for assembly in root.iter('assembly'):
        old_hair_bsdfs = set()

        for material in assembly.findall('material'):
            if "hair_mat" in material.attrib['name']:
                old_hair_bsdfs.add(fixup_hair_material(assembly, material))

        assert len(old_hair_bsdfs) <= 1

        if len(old_hair_bsdfs) > 0:
            add_hair_bsdf_network(assembly, old_hair_bsdfs.pop())

def process_file(filepath):
    print("Processing {0}...".format(filepath))

    tree = load_project_file(filepath)
    root = tree.getroot()

    assign_render_layers([ edf for edf in root.iter('edf') ])
    assign_render_layers([ light for light in root.iter('light') ])

    replace_hair_shader(root)

    write_project_file(filepath, tree)


#--------------------------------------------------------------------------------------------------
# Process all files in the current directory.
#--------------------------------------------------------------------------------------------------

def process_files_in_current_directory():
    for dirpath, dirnames, filenames in os.walk("."):
        for filename in filenames:
            if os.path.splitext(filename)[1] == ".appleseed":
                process_file(os.path.join(dirpath, filename))


#--------------------------------------------------------------------------------------------------
# Entry point.
#--------------------------------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        process_files_in_current_directory()
    else:
        for filepath in sys.argv[1:]:
            process_file(filepath)

if __name__ == '__main__':
    main()
