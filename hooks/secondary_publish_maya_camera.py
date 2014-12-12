# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import time, datetime, os, subprocess
import re, shutil
import maya.cmds as cmds

import sys
from os import listdir
from os.path import isfile, join
import tempfile

import tank
from tank import Hook
from tank import TankError

import sgtk
from sgtk.platform import Application

CREATE_NO_WINDOW  = 0x00000008

#from shotgun import Shotgun

class PublishHook(Hook):
	"""
	Single hook that implements publish functionality for secondary tasks
	"""	
	def execute(self, tasks, work_template, comment, thumbnail_path, sg_task, primary_task, primary_publish_path, progress_cb, **kwargs):
		"""
		Main hook entry point
		:param tasks:				   List of secondary tasks to be published.  Each task is a 
										dictionary containing the following keys:
										{
											item:   Dictionary
													This is the item returned by the scan hook 
													{   
														name:		   String
														description:	String
														type:		   String
														other_params:   Dictionary
													}
												   
											output: Dictionary
													This is the output as defined in the configuration - the 
													primary output will always be named 'primary' 
													{
														name:			 String
														publish_template: template
														tank_type:		String
													}
										}
						
		:param work_template:		   template
										This is the template defined in the config that
										represents the current work file
			   
		:param comment:				 String
										The comment provided for the publish
						
		:param thumbnail:			   Path string
										The default thumbnail provided for the publish
						
		:param sg_task:				 Dictionary (shotgun entity description)
										The shotgun task to use for the publish	
						
		:param primary_publish_path:	Path string
										This is the path of the primary published file as returned
										by the primary publish hook
						
		:param progress_cb:			 Function
										A progress callback to log progress during pre-publish.  Call:
										
											progress_cb(percentage, msg)
											 
										to report progress to the UI
						
		:param primary_task:			The primary task that was published by the primary publish hook.  Passed
										in here for reference.  This is a dictionary in the same format as the
										secondary tasks above.
		
		:returns:					   A list of any tasks that had problems that need to be reported 
										in the UI.  Each item in the list should be a dictionary containing 
										the following keys:
										{
											task:   Dictionary
													This is the task that was passed into the hook and
													should not be modified
													{
														item:...
														output:...
													}
													
											errors: List
													A list of error messages (strings) to report	
										}
		"""
		def FindFirstImageOfSequence(FolderPath):
			ImgsList=[]
			for file in (os.listdir(FolderPath)):
				SeqImgName = str.split(str(file),".")[1]
				ImgsList.append(SeqImgName)
			First_elmnt=ImgsList[0]
			return First_elmnt
			
		def FindFirstImageOfSequence(FolderPath):
			ImgsList=[]
			for file in (os.listdir(FolderPath)):
				if file.endswith(".png"):
					SeqImgName = str.split(str(file),".")[1]
					ImgsList.append(int(SeqImgName))
				First_elmnt=ImgsList[0]
			return First_elmnt

		def FindLastImageOfSequence(FolderPath):
			ImgsList=[]
			for file in (os.listdir(FolderPath)):
				if file.endswith(".png"):
					SeqImgName = str.split(str(file),".")[1]
					ImgsList.append(int(SeqImgName))
				Last_elmnt=ImgsList[-1]
			return Last_elmnt
			
		def FindLengthOfSequence(FolderPath):
			ImgsList=[]
			for file in (os.listdir(FolderPath)):
				if file.endswith(".png"):
					SeqImgName = str.split(str(file),".")[1]
					ImgsList.append(int(SeqImgName))
				Length_seq=len(ImgsList)
			return Length_seq
			
		def MakeListOfSequence(FolderPath):
			ImgsList=[]
			for file in (os.listdir(FolderPath)):
				if file.endswith(".png"):
					SeqImgName = str.split(str(file),".")[1]
					ImgsList.append(int(SeqImgName))
			return ImgsList

		def FindMissingFramesFromSequence(SequenceSet,inputStart,inputEnd):
			# my_list= list(range( int(FindFirstImageOfSequence(os.path.dirname(RenderPath)))	, int(FindLastImageOfSequence(os.path.dirname(RenderPath)))	 ))
			my_list= list(range( inputStart, inputEnd))
			MissingFrames =  set(my_list)-set(SequenceSet)
			return sorted(MissingFrames)
			
		def combineMediaFiles(fileList,output,concatTxt=None, ffmpeg_path = "ffmpeg"):
			rootPath = str.split(str(fileList[0]),"/q")[0]
			mediaType = str.rsplit(str(fileList[0]),".",1)[1]
			mediaFilePresent = False
			mediaListFile = rootPath+'/tmp_'+mediaType+'List.txt'
			if concatTxt != None:
				mediaListFile = concatTxt
			with open(mediaListFile, 'w') as mediaTxtFile:
				for mediaFile in fileList:
					if os.path.exists(mediaFile):
						mediaFilePresent = True
						#print mediaFile
						shotPath = str.split(str(mediaFile),"/")[-1]
						if 'Sequences' in mediaFile:
							shotPath = str.split(str(mediaFile),"Sequences")[1][1:]
						if concatTxt != None:
							shotPath = str.split(str(mediaFile),os.path.dirname(concatTxt))[1][1:]
						mediaTxtFile.write("file '" +shotPath+"'")
						mediaTxtFile.write('\r\n')
					else:
						print("AUDIO FILE NOT FOUND :  " + str(mediaFile))
						# results.append({"task":"audio stuff", "errors":("AUDIO FILE NOT FOUND :  " + str(mediaFile))})
			if mediaFilePresent:
				# command = os.path.normpath(ffmpeg_path + ' -f concat -i '+mediaListFile+' -c copy '+output + " -y")
				# command = os.path.normpath(ffmpeg_path + ' -f concat -r 24 -i '+mediaListFile+' -vcodec mjpeg -r 24 -qscale 1 -pix_fmt yuvj420p -acodec pcm_s16le -ar 48000 -ac 2 '+output + " -y")
				command = os.path.normpath(ffmpeg_path + ' -f concat -r 24 -i '+mediaListFile+' -vcodec mjpeg -r 24 -qscale 1 -pix_fmt yuvj420p '+output + " -y")
				command = str.replace(str(command), "\\" , "/")
				#print command
				if sys.platform == "linux2":
					value = subprocess.call(command, shell=True)
				elif sys.platform == "win32":
					value = subprocess.call(command, creationflags=CREATE_NO_WINDOW, shell=False)
				elif sys.platform == "darwin":
					value = subprocess.call(command, shell=True)
		
				return output
			else:
				return None
		
		def findLastVersion(FolderPath,returnFile=False,returnFilePath=False):
			if os.path.exists(FolderPath):
				fileList=os.listdir(FolderPath)
			else:
				return 0
			if fileList != []:
				fileList.sort()
				lastVersion = fileList[-1]
				version = int(re.findall('\d+', lastVersion)[-1])
				if returnFilePath:
					return FolderPath+"/"+lastVersion
				if returnFile:
					return lastVersion
				return version
				#return str(FolderPath+"/"+lastVersion)
			else:
				return 0
		
		def orderMovs(movList,orderList):
			tmp = ""

		def setAudioToCorrectPath():
			scenePath = cmds.file(q=True,sceneName=True)
			scene_template = tk.template_from_path(scenePath)
			flds = scene_template.get_fields(scenePath)
			audio_template = tk.templates["shot_published_audio"]

			tank = sgtk.tank_from_entity('Project', 66)

			allShots = cmds.ls(type="shot")
			allAudio = cmds.ls(type="audio")
			reportList = []
			returnList = []
			for seqShot in allShots:
				audio = cmds.shot(seqShot,q=True,audio=True)
				audioFile = cmds.getAttr(audio+".filename")# "W:/RTS/1_PREPROD/13_ANIMATIC/q340/splitshots/wav new 01/q340_s260_snd_v001.wav";
				#print audioFile
				flds['Shot'] = flds['Sequence']+"_"+seqShot
				audioOutputFile = audio_template.apply_fields(flds)
				#audioOutputPath = str.replace(str(audioOutputPath),"\\","/")
				#print audioFile
				audioFile = str.replace(str(audioFile),"Z:/Richard The Stork","W:/RTS")
				audioOutputPath = str.rsplit(str(audioOutputFile),"\\",1)[0]
				print audioOutputPath
				if os.path.exists(audioOutputPath):
					audioOutputFile = findLastVersion(audioOutputPath,True,True)
					if audioOutputFile != 0:
						newAudio = str.rsplit(audioOutputFile,"/",1)[-1]
						newAudio = str.split(newAudio,".")[0]
						print newAudio
						cmds.delete(audio)
						ref = cmds.file( audioOutputFile, r=True, type="audio",mergeNamespacesOnClash=False, namespace="audio")
						#
						offset = cmds.getAttr(seqShot+".sequenceStartFrame")
						cmds.setAttr(newAudio+".offset", offset)
						cmds.connectAttr(newAudio+".message", seqShot+".audio")
						
						shotEnd =  cmds.getAttr(seqShot +".sequenceEndFrame")
						audioEnd = cmds.getAttr(newAudio+".endFrame")
						if audioEnd < shotEnd:
							reportList += [newAudio + "  is shorter than shot !!!"]
						if audioEnd > shotEnd:
							reportList += [newAudio + "  was longer than shot. now cut to match!!!"]
							cmds.setAttr(newAudio+".endFrame",shotEnd+1)

						returnList += [newAudio]
				else:
					print "skipped ", audio
			for report in reportList:
				print report
			return returnList
		
		def getStereoCams(sht):
			leftCam = ""
			rightCam = ""
			prevCamShape = cmds.shot(sht,q=True,cc=True)
			prevCam = cmds.listRelatives(prevCamShape,p=True)
			prevCamParent = cmds.listRelatives(prevCam,p=True)
			for obj in cmds.listRelatives(prevCamParent):
				if cmds.objectType(obj) == 'stereoRigTransform':
					leftCam = str(cmds.listConnections(obj+".leftCam",source=True)[0])
					rightCam = str(cmds.listConnections(obj+".rightCam",source=True)[0])
			return[leftCam,rightCam]

		wtd_fw = self.load_framework("tk-framework-wtd_v0.x.x")
		ffmpeg = wtd_fw.import_module("pipeline.ffmpeg")
		# ffmpeg.test()
		
		def _register_publish(path, name, sg_task, publish_version, tank_type, comment, thumbnail_path, context = None,tagList=[]):
			"""
			Helper method to register publish using the 
			specified publish info.
			"""
			ctx = self.parent.tank.context_from_path(str(path))
			# construct args:
			args = {"tk": self.parent.tank,"sg_status_list": "cmpt","context": context,"comment": comment,"path": path,"name": name,"version_number": publish_version,"thumbnail_path": thumbnail_path,"sg_task": sg_task,"published_file_type":tank_type,"user": ctx.user,"created_by": ctx.user}
			print "-------------------"
			

			sync_field_others = ["sg_sync_wtd","sg_sync_352","sg_sync_rakete"]
			if ctx.user != None:
				fields= ["sg_company"]
				company = self.parent.shotgun.find_one("HumanUser",[['id', 'is',ctx.user["id"]]], fields)["sg_company"]
				studios = { 'Walking the Dog': 'wtd', 'Studio Rakete': 'rakete', 'Bug': 'bug', 'RiseFX': 'risefx', 'Studio 352': '352' }
				sync_field = "sg_sync_%s" % (studios[company])
				
				args[sync_field] = "cmpt"
				
				for other_sync in sync_field_others:
					if other_sync != sync_field:
						args[other_sync] = "wtg"


			for a in args:
				print a , args[a]
			# print args
			# register publish;
			sg_data = tank.util.register_publish(**args)
			print 'Register in shotgun done!'
			tk.shotgun.update('PublishedFile', sg_data['id'], {'tag_list':tagList})
			return sg_data


		def orderShots(shotDictList):
			valueOrderList = []
			valueOrderListSecondary = []
			listIndex = 0
			for sht in shotDictList:
				orderNr = str("00000"+str(sht['sg_cut_order']))[-4:]
				addValue = str(listIndex)
				if sht['sg_status_list'] == 'omt':
					addValue = 'omt'
				if sht['parent_shots'] == []:
					valueOrderList += [orderNr+">>"+addValue]
				else:
					valueOrderListSecondary += [orderNr+">>"+addValue]
				listIndex += 1
			valueOrderList = sorted(valueOrderList)+sorted(valueOrderListSecondary)
			orderedList = []
			for sht in valueOrderList:
				addValue = str.split(sht,'>>')[1]
				if addValue != "omt":
					orderedList+=[shotDictList[int(addValue)]]
			return orderedList

		def checkSoundCut():
			allShots = cmds.ls(type="shot")
			allAudio = cmds.ls(type="audio")
			sequenceList = []
			for seqShot in allShots:
				#print "---", seqShot
				shotStart =  int(cmds.getAttr(seqShot +".sequenceStartFrame"))
				shotEnd  =   int(cmds.getAttr(seqShot +".sequenceEndFrame"))
				#print shotStart
				#print shotEnd
				sequenceList.append({"shot": seqShot})
				audioList = []
				audioIn = []
				audioOut = []
				for aud in allAudio:
					
					add = False
					aIn = 0
					aOut= 0
					audioStart   =  int(cmds.getAttr(aud+".offset" ))
					audioEnd = int(cmds.getAttr(aud+".endFrame"))-1
					audioOriginalDuration = int(cmds.getAttr(aud+".duration"))
					audioDuration  =  audioEnd-audioStart
					
						
					if shotStart < audioStart < shotEnd:
						add = True
						if audioEnd > shotEnd:
							aOut = shotEnd - audioStart
					if shotStart < audioEnd < shotEnd:
						add = True
						aIn = audioDuration-(audioEnd-shotStart)
					if audioStart < shotStart < audioEnd:
						add = True
						aIn = shotStart - audioStart
					if audioStart < shotEnd < audioEnd:
						add = True
						aOut = audioDuration-(audioEnd-shotEnd)+1
					
					if add:
						audioList.append([aud,aIn,aOut])

				sequenceList[-1]["audioList"] = audioList
			
			scenePath = cmds.file(q=True,sceneName=True)
			scene_template = tk.template_from_path(scenePath)
			audio_template = tk.templates["shot_published_audio"]
			flds = scene_template.get_fields(scenePath)
			flds['Step'] = 'snd'
			soundCheckList = ["These audio cuts dont match the camera cuts."]
			for audio in sequenceList:
				if audio['audioList'] != []:
					#print audio['shot']
					flds['Shot'] = flds['Sequence']+"_"+str(audio['shot'])
					i=0
					newAudio =[]
					soundCheckList += [""]
					soundCheckList += ["audio files overlapping shot " + audio['shot']]
					for aud in audio['audioList']:
						inSec = float(aud[1])/24
						outSec = float(aud[2])/24
						print aud[0],inSec,outSec
						# print "------>>>>>>>>>", aud
						soundCheckList += [aud[0] +"   cut in offset = "+ str(aud[1]) +"   cut out offset = "+ str(aud[2])]

			return sequenceList
		def MakeSoundCuts(ffmpegPath,Input,Output,Position,Duration ):
			time01= Position
			time02= Duration
			if os.path.isfile(Output):
				os.remove(Output)
			subprocess.call('%s -i "%s" -ss "%s" -t "%s" -acodec copy "%s"' %(ffmpegPath,Input,time01,time02,Output))
		def fixSound(sequenceList):
			## tempfile function supposed to work on linux/ drawin
			tmpFolder = tempfile.gettempdir()
			if not os.path.exists(tmpFolder):
				os.makedirs(tmpFolder)
			scenePath = cmds.file(q=True,sceneName=True)
			sceneName = str.split(str(scenePath),"/")[-1]
			scene_template = tk.template_from_path(scenePath)
			audio_template = tk.templates["shot_published_audio"]
			flds = scene_template.get_fields(scenePath)
			flds['Step'] = 'snd'
			for audio in sequenceList:
				if audio['audioList'] != []:
					print audio['shot']
					flds['Shot'] = flds['Sequence']+"_"+str(audio['shot'])
					i=0
					newAudio =[]
					for aud in audio['audioList']:
						inSec = float(aud[1])/24
						outSec = float(aud[2])/24
						print aud[0],inSec,outSec
						if outSec == 0.0:
							outSec = 10000
						input = cmds.getAttr(aud[0]+'.filename')
						output = tmpFolder+"/"+audio['shot']+"_part"+str(i)+str.split(str(input),"/")[-1]
						i+=1
						MakeSoundCuts(ffmpegPath,input,output,inSec,outSec)
						newAudio +=[output]
					audioOutput = audio_template.apply_fields(flds)
					
					# version UP
					latestVersion = findLastVersion(os.path.dirname(audioOutput))+1
					flds['version'] = latestVersion
					audioOutput = audio_template.apply_fields(flds)
					# combine
					mergedAudio = combineMediaFiles(newAudio,audioOutput,tmpFolder+"/tmp_wavList.txt",ffmpegPath)
					
					ver = str(findLastVersion(os.path.dirname(audioOutput),True))
					newAudioName = str.rsplit(ver,"_",1)[0]
					cmds.file( audioOutput, i=True, type="audio",mergeNamespacesOnClash=False, namespace=flds['Shot']+"_audio",resetError=True)
					crappyAudioName = str.split(ver,".")[0]
					cmds.rename(crappyAudioName,newAudioName)
					cutIn = cmds.getAttr(audio['shot']+".startFrame")
					cutOut = cmds.getAttr(audio['shot']+".endFrame")
					cutDuration = cutOut-cutIn
					cmds.setAttr(newAudioName+".offset", cutIn)
					cmds.setAttr(newAudioName+".sourceEnd",cutDuration+1)
					cmds.connectAttr(newAudioName+".message", audio['shot']+".audio",f=True)
					print "-----------------------------------------------------------------------------________________-------------------------------------------------------------------------"
					# PUBLISH
					file_template = tk.template_from_path(audioOutput)
					flds = file_template.get_fields(audioOutput)
					print audioOutput
					ctx = tk.context_from_path(audioOutput)

					print ctx

					sg_task = tk.shotgun.find("Task",[['content', 'is',"Sound"],["entity",'is',ctx.entity]], ['id'])
					try:
						sg_task = sg_task[0]
					except indexError:
						print "SKIPPED - are the folders already created on shotgun?????"
						errors.append("SKIPPED - are the folders already created on shotgun?????")
					if sg_task != []:
						_register_publish(audioOutput,newAudioName,sg_task,flds['version'],"Audio", "publish","",ctx,["from maya : "+sceneName])
					else:
						print "SKIPPED - are the folders already created on shotgun?????"
						errors.append("SKIPPED - are the folders already created on shotgun?????")
						#popup('error',"skipped creation of "+newAudioName+" - are the folders already created on shotgun??")

			for audio in sequenceList:
				if audio['audioList'] != []:
					for aud in audio['audioList']:
						if cmds.objExists(aud[0]):
							print "------------------",aud[0],"------------------------"
							cmds.delete(aud[0])


		shots = cmds.ls(type="shot")
		shotCams = []
		unUsedCams = []

		sides=["l","r"]

		pbShots = []
		CutInList = []
		parentShotList = []
		
		# these booleans can be used for 
		noOverscan = False
		resetCutIn = False

		# template stuff...
		# tk = tank.tank_from_path("W:/RTS/Tank/config")
		tk = self.parent.tank
		scenePath = cmds.file(q=True,sceneName=True)
		scene_template = tk.template_from_path(scenePath)
		flds = scene_template.get_fields(scenePath)
		flds['width'] = 1724
		flds['height'] = 936
		pb_template = tk.templates["maya_seq_playblast_publish"]
		pb_template_current = tk.templates["maya_seq_playblast_current"]
		pbArea_template = tk.templates["maya_seq_playblast_publish_area"]
		audio_template = tk.templates["shot_published_audio"]
		mov_template = tk.templates["maya_seq_playblast_publish_currentshots_mov"]
		concatMovTxt = tk.templates["maya_seq_playblast_publish_concatlist"]
		pbMov = tk.templates["maya_seq_playblast_publish_mov"]
		pbMp4 = tk.templates["maya_seq_playblast_review_mp4"]

		# get extra shot info through shotgun
		fields = ['id']
		sequence_id = self.parent.shotgun.find('Sequence',[['code', 'is',flds['Sequence'] ]], fields)[0]['id']
		fields = ['id', 'code', 'sg_asset_type','sg_cut_order','sg_cut_in','sg_cut_out','sg_cut_duration','sg_status_list','parent_shots']
		filters = [['sg_sequence', 'is', {'type':'Sequence','id':sequence_id}]]
		assets= self.parent.shotgun.find("Shot",filters,fields)
		results = []
		errors = []
		if sys.platform == "linux2":
			ffmpegPath = r'%s' % (os.getenv('FFMPEG','/rakete/tools/rakete/ffmpeg/lx64/ffmpeg'))
		elif sys.platform == "win32":
			ffmpegPath = '"'+os.environ.get('FFMPEG_PATH')
			if "ffmpeg.exe" not in ffmpegPath:
				ffmpegPath += "\\ffmpeg.exe"
			ffmpegPath += '"'
		elif sys.platform == "darwin":
			ffmpegPath = r'%s' % (os.getenv('FFMPEG','/rakete/tools/rakete/ffmpeg/lx64/ffmpeg'))
		soundFixList = checkSoundCut()
		print soundFixList
		fixSound(soundFixList)

		for task in tasks:
			item = task["item"]
			output = task["output"]
			errors = []
			
			#get shots from scan scene
			if item["type"] == "shot":
				shotTask = [item["name"]][0]
				pbShots += [shotTask]
			# get corresponding cut values from shotgun
				for sht in assets:
					shot_from_shotgun = str.split(sht['code'],"_")[1]
					if shot_from_shotgun == shotTask:
						CutInList += [sht['sg_cut_in']]
						parentShotList += [sht['parent_shots']]
			
			# set extra settings
			if item["type"] == "setting":
				if item["name"]=="overscan":
					noOverscan = True
				if item["name"]=="set Cut in":
					resetCutIn = True

			# if there is anything to report then add to result
			if len(errors) > 0:
				# add result:
				results.append({"task":task, "errors":errors})

		# temporarily hide cams and curves
		modPan = cmds.getPanel(type="modelPanel")
		for pan in modPan:
			cmds.modelEditor( pan,e=True, alo= False, polymeshes =True )
			cmds.modelEditor( pan,e=True,displayAppearance="smoothShaded")
			cmds.modelEditor( pan,e=True,displayTextures=True)
			allobjs = cmds.ls(type= "transform")
			boundingboxObjsList = []


			for i in allobjs:
				if cmds.getAttr(i+".overrideEnabled"):
					if cmds.getAttr(i+".overrideLevelOfDetail") == 1:
						boundingboxObjsList.append(i)
						cmds.setAttr(i+".overrideLevelOfDetail",0)
						
		currentselection= cmds.ls(sl=True)
		cmds.select(cl=True)
		
		cmds.headsUpDisplay(lv=False)

		CamsList = cmds.listCameras()
		for Cam in CamsList:
			cmds.camera(Cam, e=True, dr=True, dgm=True,ovr=1.3)
		

		#Get USER
		USER = sgtk.util.get_current_user(tk)
		if USER == None:
			USER = {'email': 'rnd@walkingthedog.be',
			 'id': 63,
			 'image': 'https://sg-media-usor-01.s3.amazonaws.com/7df0575d53fc3b61c36343837da18effb72bb6ff/86f714413d0a2c68382b706e8e45991d41a0ffed/thumb_t.jpg?AWSAccessKeyId=AKIAIFHY52V77FIVWKLQ&Expires=1415784134&Signature=%2Ff4qeNQMq4oHscIKePb1IrtRPZQ%3D',
			 'login': 'rnd',
			 'name': 'WTD RND',
			 'type': 'HumanUser'}


		# audio stuff
		'''
		stepVersion = flds['version']
		step = flds['Step']
		audioList = []
		for sht in shots:
			#print sht
			flds['Shot'] = (flds['Sequence']+"_"+sht)
			flds['version'] = findLastVersion(os.path.dirname(audio_template.apply_fields(flds)))
			flds['Step'] = 'snd'
			print flds['version']
			if flds['version'] > 0:
				audioList += [str.replace(str(audio_template.apply_fields(flds)),"\\","/")]
		flds['Shot'] = flds['Sequence']
		flds['version'] = stepVersion #set version back
		flds['Step'] = step
		
		audioOutput = pbArea_template.apply_fields(flds)+"/"+flds['Sequence']+"_"+flds['Step']+".wav"
		if audioList != []:
			combinedAudio = combineMediaFiles(audioList,audioOutput, ffmpeg_path = ffmpegPath)
		print ("combined audio at  " + audioOutput)
		'''


		# replacedAudio = setAudioToCorrectPath()
		# for aud in replacedAudio:
		# 	results.append({"task":{'item': aud , 'output': 'replaced' }})

		Test = True;
		#Test = False;
		if Test:
			j = 0
			RenderPath = ""
			for pbShot in pbShots:
				CutIn = CutInList[j]
				parentShot = ""
				if parentShotList[j] != []:
					parentShot = str.split(parentShotList[j][0]['name'],"_")[-1]
				j += 1
				
				sequenceName = flds ['Sequence']
				shotName = pbShot
				
				# ... correct this in the templates?
				flds['Shot'] = flds['Sequence']+"_"+pbShot

				

				#get camera name from sequence shot 
				shotCam = cmds.shot(pbShot, q=True, currentCamera=True)

				# overscanValue = cmds.getAttr(shotCam+".overscan")
				cmds.setAttr(shotCam+".overscan", 1.3)
				if noOverscan:
					cmds.setAttr(shotCam+".overscan", 1)


				shotCams = [shotCam]
				previewCam = shotCam
				if flds['Step'] == 's3d':
					shotCams = getStereoCams(pbShot)
				s = 0
				for shotCam in shotCams:
					side = sides[s]
					s += 1
					if flds['Step'] == 's3d':
						flds['eye'] = side.lower()

					cmds.shot(pbShot, e=True, currentCamera=shotCam)
					focal = cmds.getAttr(shotCam+'.focalLength')
					# make outputPaths from templates
					RenderPath = pb_template.apply_fields(flds)
					pbPath = str.split(str(RenderPath),".")[0]
					renderPathCurrent = pb_template_current.apply_fields(flds)
					pbPathCurrent = str.split(str(renderPathCurrent),".")[0]
					if not os.path.exists(os.path.dirname(pbPathCurrent)):
						os.makedirs(os.path.dirname(pbPathCurrent))
					pbPathCurrentMov = mov_template.apply_fields(flds)
					if not os.path.exists(os.path.dirname(pbPathCurrentMov)):
						os.makedirs(os.path.dirname(pbPathCurrentMov))

					# report progress:
					progress_cb(0, "Publishing", task)

					shotStart = cmds.shot(pbShot,q=True,sequenceStartTime=True)
					shotEnd = cmds.shot(pbShot,q=True,sequenceEndTime=True)
					progress_cb(25, "Making playblast %s" %pbShot)
					cmds.playblast(indexFromZero=False,filename=(pbPath),fmt="iff",compression="png",wh=(flds['width'], flds['height']),startTime=shotStart,endTime=shotEnd,sequenceTime=1,forceOverwrite=True, clearCache=1,showOrnaments=1,percent=100,offScreen=True,viewer=False,useTraxSounds=True)
					progress_cb(50, "Placing Slates %s" %pbShot)
					
					Film = "Richard the Stork"
					#GET CURRENT DATE
					today = datetime.date.today()
					todaystr = today.isoformat()
					
					"""
						Adding Slates to playblast files
					"""
					for i in range(int(shotStart),int(shotEnd)+1):
						FirstPartName = RenderPath.split( '%04d' )[0]
						EndPartName = '%04d' % i + RenderPath.split( '%04d' )[-1]
						ImageFullName = FirstPartName + EndPartName
						pbFileCurrent = pbPathCurrent+"."+EndPartName
						print 'fld ===>',flds
						print 'USER===>',USER
						ffmpeg.ffmpegMakingSlates(inputFilePath= ImageFullName, outputFilePath= ImageFullName, topleft = flds ['Sequence']+"_"+flds['Step']+"_v"+str('%03d' % (flds['version'])), topmiddle = Film, topright = str(int(CutIn))+"-"+str('%04d' %(i-int(shotStart)+CutIn))+"-"+str('%04d' %(int(shotEnd)-int(shotStart)+CutIn))+"  "+str('%04d' %(i-int(shotStart)+1))+"-"+str('%04d' %(int(shotEnd)-int(shotStart)+1)), bottomleft = shotName+" - focal_Length "+ str(focal), bottommiddle = USER['name'], bottomright = todaystr , ffmpegPath =ffmpegPath, font = "C:/Windows/Fonts/arial.ttf"  )
						print("COPYING PNG "+ImageFullName+"  TO  "+pbFileCurrent+"  FOR SHOT  " + shotName)
						shutil.copy2(ImageFullName, pbFileCurrent)
					
					shotAudio = audio_template.apply_fields(flds)
					shotAudio = findLastVersion(os.path.dirname(shotAudio),True,True)
					if shotAudio == 0:
						print " NO PUBLISHED AUDIO FOUND"
						for aud in [parentShot,pbShot]:
							try:
								audio = cmds.shot(aud,q=True,audio=True)
								shotAudio = '"'+cmds.getAttr(audio+".filename")+'"'
								shotAudio = str.replace(str(shotAudio),"Z:/Richard The Stork/",'W:/RTS/')
								print "used audio from maya :  ", shotAudio
								break
							except:
								shotAudio = ''
					print ffmpeg.ffmpegMakingMovie(inputFilePath=renderPathCurrent, outputFilePath=pbPathCurrentMov, audioPath=shotAudio, start_frame=int(shotStart),end_frame=int(shotEnd), framerate=24 , encodeOptions='libx264',ffmpegPath=ffmpegPath)
				# end_frame=shotEnd
				cmds.shot(pbShot, e=True, currentCamera=previewCam)
			
			if currentselection != []:
				cmds.select(currentselection)
			
			if flds['Step'] == 'lay':
				sides = ['']
			for side in sides:
				if flds['Step'] == 's3d':
					flds['eye'] = side.lower()
					
				
				RenderPath = pb_template.apply_fields(flds)
				print RenderPath

				for i in boundingboxObjsList:
					cmds.setAttr(i+".overrideEnabled",True)
					cmds.setAttr(i+".overrideLevelOfDetail",1)
				sequenceTest= MakeListOfSequence(os.path.dirname(RenderPath))
				FistImg= int(FindFirstImageOfSequence(os.path.dirname(RenderPath))) 
				LastImg= int(FindLastImageOfSequence(os.path.dirname(RenderPath)))

				FramesMissingList= FindMissingFramesFromSequence( sequenceTest ,FistImg ,LastImg )
				
				"""
					Copy empty frames
				"""
				# blackFrame = False
				# blackFrameName = ""
				# for n in FramesMissingList:
					# if blackFrame == False:
						# blackFrameName = FirstPartName+str('%04d' % n)+".png"
						# value = subprocess.call('%s -f lavfi -i color=c=black:s="%s" -vframes 1 "%s"' %(ffmpegPath,(str(flds['width'])+"x"+ str(flds['height'])),FirstPartName+str('%04d' % n)+".png"))
						# print '%s -f lavfi -i color=c=black:s="%s" -vframes 1 "%s"' %(ffmpegPath,(str(flds['width'])+"x"+ str(flds['height'])),FirstPartName+str('%04d' % n)+".png")
						# blackFrame = True
					
					# newFrameName = FirstPartName+str('%04d' % n)+".png"
					# if blackFrameName != newFrameName:
						# shutil.copy2(blackFrameName, newFrameName)	

				FirstImageNumber= FindFirstImageOfSequence(os.path.dirname(RenderPath))
				FirstImageNumberSecond= FirstImageNumber/24

				'''
				makeSeqMov
				'''
				concatTxt = concatMovTxt.apply_fields(flds)
				pbMovPath = pbMov.apply_fields(flds)
				pbMp4Path = pbMp4.apply_fields(flds)
				pbMp4Path = str.replace(str(pbMp4Path),'\\','/')

				pbMovFile =  str.split(str(pbMovPath),os.path.dirname(pbMovPath))[1][1:]

				# movList = []
				# for mov in os.listdir(os.path.dirname(pbPathCurrentMov)):
				# 	movList += [os.path.dirname(pbPathCurrentMov)+"/"+mov]
				# print movList

				assetsOrdered = orderShots(assets)
				movList = []
				for ass in assetsOrdered:
					for mov in os.listdir(os.path.dirname(pbPathCurrentMov)):
						movName = str.split(str(mov),".")[0]
						if ass['code'] == movName:
							movList += [os.path.dirname(pbPathCurrentMov)+"/"+mov]
				## need to keep that for s3d layout
				if flds['Step'] == 's3d':
					for ass in assetsOrdered:
						for mov in os.listdir(os.path.dirname(pbPathCurrentMov)):
							movName = str.split(str(mov),".")[0]
							if "%s_%s" % (ass['code'], flds['eye']) == movName:
								movList += [os.path.dirname(pbPathCurrentMov)+"/"+mov]
								
				makeSeqMov = True
				if makeSeqMov:
					if not os.path.exists(os.path.dirname(pbMovPath)):
						self.parent.ensure_folder_exists(os.path.dirname(pbMovPath))
						# os.makedirs(os.path.dirname(pbMovPath))
					
					if not os.path.exists(os.path.dirname(pbMp4Path)):
						print "creating", pbMp4Path
						self.parent.ensure_folder_exists(os.path.dirname(pbMp4Path))
						print "created", pbMp4Path
						# os.makedirs(os.path.dirname(pbMp4Path))
					"""
						SEQUENCE MOV and MP4 Creation
					"""
					print "Making mov and mp4: \n", pbMovPath, ' --- ', pbMp4Path
					print movList
					print combineMediaFiles(movList,pbMovPath,concatTxt,ffmpegPath)
					
					amount = 0
					while not os.path.exists(pbMovPath) and amount < 10:
						time.sleep(1)
						amount += 1
						
					print ffmpeg.ffmpegMakingMovie(pbMovPath,pbMp4Path,encodeOptions="libx264",ffmpegPath=ffmpegPath)
							
						
					# ----------------------------------------------
					# UPLOAD MP4
					# ----------------------------------------------
					
			upload = True
			if upload:
				user = self.parent.context.user
				scenePath = cmds.file(q=True,sceneName=True)
				ctx = self.parent.tank.context_from_path(scenePath)
				fields = ['id']
				sg_task = self.parent.shotgun.find("Task",[['content', 'is',ctx.step['name']],["entity",'is',ctx.entity]], fields)
				RenderPath = re.sub('\_(l|r)\.','_%v.',RenderPath)
				
				data = {'project': {'type':'Project','id':66},
						'entity': {'type':'Sequence', 'id':int(sequence_id)},
						'code': flds ['Sequence']+"_"+flds['Step']+"_v"+str('%03d' % (flds['version'])),
						'sg_path_to_frames': re.sub('\.[0-9]{4}\.','.%04d.', (RenderPath)),
						'sg_path_to_movie':re.sub('\_(l|r)\.','_%v.',pbMovPath),
						'sg_version_type': 'publish',
						'user': user,
						'created_by': user,
						'updated_by': user,
						'sg_task': sg_task[0]
						'sg_version_type': 'publish',
						}

				if not os.path.exists(os.path.dirname(pbMp4Path)):
					os.makedirs(os.path.dirname(pbMp4Path))
				
				findVersion = self.parent.shotgun.find_one('Version', 
														[['code', 'is', flds ['Sequence']+"_"+flds['Step']+"_v"+str('%03d' % (flds['version']))],
														 ['sg_version_type', 'is', 'publish'],
														 ['sg_task', 'is', sg_task]
														] , 
														['sg_path_to_movie','sg_path_to_frames', 'id']
														)
				
				if not findVersion:
					result = tk.shotgun.create('Version', data)
				else:
					result = tk.update('Version', findVersion.get('id'),data)
				print "---> UPLOADING ",pbMp4Path
				executed = tk.shotgun.upload("Version",result['id'],pbMp4Path,'sg_uploaded_movie')
				print executed
		
			# PUBLISH
			if sg_task != []:
				version = tank.util.find_publish(tk,[primary_publish_path],fields=['version'])
				version = version.get(primary_publish_path).get('version')
				#version = findLastVersion(os.path.dirname(pbMovPath))
				#sg_task = sg_task[0]
				print sg_task
				_register_publish(re.sub('\_(l|r)\.','_%v.',pbMovPath),re.sub('\_(l|r)\.','_%v.',pbMovFile),sg_task,version,"Movie", "published playblast mov","",ctx)
				print "PUBLISHED"
			else:
				print "SKIPPED PUBLISH"
				
					
				# print "TODO : make mov of whole sequence with audio"
		return results

