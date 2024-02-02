from roslibpy import Ros, Topic

from compas.geometry import KDTree, Pointcloud
from compas.geometry import Point, Frame, Quaternion
from compas.data import Data

class WsSphere(Data):
    def __init__(self, header=None, point=None, ri=None, poses=None):
        self.header = header
        self.point = point
        self.ri = ri
        self.poses = poses

    @property
    def data(self):
        _data = {
            "header" : self.header,
            "point" : self.point.data,
            "ri" : self.ri,
            'poses' : [frame.data for frame in self.poses]
        }
        return _data

    @data.setter
    def data(self, data):
        self.header = data['header']
        self.point = Point.from_data(data['point'])
        self.ri = data['ri']
        self.poses = [Frame.from_data(pose) for pose in data['poses']]

    @classmethod
    def from_data(cls, data):
        sph = cls()
        sph.data = data
        return sph

    @classmethod
    def from_message(cls, message):
        hdr = message["header"]
        pt = message["point"]
        point = Point(pt["x"], pt["y"], pt["z"])
        ri = message["ri"]
        poses = []
        for pose in message["poses"]:
            pos, ori = [pose["position"], pose["orientation"]]
            qt = Quaternion(ori["w"], ori["x"], ori["y"], ori["z"])
            pt = Point(pos["x"],pos["y"], pos["z"])
            poses.append(Frame.from_quaternion(qt, pt))
        return cls(hdr, point, ri, poses)


class ReuleauxReachability(Data):
    def __init__(self, header=None, spheres=[], resolution=None):
        self.header = header
        self.spheres = spheres
        self.resolution = resolution

    @property
    def kdtree(self):
        if self.spheres != []:
            return KDTree(self.spheres_data())

    def get_kdtree_transformed(self, transformation):
        pointcloud = Pointcloud(self.spheres_data())
        points = pointcloud.transformed(transformation).points
        return KDTree(points), points

    @property
    def data(self):
        _data = {
            "header" : self.header,
            "spheres" : [sphere.data for sphere in self.spheres],
            "resolution" : self.resolution
        }
        return _data

    @data.setter
    def data(self, data):
        self.header = data['header']
        self.spheres = [WsSphere.from_data(sphere) for sphere in data['spheres']]
        self.resolution = data['resolution']

    @classmethod
    def from_data(cls, data):
        rm = cls()
        rm.data = data
        return rm

    @classmethod
    def from_message(cls, message):
        hdr = message["header"]
        spheres = []
        for sphere in message["WsSpheres"]:
            spheres.append(WsSphere.from_message(sphere))
        res = message["resolution"]
        return cls(hdr, spheres, res)

    def update_from_message(self, message):
        self.header = message["header"]
        self.spheres = []
        for sphere in message["WsSpheres"]:
            self.spheres.append(WsSphere.from_message(sphere))
        self.resolution = message["resolution"]

    def spheres_data(self, yield_ri=False):
        if yield_ri:
            for sphere in self.spheres:
                yield sphere.point, sphere.ri
        else:
            for sphere in self.spheres:
                yield sphere.point


if __name__ == "__main__":
    client = Ros(host="10.152.106.220", port=9090)
    client.run()
    listener = Topic(client, '/reachability_map', 'map_creator/WorkSpace')
    reachabilitymap = ReachabilityMap()
    listener.subscribe(reachabilitymap.update_from_message)

    try:
        while True:
            pass
        else:
            print(len(listener.rm.spheres))
    except KeyboardInterrupt:
        client.terminate()
        print(len(listener.rm.spheres))
