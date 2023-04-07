from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import os
import math
import compas

from copy import deepcopy
from compas.geometry import Frame, Vector
from compas.geometry import Transformation, Translation, Rotation
from compas.geometry import distance_point_point, distance_line_line
from compas.datastructures import Network, mesh_offset
from compas.artists import Artist
from compas.colors import Color

import rhinoscriptsyntax as rs
import Rhino.Geometry as rg
import ghpythonlib.components as gh

from .element import Element

from .utilities import FromToData
from .utilities import FromToJson
from .utilities import element_to_INCON
from .utilities import tag_to_INCON

__all__ = ['Assembly']


class Assembly(FromToData, FromToJson):
    """A data structure for discrete element assemblies.

    An assembly is essentially a network of assembly elements.
    Each element is represented by a node of the network.
    Each interface or connection between elements is represented by an edge of the network.

    Attributes
    ----------
    network : :class:`compas.Network`, optional
    elements : list of :class:`Element`, optional
        A list of assembly elements.
    attributes : dict, optional
        User-defined attributes of the assembly.
        Built-in attributes are:
        * name (str) : ``'Assembly'``
    default_element_attribute : dict, optional
        User-defined default attributes of the elements of the assembly.
        The built-in attributes are:
        * is_planned (bool) : ``False``
        * is_placed (bool) : ``False``
    default_connection_attributes : dict, optional
        User-defined default attributes of the connections of the assembly.

    Examples
    --------
    >>> assembly = Assembly()
    >>> for i in range(2):
    >>>     element = Element.from_box(Box(Frame.worldXY(), 10, 5, 2))
    >>>     assembly.add_element(element)
    """

    def __init__(self,
                 elements=None,
                 attributes=None,
                 default_element_attributes=None,
                 default_connection_attributes=None):

        self.network = Network()
        self.network.attributes.update({'name': 'Assembly'})

        if attributes is not None:
            self.network.attributes.update(attributes)

        self.network.default_node_attributes.update({
            'is_planned': False,
            'is_built': False,
            'is_support': False,
            'is_held_by_robot': False,
            'has_open_connector':False,
            'color': None

        })

        if default_element_attributes is not None:
            self.network.default_node_attributes.update(default_element_attributes)

        if default_connection_attributes is not None:
            self.network.default_edge_attributes.update(default_connection_attributes)

        if elements:
            for element in elements:
                self.add_element(element)

    @property
    def name(self):
        """str : The name of the assembly."""
        return self.network.attributes.get('name', None)

    @name.setter
    def name(self, value):
        self.network.attributes['name'] = value

    def number_of_elements(self):
        """Compute the number of elements of the assembly.

        Returns
        -------
        int
            The number of elements.

        """
        return self.network.number_of_nodes()

    def number_of_connections(self):
        """Compute the number of connections of the assembly.

        Returns
        -------
        int
            the number of connections.

        """
        return self.network.number_of_edges()

    @property
    def data(self):
        """Return a data dictionary of the assembly.
        """
        # Network data does not recursively serialize to data...
        d = self.network.data

        # so we need to trigger that for elements stored in nodes
        node = {}
        for vkey, vdata in d['node'].items():
            node[vkey] = {key: vdata[key] for key in vdata.keys() if key != 'element'}
            node[vkey]['element'] = vdata['element'].to_data()

            if 'frame_est' in vdata:
                if node[vkey]['frame_est']:
                    node[vkey]['frame_est'] = node[vkey]['frame_est'].to_data()

        d['node'] = node

        return d

    @data.setter
    def data(self, data):
        # Deserialize elements from node dictionary
        for _vkey, vdata in data['node'].items():
            vdata['element'] = Element.from_data(vdata['element'])

            if 'frame_est' in vdata:
                if vdata['frame_est']:
                    vdata['frame_est'] = Frame.from_data(vdata['frame_est']) #node[vkey]['frame_est'].to_data()

        self.network = Network.from_data(data)

    def clear(self):
        """Clear all the assembly data."""
        self.network.clear()

    def add_element(self, element, key=None, attr_dict={}, **kwattr):
        """Add an element to the assembly.

        Parameters
        ----------
        element : Element
            The element to add.
        attr_dict : dict, optional
            A dictionary of element attributes. Default is ``None``.

        Returns
        -------
        hashable
            The identifier of the element.
        """
        attr_dict.update(kwattr)
        x, y, z = element.frame.point
        key = self.network.add_node(key=key, attr_dict=attr_dict,
                                    x=x, y=y, z=z, element=element)
        return key


    def add_rf_unit_element(self, current_key, flip='AA', angle=0, shift_value=0, placed_by='human', on_ground=False, unit_index=0, frame_id=None, frame_est=None):
        """Add an element to the assembly.
        """
        radius = self.globals['rod_radius']
        length = self.globals['rod_length']
        rf_unit_radius = self.globals['rf_unit_radius']
        rf_unit_offset = self.globals['rf_unit_offset']

        N = self.network.number_of_nodes()

        current_elem = self.network.node[current_key]['element']

        # Find the open connector of the current element
        if current_elem.connector_1_state:
            current_connector_frame = current_elem.connector_frame_1
            c = -1
        else:
            current_connector_frame = current_elem.connector_frame_2
            c = 1

        if flip == 'AA':
            a = b = 0
        if flip == 'AB':
            a = 0
            b = 1*c
        if flip == 'BA':
            a = 1*c
            b = 0
        if flip == 'BB':
            a = b = 1*c

        new_elem = current_elem.copy()

        if placed_by == 'robot':
            R1 = Rotation.from_axis_and_angle(current_connector_frame.zaxis, math.radians(120), current_connector_frame.point)
            T1 = Translation.from_vector(-new_elem.frame.xaxis*a*((length-rf_unit_radius+rf_unit_offset)/2.))
        else:
            R1 = Rotation.from_axis_and_angle(current_connector_frame.zaxis, math.radians(240), current_connector_frame.point)
            T1 = Translation.from_vector(-new_elem.frame.xaxis*b*((length-rf_unit_radius+rf_unit_offset)/2.))

        new_elem.transform(R1*T1)

        # Define a desired rotation around the parent element
        T_point = Translation.from_vector(current_elem.frame.xaxis)
        new_point = current_elem.frame.point.transformed(T_point)
        R2 = Rotation.from_axis_and_angle(current_elem.frame.xaxis, math.radians(angle),new_point)

        # Define a desired shift value along the parent element
        T3 = Translation.from_vector(current_elem.frame.xaxis*shift_value)

        # Transform the new element
        new_elem.transform(R2*T3)

        self.add_element(new_elem, placed_by=placed_by, on_ground=on_ground, frame_id=frame_id, frame_est=frame_est, is_built=True)

        # Add adges
        if unit_index == 0:
            self.network.add_edge(current_key, N, edge_to='neighbour')
        else:
            self.network.add_edge(N-1, N, edge_to='parent')
            self.network.add_edge(current_key, N, edge_to='parent')

        self.update_connectors_states(current_key, flip, new_elem, unit_index)

        if unit_index == 1:
            if current_elem.connector_1_state:
                current_elem.connector_1_state = False
            else:
                current_elem.connector_2_state = False

        return new_elem

    def add_connection(self, u, v, attr_dict=None, **kwattr):
        """Add a connection between two elements and specify its attributes.

        Parameters
        ----------
        u : hashable
            The identifier of the first element of the connection.
        v : hashable
            The identifier of the second element of the connection.
        attr_dict : dict, optional
            A dictionary of connection attributes.
        kwattr
            Other connection attributes as additional keyword arguments.

        Returns
        -------
        tuple
            The identifiers of the elements.
        """
        return self.network.add_edge(u, v, attr_dict, **kwattr)

    def add_joint(self, edge, joint):
        """
        """
        u, v = edge
        return self.add_edge(u, v, joint=joint)

    def transform(self, transformation):
        """Transforms this assembly.

        Parameters
        ----------
        transformation : :class:`Transformation`

        Returns
        -------
        None
        """
        for _k, element in self.elements(data=False):
            element.transform(transformation)

    def transformed(self, transformation):
        """Returns a transformed copy of this assembly.

        Parameters
        ----------
        transformation : :class:`Transformation`

        Returns
        -------
        Assembly
        """
        assembly = self.copy()
        assembly.transform(transformation)
        assembly.network.transform(transformation)
        return assembly

    def copy(self):
        """Returns a copy of this assembly.
        """
        cls = type(self)
        return cls.from_data(deepcopy(self.data))

    def element(self, key, data=False):
        """Get an element by its key."""
        if data:
            return self.network.node[key]['element'], self.network.node[key]
        else:
            return self.network.node[key]['element']

    def elements(self, data=False):
        """Iterate over the elements of the assembly.

        Parameters
        ----------
        data : bool, optional
            If ``True``, yield both the identifier and the attributes.

        Yields
        ------
        2-tuple
            The next element as a (key, element) tuple, if ``data`` is ``False``.
        3-tuple
            The next element as a (key, element, attr) tuple, if ``data`` is ``True``.

        """
        if data:
            for vkey, vattr in self.network.nodes(True):
                yield vkey, vattr['element'], vattr
        else:
            for vkey in self.network.nodes(data):
                yield vkey, self.network.node[vkey]['element']

    def connections(self, data=False):
        """Iterate over the connections of the network.

        Parameters
        ----------
        data : bool, optional
            If ``True``, yield both the identifier and the attributes.

        Yields
        ------
        2-tuple
            The next connection identifier (u, v), if ``data`` is ``False``.
        3-tuple
            The next connection as a (u, v, attr) tuple, if ``data`` is ``True``.

        """
        return self.network.edges(data)


    def collision_check(self, option_elems, tolerance):
        """Check for collisions with previously built elements.
        """

        collision = False
        results = []

        for key, elem in self.elements():
            a_line = Artist(elem.line).draw()
            for option_elem in option_elems:
                b_line = Artist(option_elem.line).draw()
                #results.append(True if distance_line_line(elem.line, option_elem.line, tol = 0.001) < assembly.globals['rod_radius']*2. + tolerance else False)
                point_a, point_b, distance = gh.CurveProximity(a_line, b_line)
                results.append(True if distance < (self.globals['rod_radius']*2. + tolerance) else False)
            collision = True if True in results else False
        return collision

    def static_equilibrium_check(self, support, option_elems, allow_temp_support=True):
        """Check if the structure is in equilibrium.
        """

        supports = []

        if allow_temp_support == True:
            s_glob = True

        planes = [Artist(element.frame).draw() for key, element in self.elements()]
        [plane.Translate(plane.ZAxis*-0.4) for plane in planes]
        elements_breps = [rg.Cylinder(rg.Circle(plane, 0.01), 0.8) for plane in planes]

        option_plane = Artist(option_elems[0].frame).draw()
        option_plane.Translate(option_plane.ZAxis*-0.4)
        elements_breps.append(rg.Cylinder(rg.Circle(option_plane, 0.01), 0.8)) # built elements + option robot

        elements_breps = [geo.ToBrep(True, True) for geo in elements_breps]
        e = elements_breps

        sa = rs.BoundingBox(support) #support area in which the resultant shall lie on
        sa = rs.AddSrfPt(sa[:4])
        sa = rs.ExtrudeSurface(rs.MoveObject(sa, (0,0,-0.1)), rs.AddLine((0,0,-0.1), (0,0,0.1)))

        supports.append(support)
        supports += e

        e = supports

        vol = [rs.SurfaceVolume(e[x])[0] for x in range(len(e))] #volume Vectors; Material weight is considered as constant
        cen = [rs.SurfaceVolumeCentroid(e[x])[0] for x in range(len(e))]
        cen = [(cen[x][0], cen[x][1], 0) for x in range(len(cen))] #planar Center-nodes

        res_pos_x = 0
        res_pos_y = 0

        static_equilibrium = False

        for i in range(len(e)):
            m_x = cen[i][0] * vol [i]
            m_y = cen[i][1] * vol [i]

            res_pos_x += m_x
            res_pos_y += m_y

            res_pos_x_loc = res_pos_x / sum(vol[:(i+1)]) #moment in x-dir
            res_pos_y_loc = res_pos_y / sum(vol[:(i+1)]) #moment in y-dir

            res_loc = rs.AddLine((res_pos_x_loc, res_pos_y_loc, 0), (res_pos_x_loc, res_pos_y_loc, sum(vol[:(i+1)]))) #Resultant
            se_loc = rs.IsPointInSurface(sa, (res_pos_x_loc, res_pos_y_loc, 0))

            if s_glob == True and allow_temp_support == False:
                if i > s_int+1: allow_temp_support = True

            if se_loc != True: # Structure is in Equilibrium
                static_equilibrium = True

            if se_loc != False and allow_temp_support == False: # Structure is NOT in Equilibrium
                static_equilibrium = False

            if se_loc != False and allow_temp_support == True: # Structure is only in Equilibrium if Robot holds the last Element
                static_equilibrium = True
                allow_temp_support = False
                s_int = i

            res = res_loc

        if res == False:
            res = None

        return static_equilibrium, res


    def close_rf_unit(self, current_key, flip, angle, shift_value, on_ground=False, added_frame_id=None, frame_est=None):
        """Add a module to the assembly.
        """

        keys_robot = []

        for i in range(2):
            if i == 0:
                placed_by = 'robot'
                frame_id = None
                my_new_elem = self.add_rf_unit_element(current_key, flip=flip, angle=angle, shift_value=shift_value, placed_by=placed_by, on_ground=False, unit_index=i, frame_id=frame_id, frame_est=None)
                keys_robot += list(self.network.nodes_where({'element': my_new_elem}))
            else:
                placed_by = 'human'
                frame_id = added_frame_id
                my_new_elem = self.add_rf_unit_element(current_key, flip=flip, angle=angle, shift_value=shift_value, placed_by=placed_by, on_ground=False, unit_index=i, frame_id=frame_id, frame_est=frame_est)
                keys_human = list((self.network.nodes_where({'element': my_new_elem})))

        keys_dict = {'keys_human': keys_human, 'keys_robot':keys_robot}

        return keys_dict


    def parent_key(self, point, within_dist):
        """Return the parent key of a tracked object.
        """
        parent_key = None

        for key, element in self.elements():
            connectors = element.connectors(state='open')
            for connector in connectors:
                dist = distance_point_point(point, connector.point)
                if dist < within_dist:
                    parent_key = key

        return parent_key


    def update_connectors_states(self, current_key, flip, my_new_elem, unit_index):

        key_index = self.network.key_index()
        current_elem = self.network.node[current_key]['element']
        keys = [key_index[key] for key in self.network.nodes()]
        previous_elem = self.network.node[keys[-2]]['element']

        if unit_index == 1:
            if current_elem.connector_2_state:
                if flip == 'AA':
                    previous_elem.connector_2_state = False
                    my_new_elem.connector_2_state = False
                if flip == 'AB':
                    previous_elem.connector_2_state = False
                    my_new_elem.connector_1_state = False
                if flip == 'BA':
                    previous_elem.connector_1_state = False
                    my_new_elem.connector_2_state = False
                if flip == 'BB':
                    previous_elem.connector_1_state = False
                    my_new_elem.connector_1_state = False
            if current_elem.connector_1_state:
                if flip == 'AA':
                    previous_elem.connector_1_state = False
                    my_new_elem.connector_1_state = False
                if flip == 'AB':
                    previous_elem.connector_1_state = False
                    my_new_elem.connector_2_state = False
                if flip == 'BA':
                    previous_elem.connector_2_state = False
                    my_new_elem.connector_1_state = False
                if flip == 'BB':
                    previous_elem.connector_2_state = False
                    my_new_elem.connector_2_state = False


    def keys_within_radius(self, current_key):

        for key, element in self.elements(data=True):
            pass

    def keys_within_radius_xy(self, current_key):
        pass

    def keys_within_radius_domain(self, current_key):
        pass

    def range_filter(self, base_frame):
        """Disable connectors outside of a given range, e.g. robot reach.
        """
        ur_range_max = 1.3
        ur_range_min = 0.75

        for key, element in self.elements():
            if element.connector_1_state == True:
                distance = distance_point_point(element.connector_frame_1.point, base_frame.point)
                if not ur_range_min <= distance <= ur_range_max:
                    element.connector_1_state = False
            elif element.connector_2_state == True:
                distance = distance_point_point(element.connector_frame_2.point, base_frame.point)
                if not ur_range_min <= distance <= ur_range_max:
                    element.connector_2_state = False
            else:
                pass

    def distance_to_input_geo(self, key, angle, input_geo):

        conn_frame = self.element(key).connectors(state='open')[0]
        elem_frame = self.element(key).frame

        R = Rotation.from_axis_and_angle(elem_frame.xaxis, math.radians(angle), elem_frame.point)

        conn_frame_copy = conn_frame.transformed(R)
        conn_plane = Artist(conn_frame_copy).draw()

        closest_point = input_geo.ClosestPoint(conn_plane.Origin)
        distance = closest_point.DistanceTo(conn_plane.Origin)

        vector = rg.Vector3d(closest_point) - rg.Vector3d(conn_plane.Origin)

        return distance, vector

    def orientation_to_input_geo(self, key, angle, input_geo):

        conn_frame = self.element(key).connectors(state='open')[0]
        elem_frame = self.element(key).frame

        R = Rotation.from_axis_and_angle(elem_frame.xaxis, math.radians(angle), elem_frame.point)

        conn_frame_copy = conn_frame.transformed(R)
        conn_plane = Artist(conn_frame_copy).draw()

        closest_point = input_geo.ClosestPoint(conn_plane.Origin)

        vector = rg.Vector3d(closest_point) - rg.Vector3d(conn_plane.Origin)

        #angle = 180 - math.degrees(conn_frame_copy.zaxis.angle(vector))
        cross_product = conn_frame_copy.zaxis.cross(vector)

        return cross_product.length**-1, vector

    def all_options_elements(self, flip, angle):
        """Returns a list of elements.
        """
        keys = [key for key, element in self.elements()]
        return [self.element(key).current_option_elements(flip, angle) for key in keys]


    def all_options_vectors(self, len):
        """Returns a list of vectors.
        """
        keys = [key for key, element in self.elements()]
        return [self.element(key).current_option_vectors(len) for key in keys]

    def all_options_viz(self, rf_unit_radius):
        """Returns a list of frames.
        """
        keys = [key for key, element in self.elements()]
        return [self.element(key).current_option_viz(rf_unit_radius) for key in keys]


    def connectors(self, state='all'):
        """ Iterate over the connectors of the assembly elements.

        Parameters
        ----------
        state : string
            A string indentifying the connectors' state.

            If 'all', yeild all connectors.
            If 'open' : yeild all open connectors.
            If 'closed' : yeild all closed connectors.

        Yields
        ------
        2-tuple
            The connectors as a (key, frame) tuple.

        """
        for key, element in self.elements():
            yield key, element.connectors(state)

        # keys = [key for key, element in self.elements()]
        # return [(key, self.element(key).connectors(state)) for key in keys]

    def connectors(self, state='all'):
        """ Iterate over the connectors of the assembly elements.

        Parameters
        ----------
        state : string
            A string indentifying the connectors' state.

            If 'all', yeild all connectors_ranges.
            If 'open' : yeild all open connectors_ranges.
            If 'closed' : yeild all closed connectors_ranges.

        Yields
        ------
        2-tuple
            The connectors as a (key, cone) tuple.

        """
        for key, element in self.elements():
            yield key, element.connectors_ranges(state)

        # keys = [key for key, element in self.elements()]
        # return [(key, self.element(key).connectors(state)) for key in keys]


    def export_building_plan(self):
        """
        exports the building plan by using the following protocol:

        the first lines are the description of the global markers (fixed in the world frame):
        type [string], element pose [6]
        = "GM", x, y, z, qw, qx, qy, qz

        the next lines contain the wall information:
        type [string], element pose [6], string_message [string]
        = type, x, y, z, qw, qx, qy, qz, string_message
        """

        print("exporting")
        building_plan = []

        for key, element, data in self.elements(data=True):
            line = []

            t = element._type
            line.append(t) #type
            line += element.get_pose_quaternion() #element pose
            string_message = "This is the element with the key index %i" %key
            line.append(string_message)
            building_plan.append(line)

        print(building_plan)
        exporter = Exporter()
        exporter.delete_file()
        exporter.export_building_plan(building_plan)

    def export_to_json_for_xr(self, path, is_built=False):

        self.network.update_default_node_attributes({"is_built":False,"idx_v":None,"custom_attr_1":None,"custom_attr_2":None,"custom_attr_3":None})

        for key, element in self.elements():
            idx_v = self.network.node_attribute(key, "course")
            self.network.node_attribute(key, "idx_v", idx_v)
            self.network.node_attribute(key, "is_built", is_built)

        self.to_json(path)

    def export_to_json_incon(self, path, qr_code, starting_geometry=True, is_built=True, pretty=True):
        buildingplan = {"id":"iaac_plan",'name':"iaac_plan", "description":"iaac_plan", "building_steps":[]}
        building_steps = []
        len = 0

        if starting_geometry:
            element_to_INCON("starting element", len, None, building_steps, True, "starting_material.obj")
            len += 1

        for key, element, data in self.elements(data=True):
            element_to_INCON("dynamic_cylinder", key, element, building_steps, True, "cylinder_for_iaac_workshop.obj")

        placeholder = {"type":"object",'object_type':"cylinder_for_iaac_workshop_1m.obj", "id": "dynamic_cylinder", "is_tag": False, "is_already_built": False, "color_rgb": [1.0, 0.0, 0.0],"instances": 200,"build_instructions" : []}
        building_steps.append(placeholder)

        for key, tag in enumerate(qr_code):
            tag_to_INCON(key, tag, building_steps)

        buildingplan['building_steps'] = building_steps
        compas.json_dump(buildingplan, path, pretty)