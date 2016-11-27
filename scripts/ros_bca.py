#!/usr/bin/python

# import
import os
import cv2
import pprint
import datetime
import rospy
import sys
import numpy as np
import pymongo
from std_msgs.msg import Bool
from biobot_ros_msgs.msg import BCAMsg
from gridfs import GridFS
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image
from bca_cv import BC_finder

class Camera2D():
    """This class is responsible for interacting with an HD Camera."""

	def __init__(self):
        # ROS init
        self.node_name = self.__class__.__name__
        rospy.init_node(self.node_name, anonymous=True)
        self.rate = rospy.Rate(10)  # 10 Hz

        # ROS subscriptions
        self.subscriber = rospy.Subscriber('image_raw', Image, self.callback_2d_capture)
		self.subscriber = rospy.Subscriber('BC_Analysis',BCAMsg, self.callback_bca)

		# ROS publisher
		self.bca_done = rospy.Publisher('BCA_Done', Bool, queue_size=10)	

        # Variables initialization 
		self.bridge = CvBridge()
		self.cv_image = np.zeros((1944,2592,3), np.uint8)
        
	    self.perimeter_min = float()
        self.perimeter_max = float()
	    self.excentricity_min = float()
        self.excentricity_max = float()
	    self.area_min = float()
        self.area_max = float()
	    self.number_of_colony_d = int()
	    self.picking = bool()
        self.protocol = ""
        self.step = int()

    def callback_2d_capture(self, data):
        """
        Callback method for 2d capture, it subscribed to UVC_Camera raw_image topics
        It refresh the image saved in self.cv_image at every callback
        """
        try:
            self.cv_image = self.bridge.imgmsg_to_cv2(data, 'bgr8')
        except CvBridgeError as e:
            print(e)
            return


    def callback_bca(self,data):
        """
        Callback method for BCA analysis, it reads BCA_Analysis ROS topics which is
        a BCAMsg.msg topic containing bacterial colonies selection specification.
        It called colony_selection and saved raw image, analysis image, picking 
        image and bacterial colonies found parameters to DB.
        """

	    try:
		    # Colony selection parameters
		    self.perimeter_min = data.perimeter_min
            self.perimeter_max = data.perimeter_max
		    self.excentricity_min = data.excentricity_min
            self.excentricity_max = data.excentricity_max
		    self.area_min = data.area_min
            self.area_max = data.area_max
		    self.number_of_colony_d = data.number_of_colony
		    self.picking = data.picking
            self.protocol = data.protocol
            self.step = data.step

        except (AssertionError, AttributeError) as e:
            print("Error : {}".format(e))
            return None

        # Sets operation value in function of self.picking
        if self.picking:
            operation = "picking"

        elif:
            operation = "analysis"

        # Saves raw image to .jpg and to DB
        imwrite("raw_image.jpg", cv_image_output)
        writeImageDB("raw", self.protocol, self.step, "raw_image.jpg")

        # Calls colony_selection methods
		parameters, image = colony_selection()

        # Saves modified image and found parameters to DB
        imwrite("temp_image.jpg", image)
        writeParamsDB(operation, self.protocol, self.step, parameters)	
        writeImageDB(operation, self.protocol, self.step, "temp_image.jpg")

        # Publish done
		self.bca_done.publish(True)
	

    def colony_selection(self):
        """
        colony_selection calls BC_finder methods from bca_cv.py library. Then, It selects
        the colony that fits the specifications from ros topics msg. 
        """

		# BC_finder parameters 
		dish_size = [600,700]
		area_min = 25
		dist_col = 5
		med_filt = 5

		# BC_finder from bca_cv.py library
		[cv_image_output, perimeter, excentricity, area, color, centers] = /
        BC_finder(self.cv_image, dish_size, area_min, dist_col, med_filt, not self.picking)

        # Selection of colonies cooresponding to specs if operation is picking
        if self.picking:
            index = np.ones(len(perimeter))

            temp_index = np.where(perimeter < self.perimeter_min)
            index[temp_index] = 0

            temp_index = np.where(perimeter > self.perimeter_max)
            index[temp_index] = 0

            temp_index = np.where(excentricity < self.excentricity_min)
            index[temp_index] = 0

            temp_index = np.where(excentricity > self.excentricity_max)
            index[temp_index] = 0

            temp_index = np.where(area < self.area_min)
            index[temp_index] = 0

            temp_index = np.where(area > self.area_max)
            index[temp_index] = 0

            index = (np.matrix(index)).transpose()
            parameters = np.concatenate((index,perimeter,excentricity,area,color,centers))
            parameters = parameters[np.argsort(-parameters[:,0],0)][:]
            
            parameters[:,0][self.number_of_colony:] = 0
            
        # No selection if operation is analysis
        elif:
            index = np.zeros(len(perimeter))
            index = (np.matrix(index)).transpose()
            parameters = np.concatenate((index,perimeter,excentricity,area,color,centers))

        #TODO ADD color selection
		return parameters, image
	
    def writeParamsDB(self,operation, protocol, step, parameters):
        """
        Write params to DB
        Args :
                - operation : "picking" or "analysis"
                - protocol : DB names  
                - step : Protocole step
                - parameters : Parameters to write in DB 
                    (x,6) numpy matrix object
        """

        # mongoDB client intialization 
        client = pymongo.MongoClient()
        protocol_db = client[protocol]
          
        colonies = []

        j = 1

        # Parsing parameters numpy matrix to create colony dict
        for i in parameters:
            colony = {
                'operation': operation,
                'step': step,
                'id': j,
                'selected': parameters[i,0],
                'perimeter': parameters[i,1],
                'excentricity': parameters[i,2],
                'area': parameters[i,3],
                'color': [i,4],
                'x': parameters[i,5,0],
                'y': parameters[i,5,1]}

            j = j + 1
            colonies.append(colony)
        
        protocol_db.colonies.insert_many(colonies)

    def writeImageDB(self, operation, protocol, step, image):
        """
        Write image to DB
        Args :
                - operation : "raw", "picking" or "analysis"
                - protocol : DB names  
                - step : Protocole step
                - image : image to write in DB (.jpg filename)
        """

        # mongoDB client intialization 
        client = pymongo.MongoClient()
        protocol_db = client[protocol]
        fs = GridFS(protocol_db)

        
        with open(image,'rb') as f:
            data = f.read()

        # Saves image to DB
        filename = "{0}_{1}.jpg".format(operation,step)
        image_id = fs.put(data, filename=filename)                

        protocol_db.images.insert_one({'filename': filename, 'image_id': image_id})


    def listener(self):
    	rospy.spin()

if __name__ == '__main__':
    try:
        cam = Camera2D()
        cam.listener()

    except (rospy.ROSInterruptException, EnvironmentError) as e:
        print(e)

