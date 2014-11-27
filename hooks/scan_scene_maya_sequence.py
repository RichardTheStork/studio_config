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
import datetime
import maya.cmds as cmds
import types
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
        
        def shotsToShotgun():
            scenePath = cmds.file(q=True,sceneName=True)
            scene_template = tk.template_from_path(scenePath)
            
            flds = scene_template.get_fields(scenePath)
            audio_template = tk.templates["shot_published_audio"]
            shot_template = tk.templates["shot_root_step"]
            #seq_template = tk.templates["maya_seq_publish"]

            fields = ['id']
            sequence_id = sg.find('Sequence',[['code', 'is',flds['Sequence'] ]], fields)[0]['id']
            fields = ['id', 'code', 'sg_asset_type','sg_cut_order','sg_cut_in','sg_cut_out']
            filters = [['sg_sequence', 'is', {'type':'Sequence','id':sequence_id}]]
            assets= sg.find("Shot",filters,fields)

            allShots = cmds.ls(type="shot")
            allAudio = cmds.ls(type="audio")
            reportList = []
            shotDictList = []
            for seqShot in allShots:
                for side in ["in","out"]:
                    shotDict = {}
                    flds['Shot'] = flds['Sequence']+"_"+seqShot
                    shotPath = shot_template.apply_fields(flds)
                    #shotInfo = {}
                    for ass in assets:
                        if ass['code'] == flds['Shot']:
                                #shotInfo = ass
                                shotDict["data"] = {}
                                shotStart =  int(cmds.getAttr(seqShot +".sequenceStartFrame"))
                                shotEnd =  cmds.getAttr(seqShot +".sequenceEndFrame")
                                add = False
                                rep = None
                                if side == "in":
                                    rep = compareInOut(flds['Shot'],"in", ass['sg_cut_in'], shotStart)
                                else:
                                    rep = compareInOut(flds['Shot'],'out', ass['sg_cut_out'], shotEnd)

                                if rep != None:
                                    reportList.append(rep)
                                    add =True
                                    shotDict["data"]["sg_cut_in"] = shotStart
                                    shotDict["data"]["sg_cut_out"] = shotEnd
                                    shotDict["description"]=rep

                                if add:
                                    shotDict["version"] = flds['version']
                                    shotDict["data"]["sg_cut_duration"] = shotEnd - shotStart
                                    shotDict["sotgun_data"] = ass
                                    shotDict["type"]="Shot"
                                    shotDict['name']=seqShot
                                    shotDict["id"]=ass['id']
                                    shotDict["scenePath"]=os.path.dirname(scenePath)
                                    shotDict["scene"]=scenePath


                    if 'type' in shotDict:
                        shotDictList += [shotDict]
            #print shotDictList
            # for report in reportList:
            #     print report
            #print "dsfffffffffffffffffffffffffff"
            popup("shots that are different from shotgun",reportList, [{'label':'update values to shotgun', 'comd':'updateShotgun('+str(shotDictList)+')' }])
            return shotDictList
            #print ('updateShotgun('+str(['dddd'])+')')
        def compareInOut(shot,inOutStr , val1,val2):
            if int(val1) != int(val2):
                return str("new cut "+inOutStr+": "+str(int(val2)) +  "   -   value on shotgun: " + str(val1))
        def popup(windowName,textList,btnList=[]):
            deleteWindows(windowName)
            window = cmds.window(windowName,title=windowName)
            cl = cmds.columnLayout()
            for text in textList:
                if isinstance(text, types.ListType):
                    for t in text:
                        if t != None:
                            cmds.text(label=t)
                else:
                    if text != None:
                        cmds.text(label=text)
            if btnList != []:
                for btn in btnList:
                    labl = btn['label']
                    comd = btn['comd']
                    deleteWindow = ""
                    if 'delete' in btn:
                        if btn['delete']:
                            deleteWindow = "cmds.deleteUI('"+window+"')"
                    #print "COMMANNNND =",comd
                    buttooon = cmds.button(label=labl,command=comd+deleteWindow)
            cmds.showWindow( window )
            return window
        
        def deleteWindows(wnd):
            for w in cmds.lsUI(wnd=True,l=True):
                if wnd in w:
                    cmds.deleteUI(w)
                    print "deleted", w
        def makeShotgunBackup(dataList):
            mediaListFile = dataList[0]['scenePath']+'/shotDataLog.txt'
            backupVersion = {"version" : str(dataList[0]["version"]) , "date": str(datetime.datetime.now())}
            with open(mediaListFile, 'a') as mediaTxtFile:
                mediaTxtFile.write(str(backupVersion))
                mediaTxtFile.write('\r\n')
                infoList = ""
                for dat in dataList:
                    infoList += str(dat["sotgun_data"])
                    infoList += ";"
                    #mediaTxtFile.write(str(dat["sotgun_data"]) + ",")
                    # for sg_dat in dat["sotgun_data"]:
                    #     mediaTxtFile.write(str(sg_dat))
                    #     mediaTxtFile.write(str(dat[sg_dat]))

                mediaTxtFile.write(str(infoList))
                mediaTxtFile.write('\r\n')
        def updateShotgun(dataList):
            #data = {'sg_cut_in': 4742 }
            makeShotgunBackup(dataList)
            for dat in dataList:
                print "UPDATING SHOTGUN VALUES"
                print dat['type']
                print dat['id']
                print dat['data']
                result = sg.update(dat['type'],dat['id'],dat['data'])
                print result
                print "UPDATED SHOTGUN VALUES"

        tk = self.parent.tank
        sg = tk.shotgun

        itemDictList = shotsToShotgun()

        items = []
        
        # get the main scene:
        scene_name = cmds.file(query=True, sn=True)
        if not scene_name:
            raise TankError("Please Save your file before Publishing")
        
        scene_path = os.path.abspath(scene_name)
        name = os.path.basename(scene_path)

        # create the primary item - this will match the primary output 'scene_item_type':            
        items.append({"type": "work_file", "name": name})
        items += itemDictList

        # makeShotgunBackup(itemDictList)

        # if there is any geometry in the scene (poly meshes or nurbs patches), then
        # add a geometry item to the list:
        #if cmds.ls(geometry=True, noIntermediate=True):
        #    items.append({"type":"geometry", "name":"All Scene Geometry"})

        return items
