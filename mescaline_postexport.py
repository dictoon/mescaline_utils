
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
# Utilities.
#--------------------------------------------------------------------------------------------------

def set_param(entity, name, value):
    param = entity.find("parameter[@name='" + name + "']")
    if param is None:
        param = xml.Element('parameter')
        param.attrib['name'] = name
        param.attrib['value'] = value
        entity.insert(0, param)
    else:
        param.attrib['value'] = value

def get_param(entity, name):
    param = entity.find("parameter[@name='" + name + "']")
    return None if param is None else param.attrib['value']

def find_entity(root, type, name):
    # return next(root.iterfind(type + "[@name='" + name + "']"), None)
    for node in root.iter(type):
        if node.attrib['name'] == name:
            return node
    return None

def find_material(root, name):
    return find_entity(root, 'material', name)

def find_bsdf(root, name):
    return find_entity(root, 'bsdf', name)

def set_material_fresnel(root, material_marker, new_fresnel):
    bsdfs = set()

    for material in root.iter('material'):
        if material_marker in material.attrib['name']:
            bsdf = find_bsdf(root, get_param(material, "bsdf"))
            assert bsdf.attrib['model'] == 'bsdf_mix'
            bsdfs.add(bsdf)

    for mix_bsdf in bsdfs:
        microfacet_bsdf = find_bsdf(root, get_param(mix_bsdf, "bsdf1"))
        old_fresnel_multiplier = get_param(microfacet_bsdf, "fresnel_multiplier")
        print("Replacing Fresnel multiplier \"{0}\" by \"{1}\" in BSDF \"{2}\"...".format(old_fresnel_multiplier, new_fresnel, microfacet_bsdf.attrib['name']))
        set_param(microfacet_bsdf, "fresnel_multiplier", new_fresnel)


#--------------------------------------------------------------------------------------------------
# Assign light-emitting entities (EDFs, lights) to separate render layers.
#--------------------------------------------------------------------------------------------------

def assign_render_layers(nodes):
    for node in nodes:
        name = node.attrib['name']
        if node.find("parameter[@name='render_layer']") is None:
            print("Assigning entity \"{0}\" to render layer \"{0}\"...".format(name))
            set_param(node, 'render_layer', name)
        else:
            print("Entity \"{0}\" is already assigned to a render layer.".format(name))


#--------------------------------------------------------------------------------------------------
# Tweak the robe shader.
#--------------------------------------------------------------------------------------------------

def tweak_robe_shader(root):
    set_material_fresnel(root, "hood_robe", "0.3")


#--------------------------------------------------------------------------------------------------
# Tweak trees shaders.
#--------------------------------------------------------------------------------------------------

def tweak_trees_shaders(root):
    set_material_fresnel(root, "big_branches_", "0.1")
    set_material_fresnel(root, "big_leaves_",   "0.1")
    set_material_fresnel(root, "big_leaves_",   "0.1")
    set_material_fresnel(root, "plant_",        "0.1")


#--------------------------------------------------------------------------------------------------
# Tweak the hair shader.
#--------------------------------------------------------------------------------------------------

HAIR_MATERIAL_MARKER = "hood_hair"
NEW_ROOT_HAIR_BRDF_NAME = "hood_hair_brdf"

def fixup_hair_material(assembly, material):
    old_bsdf_name = get_param(material, 'bsdf')
    print("Replacing BSDF \"{0}\" by BSDF \"{1}\" in material \"{2}\"...".format(old_bsdf_name, NEW_ROOT_HAIR_BRDF_NAME, material.attrib['name']))
    set_param(material, 'bsdf', NEW_ROOT_HAIR_BRDF_NAME)
    return old_bsdf_name

def add_hair_bsdf_network(assembly, reflectance_name):
    print("Adding BSDF \"{0}\" with reflectance \"{1}\" to assembly \"{2}\"...".format(NEW_ROOT_HAIR_BRDF_NAME, reflectance_name, assembly.attrib['name']))
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
            old_bsdf = find_bsdf(assembly, old_bsdf_name)
            if old_bsdf.attrib['model'] == 'bsdf_mix':
                old_bsdf = find_bsdf(assembly, get_param(old_bsdf, 'bsdf0'))
            reflectance_name = get_param(old_bsdf, 'reflectance')
            add_hair_bsdf_network(assembly, reflectance_name)


#--------------------------------------------------------------------------------------------------
# Tweak the settings of the frames.
#--------------------------------------------------------------------------------------------------

def tweak_frames(root):
    for frame in root.iter('frame'):
        print("Tweaking frame \"{0}\"...".format(frame.attrib['name']))
        set_param(frame, "filter", "gaussian")
        set_param(frame, "filter_size", "2.5")


#--------------------------------------------------------------------------------------------------
# Applies a series of tweaks to a given appleseed project file.
#--------------------------------------------------------------------------------------------------

def process_file(filepath):
    print("Processing {0}...".format(filepath))

    tree = load_project_file(filepath)
    root = tree.getroot()

    assign_render_layers([ edf for edf in root.iter('edf') ])
    assign_render_layers([ light for light in root.iter('light') ])

    tweak_robe_shader(root)
    tweak_trees_shaders(root)
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
