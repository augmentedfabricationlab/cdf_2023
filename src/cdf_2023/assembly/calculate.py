import math 
import random

"""radius = 0.01
length = 0.8
rf_unit_offset = 0.05
joint_dist = 0.015
unit_size = 0.25

angle_rf_unit = math.asin((2 * radius + joint_dist)/unit_size)
print ("angle1", angle_rf_unit)
angle_rf_unit = math.atan(math.sqrt(3)*(joint_dist/2+radius)/unit_size)
print ("angle2", angle_rf_unit)

rad1 = unit_size/math.sqrt(3)*math.cos(angle_rf_unit)
print ("rad1 1", rad1)
rad1 = rad1*math.sqrt(3)/2
#rad1 = unit_size*math.cos(angle_rf_unit)
print ("rad1 2", rad1)
#rad1= unit_size
print ("rad1 3", rad1)
y1 = rad1/2.
print ("y1", y1)
x1 = rad1*math.sqrt(3)/2.
print ("x1", x1)

#print(0.5/math.cos(angle_rf_unit))
#print(x1*x1 + y1*y1)
#print(rad1*rad1)

r = 0.552/2
s = 1.028
angle_rf_unit = math.atan(math.sqrt(3)*(r)/s)
print ("angle2", angle_rf_unit)
"""
"""selected_shift_value = 0
set_random_shift = True
random_shift = selected_shift_value if not set_random_shift else round(random.uniform(0, 0.12),2)
print(random_shift)

selected_unit_size = 0.15
random_params = ['unit_size']
random_unit_size = selected_unit_size if not "unit_size" in random_params else round(random.uniform(0.8, 0.20),2)
print(random_unit_size)


resultant.append(rg.Circle(resultant_line.PointAt(0),lever_arm))"""
bkey  = 3
support_keys = [0,2,3,4]

if bkey in support_keys:
    print ('ja')
else:
    print('nein')
