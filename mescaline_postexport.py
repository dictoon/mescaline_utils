
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

HAIR_MATERIAL_MARKER = "hood_hair"
NEW_ROOT_HAIR_BRDF_NAME = "hood_hair_brdf"

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

def set_param(entity, name, value):
    param = entity.find("parameter[@name='" + name + "']")
    if param is None:
        param = xml.Element('parameter')
        param.attrib['name'] = name
        param.attrib['value'] = value
        entity.insert(0, param)
    else:
        param.attrib['value'] = value

def add_hair_bsdf_network(assembly, reflectance_name):
    print("Adding BSDF {0} with reflectance {1} to assembly {2}...".format(NEW_ROOT_HAIR_BRDF_NAME, reflectance_name, assembly.attrib['name']))
    hair_brdf = xml.Element('bsdf')
    hair_brdf.attrib['name'] = NEW_ROOT_HAIR_BRDF_NAME
    hair_brdf.attrib['model'] = "microfacet_brdf"
    set_param(hair_brdf, "mdf", "ward")
    set_param(hair_brdf, "mdf_parameter", "0.3")
    set_param(hair_brdf, "reflectance", reflectance_name)
    set_param(hair_brdf, "reflectance_multiplier", "1.0")
    set_param(hair_brdf, "fresnel_multiplier", "0.1")
    assembly.append(hair_brdf)

def replace_hair_shader(root):
    for assembly in root.iter('assembly'):
        old_hair_bsdf_names = set()

        for material in assembly.findall('material'):
            if HAIR_MATERIAL_MARKER in material.attrib['name']:
                old_hair_bsdf_names.add(fixup_hair_material(assembly, material))

        # assert len(old_hair_bsdf_names) <= 1

        if len(old_hair_bsdf_names) > 0:
            old_bsdf_name = old_hair_bsdf_names.pop()
            old_bsdf = assembly.find('bsdf[@name="' + old_bsdf_name + '"]')
            old_bsdf_model = old_bsdf.attrib['model']
            if old_bsdf_model == 'bsdf_mix':
                bsdf0_param = old_bsdf.find('parameter[@name="bsdf0"]')
                bsdf0_name = bsdf0_param.attrib['value']
                old_bsdf = assembly.find('bsdf[@name="' + bsdf0_name + '"]')
            reflectance_param = old_bsdf.find('parameter[@name="reflectance"]')
            reflectance_name = reflectance_param.attrib['value']
            add_hair_bsdf_network(assembly, reflectance_name)

def tweak_frames(root):
    for frame in root.iter('frame'):
        print("Tweaking frame {0}...".format(frame.attrib['name']))
        set_param(frame, "filter", "gaussian")
        set_param(frame, "filter_size", "2.5")

def process_file(filepath):
    print("Processing {0}...".format(filepath))

    tree = load_project_file(filepath)
    root = tree.getroot()

    assign_render_layers([ edf for edf in root.iter('edf') ])
    assign_render_layers([ light for light in root.iter('light') ])

    replace_hair_shader(root)

    tweak_frames(root)

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
