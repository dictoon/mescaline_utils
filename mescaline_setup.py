
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

import maya.cmds as cmds
import re
import ms_commands

reload(ms_commands)

CUSTOM_ATTR_NAME = 'UDP3DSMAX'

def parse_custom_attributes(entity):
    print("Parsing custom attributes on {0}...".format(entity))

    attributes = dict()

    for param in cmds.getAttr(entity + '.' + CUSTOM_ATTR_NAME).split('&cr;&lf;'):
        if len(param) == 0:
            continue

        parts = param.split('=')

        if len(parts) != 2:
            print("Skipping custom attribute string: {0}".format(param))
            continue

        key = parts[0].strip()
        value = parts[1].strip()

        if key == 'as_light' or key == 'invisible':
            attributes[key] = (value == 'true')

        elif key == 'multiplier' or key == 'f_stop':
            attributes[key] = float(re.match(r'^[0-9\.]+$', value).group(0))

        elif key == 'color':
            values = re.findall(r'[0-9]+', value)
            attributes[key] = (float(values[0]) / 255, float(values[1]) / 255, float(values[2]) / 255)

        elif key == 'from_spot_light' or key == 'type':
            attributes[key] = value

    return attributes


def convert_area_light(area_light, attributes):
    # create and initialise material for object
    light_material = cmds.createNode('ms_appleseed_material', n=area_light + '_material')
    cmds.setAttr(light_material + '.enable_back_material', 0)
    cmds.setAttr(light_material + '.duplicate_front_attributes_on_back', 0)

    # create and initialise surface shader
    light_surface_shader = ms_commands.create_shading_node('constant_surface_shader', area_light + '_surface_shader')
    cmds.setAttr(light_surface_shader + '.alpha_multiplier', 0,0,0, type='double3')

    # create and initialise edf
    light_edf = ms_commands.create_shading_node('diffuse_edf', area_light + '_edf')
    cmds.setAttr(light_edf + '.exitance', attributes['color'][0], attributes['color'][1], attributes['color'][2], type='double3')
    cmds.setAttr(light_edf + '.exitance_multiplier', attributes['multiplier'], attributes['multiplier'], attributes['multiplier'], type='double3')

    # assign material and connect up nodes
    cmds.select(area_light)
    cmds.hyperShade(assign=light_material)
    cmds.connectAttr(light_edf + '.outColor', light_material + '.EDF_front_color', f=True)
    cmds.connectAttr(light_surface_shader + '.outColor', light_material + '.surface_shader_front_color', f=True)


def add_gobo(dummy_object, attributes):
    attributes = parse_custom_attributes(dummy_object)
    cmds.select(attributes['from_spot_light'])

    shape_node = cmds.listRelatives(dummy_object, shapes=True)[0]
    material = ms_commands.has_shader_connected(shape_node)
    file_node = ms_commands.get_connected_node(material)

    cmds.connectAttr(file_node + '.outColor', attributes['from_spot_light'] + '.color', f=True)
    cmds.select(dummy_object)
    cmds.delete()


def setup_dof(target, camera, f_stop):
    cmds.setAttr(camera + '.depthOfField', 1)

    # create a locator parented to the camera
    cam_matrix = cmds.xform(camera, q=True, m=True, ws=True)
    cam_locator = cmds.spaceLocator()
    cmds.xform(cam_locator, m=cam_matrix, ws=True)
    cmds.select(cam_locator, camera, r=True)
    cmds.parent()

    # create a locator parented to the target
    target_matrix = cmds.xform(target, q=True, m=True, ws=True)
    target_locator = cmds.spaceLocator()
    cmds.xform(target_locator, m=target_matrix, ws=True)
    cmds.select(target_locator, target, r=True)
    cmds.parent()

    distance_node = cmds.distanceDimension(cam_locator, target_locator)
    cmds.connectAttr(distance_node + '.distance', camera + '.focusDistance')

    f_stop_multiplier = 1.0
    while f_stop < 1.0:
        f_stop *= 2.0
        f_stop_multiplier /= 2.0

    cmds.setAttr(camera + '.fStop', f_stop)
    cmds.setAttr(camera + '.focusRegionScale', f_stop_multiplier)


def setup():
    for transform in cmds.ls(tr=True):
        if cmds.attributeQuery(CUSTOM_ATTR_NAME, n=transform, exists=True):
            attributes = parse_custom_attributes(transform)
            if 'type' in attributes.keys():
                type = attributes['type']
                if type == 'arealight':
                    convert_area_light(transform, attributes)
                elif type == 'gobo_dummy':
                    add_gobo(transform, attributes)
                elif type == 'camera':
                    setup_dof('dof_target', transform, attributes['f_stop'])

    # adjust light multiplier values
    for light in cmds.ls(lt=True):
        light_type = cmds.nodeType(light)
        if light_type == 'spotLight' or light_type == 'pointLight':
            intensity = cmds.getAttr(light + '.intensity') * 2.5
            cmds.setAttr(light + '.intensity', intensity)

    print("Done.")
