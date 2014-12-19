# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import maya.cmds as cmds

import tank
from tank import Hook
from tank import TankError

class ScanSceneHook(Hook):
	"""
	Hook to scan scene for items to publish
	"""
	
	def execute(self, **kwargs):
		"""
		Main hook entry point
		:returns:       A list of any items that were found to be published.  
						Each item in the list should be a dictionary containing 
						the following keys:
						{
							type:   String
									This should match a scene_item_type defined in
									one of the outputs in the configuration and is 
									used to determine the outputs that should be 
									published for the item
									
							name:   String
									Name to use for the item in the UI
							
							description:    String
											Description of the item to use in the UI
											
							selected:       Bool
											Initial selected state of item in the UI.  
											Items are selected by default.
											
							required:       Bool
											Required state of item in the UI.  If True then
											item will not be deselectable.  Items are not
											required by default.
											
							other_params:   Dictionary
											Optional dictionary that will be passed to the
											pre-publish and publish hooks
						}
		"""   
		
		# print dir(self.parent.context)
		# print dir(self.parent.context.entity)
		# print dir(self.parent.context.task)
		# print self.parent.context.task
		
		items = []
		
		# get the main scene:
		scene_name = cmds.file(query=True, sn=True)
		if not scene_name:
			raise TankError("Please Save your file before Publishing")
		
		scene_path = os.path.abspath(scene_name)
		name = os.path.basename(scene_path)

		self.getAllObjects()
		# create the primary item - this will match the primary output 'scene_item_type':            
		items.append({"type": "work_file", "name": name})		
		other_params = self.content
		
		if len(self.content) > 0:
			PoslistItem = {"type":'poslist', "name":'Position List', "description": "Positionlist for %s" %(scene_path), "selected": True, "required": False, "other_params": other_params}
			items.append(PoslistItem)

		return items

	def getAllObjects(self):
		objectTypes = {"SET":"Set", "SUB":"Set", "PRP":"Prop", "CHR":"Character", "VHL":"Vehicle"}
		self.content = {}
		for t in objectTypes:
			tempDict = getAllFromType(t)
			if tempDict == {}:
				continue
			self.content[t] = tempDict
		# print self.content

		
def getAllFromType(type):
	temp = cmds.ls("%s*" %type, long = True, recursive = True)
	resultDict = {}
	errorList = []
	for i in temp:
		propName = i
		separatorCheck = str(i).rfind("|")
		if separatorCheck != -1:
			propName = i[ separatorCheck+1: ]
		separatorCheck = str(propName).rfind(":")
		if separatorCheck != -1:
			propName = propName[ separatorCheck+1: ]
		if propName.startswith("%s_"%type):
			if checkIfLocator(i):
				if resultDict.has_key(propName):
					errorList.append("DOUBLE '%s' in scene!" %propName)
					continue
				position = cmds.xform(i, ws=True, q=True, t=True)
				rotation = cmds.xform(i, ws=True, q=True, ro=True)
				scale = cmds.xform(i, r=True, q=True, s=True)
				asset = propName[ len("%s_"%type): propName.rfind("_")]
				resultDict[propName] = setAssetDict(propName, asset, type, longName = i, position = position, rotation = rotation, scale = scale)
	
	errorMessage = ""
	for i in errorList:
		errorMessage += "%s\n"%i
	if errorMessage != "":
		errorMessage += "\nPlease run Sanity Check or fix the naming."
		raise TankError(errorMessage)

	return resultDict

def checkIfLocator(obj):
	shape = cmds.listRelatives(obj,shapes=True,fullPath=True)
	if shape!=None:
		if cmds.objectType(shape) == "locator":
			return True
	return False
	
def setAssetDict(name, asset, assetType, longName = None, animated = None, position = [0,0,0], rotation = [0,0,0], scale = [1,1,1], parentAssets = [], resolution = None):
	tempDict = {}
	tempDict["name"] = name
	tempDict["longName"] = longName
	tempDict["asset"] = asset
	tempDict["assetType"] = assetType
	tempDict["animated"] = animated
	tempDict["resolution"] = resolution
	tempDict["position"] = position
	tempDict["rotation"] = rotation
	tempDict["scale"] = scale
	tempDict["parentAssets"] = parentAssets
	return tempDict		
