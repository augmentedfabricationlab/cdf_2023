from compas.datastructures import Network
from compas.geometry import Frame, Vector, Transformation
from compas.geometry import KDTree
from statistics import mean

class BaseMap(object):
    def __init__(self):
        self.base_map = Network(name="base_map")
        self.base_map.default_node_attributes = {
            'frame': Frame.worldXY(),
            'point': [0, 0, 0],
            'xaxis': [1, 0, 0],
            'yaxis': [0, 1, 0],
            'valid_position': True,
            'mean_reuleax_index':-1,
            'mean_reach_index':-1,
            'reuleaux_data': None
        }

    @property
    def kdtree(self):
        objects = []
        for key, data in self.base_map.nodes(data=True):
            objects.append((data['frame'].point, key))
        kdtree = KDTree()
        kdtree.build(objects)
        return kdtree

    def add_pose(self, pose, **kwargs):
        return self.base_map.add_node(frame=pose, point=pose.point, xaxis=pose.xaxis,
                               yaxis=pose.yaxis, **kwargs)

    def set_poses(self, points, attractor_point=[0,0,0]):
        self.base_map.clear()
        for i, pt in enumerate(points):
            vec = Vector.from_start_end(pt, attractor_point).unitized()
            self.base_map.add_node(key=i, x=pt.x, y=pt.y, z=pt.z,
                                   vx=vec.x, vy=vec.y, vz=vec.z)
    
    def get_reuleaux_index_by_base_pose(self, pose, reuleaux, goal_pointcloud, collision_pointcloud=None):
        from time import time
        t0 = time()
        if reuleaux.resolution == 0:
            raise ValueError("ReuleauxReachability instance has resolution == 0.0")
        closest_map_point, id, distance = self.kdtree.nearest_neighbor(pose.point)
        # print("t1: ", time()-t0)
        T = Transformation.from_change_of_basis(pose, Frame.worldXY())
        kdtree, reuleaux_points = reuleaux.get_kdtree_transformed(T)
        # print("t2: ", time()-t0)
        reuleaux_data = {
            'goal_points': goal_pointcloud.points,
            'collision_points': None,
            'reuleaux_points': reuleaux_points,
            'goal_reuleaux_index': [],
            'collision_reuleaux_index': [],
            'reachable': []
        }
        goal_data = [kdtree.nearest_neighbors(pt, 2, distance_sort=True) for pt in goal_pointcloud.points]

        for d, pt in zip(goal_data, goal_pointcloud.points): 
            eval_data = {
                'goal_reuleaux_index': 0,
                'reachable': False}
            if d[0][2]<(reuleaux.resolution*1.415) and d[1][2]<(reuleaux.resolution*1.415):
                point_ri = reuleaux.spheres[d[0][1]].ri
                eval_data.update({
                    'goal_reuleaux_index': point_ri,
                    'reachable': True})
            for key, value in eval_data.items():
                reuleaux_data[key].append(value)

        if collision_pointcloud is not None:
            reuleaux_data['collision_points'] = collision_pointcloud.points
            collision_data = [kdtree.nearest_neighbors(pt, 2, distance_sort=True) for pt in collision_pointcloud.points]
            for d, pt in zip(collision_data, collision_pointcloud.points): 
                eval_data = {'collision_reuleaux_index': 0}
                if d[0][2]<(reuleaux.resolution*1.415) and d[1][2]<(reuleaux.resolution*1.415):
                    point_ri = reuleaux.spheres[d[0][1]].ri
                    eval_data.update({'collision_reuleaux_index': point_ri})
                for key, value in eval_data.items():
                    reuleaux_data[key].append(value)

        goal_ri_mean = mean(reuleaux_data['goal_reuleaux_index'])
        if collision_pointcloud is not None:
            collision_ri_mean = mean(reuleaux_data['collision_reuleaux_index'])
            ri_mean = mean([goal_ri_mean]*len(reuleaux_data['goal_reuleaux_index'])+[collision_ri_mean*-1]*len(reuleaux_data['collision_reuleaux_index']))
        else:
            ri_mean = goal_ri_mean

        if distance > 0.01:
            id = self.add_pose(pose, mean_reuleaux_index=ri_mean, reuleaux_data=reuleaux_data)
        else:
            self.base_map.node_attribute(id, 'mean_reuleaux_index', ri_mean)
            self.base_map.node_attribute(id, 'reuleaux_data', reuleaux_data)
        # print("t5: ", time()-t0)
        return id, reuleaux_data

    def populate_surface(self, surface, number_of_points):
        # points = populate(surface, number of points)
        # for i, pt in enumerate(points):
        #   node = {
        #       'x':pt.x, 'y':pt.y, 'z':pt.z,
        #   }
        #   self.base_map.add_node(key=i, attr_dict=node)
        pass

    def populate_around_point(self, surface, point, number_of_points, radius):
        # sphere(point, radius)
        # cut_surface with sphere
        # populate area with new points
        # for i, pt in enumerate(points):
        #   node = {
        #       'x':pt.x, 'y':pt.y, 'z':pt.z,
        #   }
        #   self.base_map.add_node(key=i, attr_dict=node)
        pass


    



