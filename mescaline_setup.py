
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

custom_attr = 'UDP3DSMAX'

def parse_custom_attribs(attrib):

    custom_attr_string = cmds.getAttr(attrib + '.' + custom_attr)
    attrs = dict()

    for pair in custom_attr_string.split('&cr;&lf;'):
        if pair:
            split_pair = pair.split(' = ')
            key = split_pair[0]
            attr = split_pair[1]

            if key == 'as_light' or key == 'invisible':
                attrs[key] = (attr == 'true')

            elif key == 'multiplier' or key == 'f_stop':
                attrs[key] = float(re.match(r'^[0-9\.]+$', attr).group(0))

            elif key == 'color':
                attr_string_list = re.findall(r'[0-9]+', attr)
                attrs[key] = (float(attr_string_list[0]) / 255, float(attr_string_list[1]) / 255, float(attr_string_list[2]) / 255)

            elif key == 'from_spot_light' or key == 'type':
                attrs[key] = attr

    return attrs


def convert_area_light(area_light, attrs):

    # create and initialise material for object
    light_material = cmds.createNode('ms_appleseed_material', n=area_light + '_material')
    cmds.setAttr(light_material + '.enable_back_material', 0)
    cmds.setAttr(light_material + '.duplicate_front_attributes_on_back', 0)

    # create and initialise surface shader
    light_surface_shader = ms_commands.create_shading_node('constant_surface_shader', area_light + '_surface_shader')
    cmds.setAttr(light_surface_shader + '.alpha_multiplier', 0,0,0, type='double3')

    # create and initialise edf
    light_edf = ms_commands.create_shading_node('diffuse_edf', area_light + '_edf')
    cmds.setAttr(light_edf + '.exitance', attrs['color'][0], attrs['color'][1], attrs['color'][2], type='double3')
    cmds.setAttr(light_edf + '.exitance_multiplier', attrs['multiplier'], attrs['multiplier'], attrs['multiplier'], type='double3')

    # assign material and connect up nodes
    cmds.select(area_light)
    cmds.hyperShade(assign=light_material)
    cmds.connectAttr(light_edf + '.outColor', light_material + '.EDF_front_color', f=True)
    cmds.connectAttr(light_surface_shader + '.outColor', light_material + '.surface_shader_front_color', f=True)


def add_gobo(dummy_object, attrs):

    attrs = parse_custom_attribs(dummy_object)
    cmds.select(attrs['from_spot_light'])

    shape_node = cmds.listRelatives(dummy_object, shapes=True)[0]
    material = ms_commands.has_shader_connected(shape_node)
    file_node = ms_commands.get_connected_node(material)

    cmds.connectAttr(file_node + '.outColor', attrs['from_spot_light'] + '.color', f=True)
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

    area_lights = []
    gobo_dummys = []
    cameras = []

    for transform in cmds.ls(tr=True):
        if cmds.attributeQuery(custom_attr, n=transform, exists=True):
            attribs = parse_custom_attribs(transform)
            if 'type' in attribs.keys():
                type = attribs['type']
                if type == 'arealight':
                    area_lights.append([transform, attribs])
                elif type == 'gobo_dummy':
                    gobo_dummys.append([transform, attribs])
                elif type == 'camera':
                    cameras.append([transform, attribs])

    for arealight in area_lights:
        convert_area_light(arealight[0], arealight[1])

    for gobo_dummy in gobo_dummys:
        add_gobo(gobo_dummy[0], gobo_dummy[1])

    # adjust light multiplier values
    for light in cmds.ls(lt=True):
        light_type = cmds.nodeType(light)
        if light_type == 'spotLight' or light_type == 'pointLight':
            intensity = cmds.getAttr(light + '.intensity') * 2.5
            cmds.setAttr(light + '.intensity', intensity)

    for camera in cameras:
        setup_dof('dof_target', camera[0], camera[1]['f_stop'])
