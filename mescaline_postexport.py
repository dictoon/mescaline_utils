
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

import argparse
import xml.etree.ElementTree as xml
import os
import shutil
import subprocess
import sys


#--------------------------------------------------------------------------------------------------
# Constants.
#--------------------------------------------------------------------------------------------------

BACKUP_DIRECTORY = "_backup"
TEXTURES_DIRECTORY = "_textures"
SKY_TEXTURE_FILENAME = "sky_dusk_00.exr"


#--------------------------------------------------------------------------------------------------
# Update a given project file.
#--------------------------------------------------------------------------------------------------

def update_project_file(filepath, tool_path, additional_args=None):
    args = [tool_path, filepath]

    if additional_args is not None:
        args += additional_args

    subprocess.call(args)


#--------------------------------------------------------------------------------------------------
# Load/write a given project file to/from memory.
#--------------------------------------------------------------------------------------------------

def load_project_file(filepath):
    tree = xml.ElementTree()

    try:
        tree.parse(filepath)
    except IOError:
        print("ERROR: failed to load project file {0}.".format(filepath))
        sys.exit(1)

    return tree

def write_project_file(filepath, tree):
    try:
        tree.write(filepath)
    except IOError:
        print("ERROR: failed to write project file {0}.".format(filepath))
        sys.exit(1)


#--------------------------------------------------------------------------------------------------
# Utility functions.
#--------------------------------------------------------------------------------------------------

def walk(directory, recursive):
    if recursive:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                yield os.path.join(dirpath, filename)
    else:
        dirpath, dirnames, filenames = os.walk(directory).next()
        for filename in filenames:
            yield os.path.join(dirpath, filename)

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

def find_surface_shader(root, name):
    return find_entity(root, 'surface_shader', name)

def collect_bsdfs_for_material(root, material_marker):
    bsdfs = set()

    for material in root.iter('material'):
        if material_marker in material.attrib['name']:
            bsdfs.add(find_bsdf(root, get_param(material, "bsdf")))

    return bsdfs

def collect_surface_shaders_for_material(root, material_marker):
    surface_shaders = set()

    for material in root.iter('material'):
        if material_marker in material.attrib['name']:
            surface_shaders.add(find_surface_shader(root, get_param(material, "surface_shader")))

    return surface_shaders

def set_material_fresnel(root, material_marker, fresnel):
    for mix_bsdf in collect_bsdfs_for_material(root, material_marker):
        assert mix_bsdf.attrib['model'] == 'bsdf_mix'
        microfacet_bsdf = find_bsdf(root, get_param(mix_bsdf, "bsdf1"))
        print("    Setting Fresnel multiplier to \"{0}\" on BSDF \"{1}\"...".format(fresnel, microfacet_bsdf.attrib['name']))
        set_param(microfacet_bsdf, "fresnel_multiplier", fresnel)

def set_material_glossy_reflectance(root, material_marker, reflectance):
    for mix_bsdf in collect_bsdfs_for_material(root, material_marker):
        assert mix_bsdf.attrib['model'] == 'bsdf_mix'
        microfacet_bsdf = find_bsdf(root, get_param(mix_bsdf, "bsdf1"))
        print("    Setting reflectance to \"{0}\" on BSDF \"{1}\"...".format(reflectance, microfacet_bsdf.attrib['name']))
        set_param(microfacet_bsdf, "reflectance", reflectance)

def set_material_glossiness(root, material_marker, glossiness):
    for mix_bsdf in collect_bsdfs_for_material(root, material_marker):
        assert mix_bsdf.attrib['model'] == 'bsdf_mix'
        microfacet_bsdf = find_bsdf(root, get_param(mix_bsdf, "bsdf1"))
        print("    Setting glossiness to \"{0}\" on BSDF \"{1}\"...".format(glossiness, microfacet_bsdf.attrib['name']))
        set_param(microfacet_bsdf, "mdf_parameter", glossiness)

def set_material_translucency(root, material_marker, translucency):
    for surface_shader in collect_surface_shaders_for_material(root, material_marker):
        assert surface_shader.attrib['model'] == 'physical_surface_shader'
        print("    Setting translucency to \"{0}\" on surface shader \"{1}\"...".format(translucency, surface_shader.attrib['name']))
        set_param(surface_shader, "translucency", translucency)

def set_material_sample_count(root, material_marker, sample_count):
    for surface_shader in collect_surface_shaders_for_material(root, material_marker):
        assert surface_shader.attrib['model'] == 'physical_surface_shader'
        print("    Setting sample count to \"{0}\" on surface shader \"{1}\"...".format(sample_count, surface_shader.attrib['name']))
        set_param(surface_shader, "front_lighting_samples", sample_count)

def set_object_instance_ray_bias(root, object_instance_marker, bias):
    for object_instance in root.iter('object_instance'):
        object_instance_name = object_instance.attrib['name']
        if object_instance_marker in object_instance_name:
            print("    Setting ray bias (incoming direction, {0}) on object instance \"{1}\"...".format(bias, object_instance_name))
            set_param(object_instance, 'ray_bias_method', 'incoming_direction')
            set_param(object_instance, 'ray_bias_distance', bias)


#--------------------------------------------------------------------------------------------------
# Replace mesh file extensions (from .obj to .binarymesh).
#--------------------------------------------------------------------------------------------------

def replace_mesh_file_extension(param):
    if os.path.splitext(param.attrib['value'])[1].lower() != '.obj':
        return 0

    param.attrib['value'] = os.path.splitext(param.attrib['value'])[0] + '.binarymesh'

    return 1

def replace_mesh_file_extensions(root):
    found = 0

    for object in root.iter('object'):
        if object.attrib['model'] != 'mesh_object':
            continue

        for parameter in object.findall('parameter'):
            if parameter.attrib['name'] == 'filename':
                found += replace_mesh_file_extension(parameter)

        for parameters in object.iter('parameters'):
            for parameter in parameters.findall('parameter'):
                found += replace_mesh_file_extension(parameter)

    print("  Replaced mesh file extension on {0} file paths.".format(found))


#--------------------------------------------------------------------------------------------------
# Replace the hair shader.
#--------------------------------------------------------------------------------------------------

HAIR_MATERIAL_MARKER = "hood_hair"
NEW_ROOT_HAIR_BRDF_NAME = "hood_hair_brdf_F972278D-F40C-4C72-95F0-E25E509FB62E"

def fixup_hair_material(assembly, material):
    old_bsdf_name = get_param(material, 'bsdf')
    print("    Replacing BSDF \"{0}\" by BSDF \"{1}\" in material \"{2}\"...".format(old_bsdf_name, NEW_ROOT_HAIR_BRDF_NAME, material.attrib['name']))
    set_param(material, 'bsdf', NEW_ROOT_HAIR_BRDF_NAME)

def add_hair_bsdf_network(assembly, reflectance_name):
    print("    Adding BSDF \"{0}\" with reflectance \"{1}\" to assembly \"{2}\"...".format(NEW_ROOT_HAIR_BRDF_NAME, reflectance_name, assembly.attrib['name']))
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
    print("  Replacing hair shader:")

    for assembly in root.iter('assembly'):
        old_hair_bsdf_names = set()

        for material in assembly.findall('material'):
            if HAIR_MATERIAL_MARKER in material.attrib['name']:
                old_hair_bsdf_names.add(get_param(material, 'bsdf'))
                fixup_hair_material(assembly, material)

        # assert len(old_hair_bsdf_names) <= 1

        if len(old_hair_bsdf_names) > 0:
            old_bsdf_name = old_hair_bsdf_names.pop()
            old_bsdf = find_bsdf(assembly, old_bsdf_name)
            if old_bsdf.attrib['model'] == 'bsdf_mix':
                old_bsdf = find_bsdf(assembly, get_param(old_bsdf, 'bsdf0'))
            reflectance_name = get_param(old_bsdf, 'reflectance')
            add_hair_bsdf_network(assembly, reflectance_name)


#--------------------------------------------------------------------------------------------------
# Tweak the shaders on various parts of the hood.
#--------------------------------------------------------------------------------------------------

def tweak_hood_shaders(root):
    print("  Tweaking hood's robe shaders:")
    set_material_fresnel(root, "hood_robe", "0.05")
    set_material_fresnel(root, "hood_cap", "0.05")
    set_object_instance_ray_bias(root, "hood_robe", "-0.05")

    print("  Tweaking hood's glove shader:")
    set_material_fresnel(root, "hood_glove", "0.3")
    set_material_glossy_reflectance(root, "hood_glove", "0.04 0.04 0.04")

    print("  Tweaking hood's shoes shader:")
    set_material_fresnel(root, "hood_shoe", "0.3")
    set_material_glossy_reflectance(root, "hood_shoe", "0.04 0.04 0.04")

    print("  Tweaking hood's body shaders:")
    set_material_sample_count(root, "_face_", "8")
    set_material_sample_count(root, "hood_body", "8")

    print("  Tweaking hood's basket shaders:")
    set_material_fresnel(root, "basket", "0.05")


#--------------------------------------------------------------------------------------------------
# Tweak the shaders on various parts of the wolf.
#--------------------------------------------------------------------------------------------------

WOLF_EYE_MATERIAL_MARKER = "wolf_eye"
NEW_WOLF_EYE_SURFACE_SHADER_NAME = "wolf_eye_surface_shader_8A421E4D-49AA-4FF6-A6A2-05028708187B"

def fixup_wolf_eye_material(assembly, material):
    old_surface_shader_name = get_param(material, 'surface_shader')
    print("    Replacing surface shader \"{0}\" by surface shader \"{1}\" in material \"{2}\"...".format(old_surface_shader_name, NEW_WOLF_EYE_SURFACE_SHADER_NAME, material.attrib['name']))
    set_param(material, 'surface_shader', NEW_WOLF_EYE_SURFACE_SHADER_NAME)

def add_wolf_eye_surface_shader(assembly, reflectance_name):
    print("    Adding surface shader \"{0}\" with color \"{1}\" to assembly \"{2}\"...".format(NEW_WOLF_EYE_SURFACE_SHADER_NAME, reflectance_name, assembly.attrib['name']))
    eye_shader = xml.Element('surface_shader')
    eye_shader.attrib['name'] = NEW_WOLF_EYE_SURFACE_SHADER_NAME
    eye_shader.attrib['model'] = "constant_surface_shader"
    set_param(eye_shader, "color", reflectance_name)
    assembly.append(eye_shader)

def replace_wolf_eye_shader(root):
    print("  Replacing wolf's eye shader:")

    for assembly in root.iter('assembly'):
        old_wolf_eye_bsdf_names = set()

        for material in assembly.findall('material'):
            if WOLF_EYE_MATERIAL_MARKER in material.attrib['name']:
                old_wolf_eye_bsdf_names.add(get_param(material, 'bsdf'))
                fixup_wolf_eye_material(assembly, material)

        if len(old_wolf_eye_bsdf_names) > 0:
            old_bsdf_name = old_wolf_eye_bsdf_names.pop()
            old_bsdf = find_bsdf(assembly, old_bsdf_name)
            if old_bsdf.attrib['model'] == 'bsdf_mix':
                old_bsdf = find_bsdf(assembly, get_param(old_bsdf, 'bsdf0'))
            reflectance_name = get_param(old_bsdf, 'reflectance')
            add_wolf_eye_surface_shader(assembly, reflectance_name)

def tweak_wolf_shaders(root):
    print("  Tweaking wolf's fur shader:")
    set_material_fresnel(root, "wolf_fiber", "0.05")
    set_material_translucency(root, "wolf_fiber", "0.3")
    set_material_fresnel(root, "wolf_fur", "0.05")
    set_material_translucency(root, "wolf_fur", "0.3")

    print("  Tweaking wolf's skin shader:")
    set_material_fresnel(root, "wolf_skin", "0.05")

    replace_wolf_eye_shader(root)

    print("  Tweaking wolf's teeth shader:")
    set_material_sample_count(root, "wolf_teeth_", "16")


#--------------------------------------------------------------------------------------------------
# Tweak vegetation shaders.
#--------------------------------------------------------------------------------------------------

VEGETATION_MATERIAL_MARKERS = [ "big_branches_",
                                "ivy_leave",
                                "plant_",
                                "ground_leaves",
                                "Leaf ",
                                "leave_",
                                "leaves_",
                                "grass_",
                                "tree_compil_" ]

def tweak_vegetation_shaders(root):
    print("  Tweaking vegetation shaders:")

    for material_marker in VEGETATION_MATERIAL_MARKERS:
        set_material_fresnel(root, material_marker, "0.1")
        set_material_translucency(root, material_marker, "0.5")

    set_material_fresnel(root, "ground", "0.0")
    set_material_fresnel(root, "rock_pure", "0.0")

    set_material_glossiness(root, "ground", "1.0")
    set_material_glossiness(root, "grass_", "1.0")


#--------------------------------------------------------------------------------------------------
# Tweak the area lights.
#--------------------------------------------------------------------------------------------------

AREA_LIGHT_MATERIAL_MARKERS = [ "arealight_",
                                "hurricane_light_" ]

def tweak_area_lights(root):
    print("  Tweaking area lights:")

    for material in root.iter('material'):
        material_name = material.attrib['name']
        for material_marker in AREA_LIGHT_MATERIAL_MARKERS:
            if material_marker in material_name:
                print("    Setting \"alpha_mask\" to \"0\" on material \"{0}\"...".format(material_name))
                set_param(material, "alpha_map", "0")
                break


#--------------------------------------------------------------------------------------------------
# Tweak the settings of the frames.
#--------------------------------------------------------------------------------------------------

def tweak_frames(root):
    for frame in root.iter('frame'):
        print("  Tweaking frame \"{0}\"...".format(frame.attrib['name']))
        set_param(frame, "pixel_format", "half")
        set_param(frame, "tile_size", "128 128")
        set_param(frame, "filter", "gaussian")
        set_param(frame, "filter_size", "2.0")


#--------------------------------------------------------------------------------------------------
# Add a sky to the scene.
#--------------------------------------------------------------------------------------------------

def add_sky(root, horizontal_shift):
    print("  Adding sky...")

    scene = root.find("scene")

    texture = xml.Element('texture')
    texture.attrib['name'] = "sky_dusk_00"
    texture.attrib['model'] = "disk_texture_2d"
    set_param(texture, "color_space", "srgb")
    set_param(texture, "filename", TEXTURES_DIRECTORY + "/" + SKY_TEXTURE_FILENAME)
    scene.append(texture)

    texture_inst = xml.Element('texture_instance')
    texture_inst.attrib['name'] = "sky_dusk_00_inst"
    texture_inst.attrib['texture'] = "sky_dusk_00"
    set_param(texture_inst, "addressing_mode", "wrap")
    set_param(texture_inst, "filtering_mode", "bilinear")
    scene.append(texture_inst)

    environment_edf = xml.Element('environment_edf')
    environment_edf.attrib['name'] = "environment_edf"
    environment_edf.attrib['model'] = "latlong_map_environment_edf"
    set_param(environment_edf, "radiance", "sky_dusk_00_inst")
    set_param(environment_edf, "horizontal_shift", horizontal_shift)
    scene.append(environment_edf)

    environment_shader = xml.Element('environment_shader')
    environment_shader.attrib['name'] = "environment_shader"
    environment_shader.attrib['model'] = "edf_environment_shader"
    set_param(environment_shader, "environment_edf", "environment_edf")
    set_param(environment_shader, "alpha_value", "0.0")
    scene.append(environment_shader)

    environment = find_entity(root, "environment", "environment")
    set_param(environment, "environment_edf", "environment_edf")
    set_param(environment, "environment_shader", "environment_shader")


#--------------------------------------------------------------------------------------------------
# Assign light-emitting entities (EDFs, lights, etc.) to separate render layers.
#--------------------------------------------------------------------------------------------------

def assign_render_layers_to_nodes(nodes, render_layer_name=None):
    print("  Assigning render layers:")

    for node in nodes:
        name = node.attrib['name']
        if node.find("parameter[@name='render_layer']") is None:
            rlname = render_layer_name if render_layer_name is not None else name
            print("    Assigning entity \"{0}\" to render layer \"{1}\"...".format(name, rlname))
            set_param(node, 'render_layer', rlname)
        else:
            print("    Entity \"{0}\" is already assigned to a render layer.".format(name))

def assign_render_layers(root):
    assign_render_layers_to_nodes([ env_edf for env_edf in root.iter('environment_edf') ])
    assign_render_layers_to_nodes([ edf for edf in root.iter('edf') ])
    assign_render_layers_to_nodes([ light for light in root.iter('light') ])

    for inst in root.iter('object_instance'):
        instance_name = inst.attrib['name']

        if "scalp" in instance_name:
            assign_render_layers_to_nodes([ inst ], "scalp")

        if "_w_skin_ncl1_1_w_skin_ncl1_1Shape_instance_0" in instance_name:
            assign_render_layers_to_nodes([ inst ], "skin")

        if "hurricane_light" in instance_name:
            assign_render_layers_to_nodes([ inst ], "hurricane_light")


#--------------------------------------------------------------------------------------------------
# Applies a series of tweaks to a given appleseed project file.
#--------------------------------------------------------------------------------------------------

def process_file(filepath, args):
    if not os.path.exists(BACKUP_DIRECTORY):
        os.makedirs(BACKUP_DIRECTORY)

    filename = os.path.basename(filepath)
    backup_filepath = os.path.join(BACKUP_DIRECTORY, os.path.basename(filepath))

    if os.path.exists(backup_filepath):
        print("Restoring project file from {0}...".format(backup_filepath))
        shutil.copyfile(backup_filepath, filepath)
    else:
        print("Backuping project file to {0}...".format(backup_filepath))
        shutil.copyfile(filepath, backup_filepath)

    update_project_file(filepath, args.tool_path, ["--to-revision", "5"])

    print("Processing {0}:".format(filepath))

    tree = load_project_file(filepath)
    root = tree.getroot()

    replace_mesh_file_extensions(root)

    replace_hair_shader(root)
    tweak_hood_shaders(root)
    tweak_wolf_shaders(root)
    tweak_vegetation_shaders(root)
    tweak_area_lights(root)

    tweak_frames(root)

    if args.add_sky:
        add_sky(root, "50.0")
        #add_sky(root, "180.0")

    assign_render_layers(root)

    write_project_file(filepath, tree)

    update_project_file(filepath, args.tool_path)


#--------------------------------------------------------------------------------------------------
# Process all files in the current directory.
#--------------------------------------------------------------------------------------------------

def process_files_in_current_directory(args):
    for filepath in walk(".", False):
        if os.path.splitext(filepath)[1] == ".appleseed":
            process_file(filepath, args)


#--------------------------------------------------------------------------------------------------
# Entry point.
#--------------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="apply post-export transformations to one or multiple project files from Mescaline.")
    parser.add_argument("-t", "--tool-path", metavar="tool-path", required=True,
                        help="set the path to the updateprojectfile tool")
    parser.add_argument("--add-sky", action='store_true', help="add a sky to the scene")
    parser.add_argument("file", nargs='?', help="file to process (process all files in the current directory if omitted)")
    args = parser.parse_args()

    if args.file is None:
        process_files_in_current_directory(args)
    else:
        process_file(args.file, args)

    if args.add_sky:
        print("Copying {0} to shot directory...".format(SKY_TEXTURE_FILENAME))
        script_directory = os.path.dirname(os.path.realpath(__file__))
        shutil.copyfile(os.path.join(script_directory, SKY_TEXTURE_FILENAME),
                        os.path.join(TEXTURES_DIRECTORY, SKY_TEXTURE_FILENAME))

if __name__ == '__main__':
    main()
