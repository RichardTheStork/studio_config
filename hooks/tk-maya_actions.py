# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that loads defines all the available actions, broken down by publish type. 
"""
import sgtk
import os
import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel

HookBaseClass = sgtk.get_hook_baseclass()

def getNextAvailableNamespace(namespaceBase):
    """@brief Return the next available name space.

    @param namespaceBase Base of the namespace. (string) ex:NEMO01
    """
    for i in xrange(1, 1000) :
        newNamespace = "%s_%03d" % (namespaceBase, i)
        if not pm.namespace(exists=newNamespace) :
            return newNamespace

class MayaActions(HookBaseClass):
	
	##############################################################################################################
	# public interface - to be overridden by deriving classes 
	
	def generate_actions(self, sg_publish_data, actions, ui_area):
		"""
		Returns a list of action instances for a particular publish.
		This method is called each time a user clicks a publish somewhere in the UI.
		The data returned from this hook will be used to populate the actions menu for a publish.
	
		The mapping between Publish types and actions are kept in a different place
		(in the configuration) so at the point when this hook is called, the loader app
		has already established *which* actions are appropriate for this object.
		
		The hook should return at least one action for each item passed in via the 
		actions parameter.
		
		This method needs to return detailed data for those actions, in the form of a list
		of dictionaries, each with name, params, caption and description keys.
		
		Because you are operating on a particular publish, you may tailor the output 
		(caption, tooltip etc) to contain custom information suitable for this publish.
		
		The ui_area parameter is a string and indicates where the publish is to be shown. 
		- If it will be shown in the main browsing area, "main" is passed. 
		- If it will be shown in the details area, "details" is passed.
		- If it will be shown in the history area, "history" is passed. 
		
		Please note that it is perfectly possible to create more than one action "instance" for 
		an action! You can for example do scene introspection - if the action passed in 
		is "character_attachment" you may for example scan the scene, figure out all the nodes
		where this object can be attached and return a list of action instances:
		"attach to left hand", "attach to right hand" etc. In this case, when more than 
		one object is returned for an action, use the params key to pass additional 
		data into the run_action hook.
		
		:param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
		:param actions: List of action strings which have been defined in the app configuration.
		:param ui_area: String denoting the UI Area (see above).
		:returns List of dictionaries, each with keys name, params, caption and description
		"""
		app = self.parent
		app.log_debug("Generate actions called for UI element %s. "
					  "Actions: %s. Publish Data: %s" % (ui_area, actions, sg_publish_data))
		
		action_instances = []
		
		if "reference" in actions:
			action_instances.append( {"name": "reference", 
									  "params": None,
									  "caption": "Create Reference", 
									  "description": "This will add the item to the scene as a standard reference."} )

		if "import" in actions:
			action_instances.append( {"name": "import", 
									  "params": None,
									  "caption": "Import into Scene", 
									  "description": "This will import the item into the current scene."} )

		if "importNoNs" in actions:
			action_instances.append( {"name": "import without Namespace", 
									  "params": None,
									  "caption": "Import into Scene without a namespace", 
									  "description": "This will import the item into the current scene without a namespace."} )

		if "openUntitled" in actions:
			action_instances.append( {"name": "open as untitled", 
									  "params": None,
									  "caption": "open the maya file and set it to untitled", 
									  "description": "This will open the publish and rename the scene to untitled, use in empty scenes only."} )

		if "texture_node" in actions:
			action_instances.append( {"name": "texture_node",
									  "params": None, 
									  "caption": "Create Texture Node", 
									  "description": "Creates a file texture node for the selected item.."} )
			
		if "udim_texture_node" in actions:
			# Special case handling for Mari UDIM textures as these currently only load into 
			# Maya 2015 in a nice way!
			if self._get_maya_version() >= 2015:
				action_instances.append( {"name": "udim_texture_node",
										  "params": None, 
										  "caption": "Create Texture Node", 
										  "description": "Creates a file texture node for the selected item.."} )    
		return action_instances

	def execute_action(self, name, params, sg_publish_data):
		"""
		Execute a given action. The data sent to this be method will
		represent one of the actions enumerated by the generate_actions method.
		
		:param name: Action name string representing one of the items returned by generate_actions.
		:param params: Params data, as specified by generate_actions.
		:param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
		:returns: No return value expected.
		"""
		app = self.parent
		app.log_debug("Execute action called for action %s. "
					  "Parameters: %s. Publish Data: %s" % (name, params, sg_publish_data))
		
		# resolve path
		path = self.get_publish_path(sg_publish_data)
		
		if name == "reference":
			self._create_reference(path, sg_publish_data)

		if name == "import":
			self._do_import(path, sg_publish_data)
			
		if name == "import without Namespace":
			self._do_importNoNs(path, sg_publish_data)
		
		if name == "texture_node":
			self._create_texture_node(path, sg_publish_data)
			
		if name == "udim_texture_node":
			self._create_udim_texture_node(path, sg_publish_data)
		
		if name == "open as untitled":
			self._do_open_file_as_untitled(path, sg_publish_data)
						
		   
	##############################################################################################################
	# helper methods which can be subclassed in custom hooks to fine tune the behaviour of things
	
	def _create_reference(self, path, sg_publish_data):
		"""
		Create a reference with the same settings Maya would use
		if you used the create settings dialog.
		
		:param path: Path to file.
		:param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
		"""
		
		if not os.path.exists(path):
			raise Exception("File not found on disk - '%s'" % path)
		
		# make a name space out of entity name + publish name
		# e.g. bunny_upperbody           
		if self.parent.context.entity != sg_publish_data['entity']:     
			namespace = "%s" % (sg_publish_data.get("entity").get("name"))
			namespace = namespace.replace(" ", "_")
			namespace = getNextAvailableNamespace(namespace)
		elif self.parent.context.entity == sg_publish_data['entity']:
			task = sg_publish_data.get('task')
			if not task:
				raise Exception('no task linked to the published file %s' % (sg_publish_data.get('id')))
			else:
				step = self.parent.shotgun.find_one('Task', [['id','is', task['id'] ]], ['step.Step.short_name'])
				resolution = ''
				import re
				if re.match('.*(High|high|hig|HIGH).*', task.get('name')):
					resolution = 'hir'
				if re.match('.*(Layout|layout|lay).*', task.get('name')):
					resolution = 'lay'
				if re.match('.*(Low|low|LOW).*', task.get('name')):
					resolution = 'low'
				if resolution:
					namespace = "%s_%s" % (resolution, step.get('step.Step.short_name', 'NOTHING_FOUND'))
				else:
					namespace = "%s" %(step.get('step.Step.short_name', 'NOTHING_FOUND'))
				namespace = namespace.replace(" ", "_")
				#namespace = getNextAvailableNamespace(namespace)
				
		pm.system.createReference(path,  loadReferenceDepth= "all", mergeNamespacesOnClash=False, namespace=namespace)

	def _do_import(self, path, sg_publish_data):
		"""
		Create a reference with the same settings Maya would use
		if you used the create settings dialog.
		
		:param path: Path to file.
		:param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
		"""
		if not os.path.exists(path):
			raise Exception("File not found on disk - '%s'" % path)
				
		# make a name space out of entity name + publish name
		# e.g. bunny_upperbody                
		namespace = "%s %s" % (sg_publish_data.get("entity").get("name"), sg_publish_data.get("name"))
		namespace = namespace.replace(" ", "_")
		
		# perform a more or less standard maya import, putting all nodes brought in into a specific namespace
		cmds.file(path, i=True, renameAll=True, namespace=namespace, loadReferenceDepth="all", preserveReferences=True)
			
	def _do_importNoNs(self, path, sg_publish_data):
		"""
		Create a reference with the same settings Maya would use
		if you used the create settings dialog.
		
		:param path: Path to file.
		:param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
		"""
		if not os.path.exists(path):
			raise Exception("File not found on disk - '%s'" % path)
		# perform a more or less standard maya import, putting all nodes brought in into a specific namespace
		cmds.file(path, i=True, loadReferenceDepth="all", preserveReferences=True)

	def _do_open_file_as_untitled(self, path, sg_publish_data):
		"""
		opens the path and sets the session to untitled
		the maya callback is paused to not loose context
		"""
		#stop the watcher for a second, or else he will pick up the load and switch to layout
		engine = sgtk.platform.current_engine() 
		engine._MayaEngine__watcher.stop_watching()

		pm.cmds.file(path, open = True, force = True)
		pm.cmds.file(rename = "untitled")
		pm.cmds.file(rts = 1)	 

		# set scene settings
		defaultResolution = pm.PyNode("defaultResolution")
		defaultResolution.width.set(1725)
		defaultResolution.height.set(936)
		defaultResolution.deviceAspectRatio.set(1725.0/936.0)

		#start the watcher again
		engine._MayaEngine__watcher.start_watching()

	def _create_texture_node(self, path, sg_publish_data):
		"""
		Create a file texture node for a texture
		
		:param path:             Path to file.
		:param sg_publish_data:  Shotgun data dictionary with all the standard publish fields.
		:returns:                The newly created file node
		"""
		file_node = cmds.shadingNode('file', asTexture=True)
		cmds.setAttr( "%s.fileTextureName" % file_node, path, type="string" )
		return file_node

	def _create_udim_texture_node(self, path, sg_publish_data):
		"""
		Create a file texture node for a UDIM (Mari) texture
		
		:param path:             Path to file.
		:param sg_publish_data:  Shotgun data dictionary with all the standard publish fields.
		:returns:                The newly created file node
		"""
		# create the normal file node:
		file_node = self._create_texture_node(path, sg_publish_data)
		if file_node:
			# path is a UDIM sequence so set the uv tiling mode to 3 ('UDIM (Mari)')
			cmds.setAttr("%s.uvTilingMode" % file_node, 3)
			# and generate a preview:
			mel.eval("generateUvTilePreview %s" % file_node)
		return file_node
			
	def _get_maya_version(self):
		"""
		Determine and return the Maya version as an integer
		
		:returns:    The Maya major version
		"""
		if not hasattr(self, "_maya_major_version"):
			self._maya_major_version = 0
			# get the maya version string:
			maya_ver = cmds.about(version=True)
			# handle a couple of different formats: 'Maya XXXX' & 'XXXX':
			if maya_ver.startswith("Maya "):
				maya_ver = maya_ver[5:]
			# strip of any extra stuff including decimals:
			major_version_number_str = maya_ver.split(" ")[0].split(".")[0]
			if major_version_number_str and major_version_number_str.isdigit():
				self._maya_major_version = int(major_version_number_str)
		return self._maya_major_version
		
