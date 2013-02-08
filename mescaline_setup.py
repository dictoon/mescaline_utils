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

            if (key == 'as_light') or (key == 'invisible'):
                if attr == 'true':
                    attrs[key] = True
                else:
                    attrs[key] = False

            elif key =='multiplier':
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

    # cerate and initialise surface shader
    light_surface_shader = ms_commands.create_shading_node('constant_surface_shader', area_light + '_surface_shader')
    cmds.setAttr(light_surface_shader + '.alpha_multiplier', 0,0,0, type='double3')

    # create and initialise dbsdf
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


def connect_dof_target(target, camera):
    pass


def setup():

    area_lights = []
    gobo_dummys = []

    for transform in cmds.ls(tr=True):
        if cmds.attributeQuery(custom_attr, n=transform, exists=True):
            attribs = parse_custom_attribs(transform)
            if 'type' in attribs.keys():
                if attribs['type'] == 'arealight':
                    area_lights.append([transform, attribs])
                elif attribs['type'] == 'gobo_dummy':
                    gobo_dummys.append([transform, attribs])

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

