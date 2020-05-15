"""
Author: Jesse Nestler
Date Created: Thu Nov 09 10:02:36 2017
Purpose: Download data from FEMA's web portal, and consolidate their schema into
more usable formats for city needs. Transfer creek names from current city
data to FEMA-derived data.
"""

"""
*******************************************************************************
IMPORT LIBRARIES
*******************************************************************************
"""
# organizational libraries
import os, sys, getpass
from os import path

# spatial libraries
import arcpy
from arcpy import env

# personal modules
scripts = path.join(r"\\boulder.local", "share", 'PW', 'Linked Documents', 
                    'Project Files', 'Flood General', 'GIS' , 'Projects', 
                    'Floodplains', 'scripts')
sys.path.append(scripts)
import data_scrape as scrape

"""
*******************************************************************************
"""
user = path.join('C:\\Users', getpass.getuser())

gis = path.join(user, 'AppData', 'Roaming', 'ESRI', 'Desktop10.4', 
                'ArcCatalog', 'gis on gisprod2.sde')

gisscr = path.join(r"\\boulder.local", "share", "PW", "PWShare", "GIS", 
                   "Scripts", "dbconnections", "gisscr on gisprod2.sde")

"""
*******************************************************************************
"""
project_path = path.join('S:\\', 'PW', 'Linked Documents', 'Project Files',
                         'Flood General', 'GIS' , 'Projects',
                         'Floodplains')

download_path = path.join(project_path, 'downloads')
archive_path = path.join(project_path, 'archived')
final = path.join(project_path, 'final.gdb')
scratch = path.join(project_path, 'scratch.gdb')

env.overwriteOutput = True

"""
*******************************************************************************
DOWNLOAD FROM FEMA
*******************************************************************************
"""
# Step 1: Scrape download url, file name, and effective date of most recent update
info_dict = scrape.scrape_info()

# Step 2: Check if the file has already been downloaded to disk
print "Checking status..."
scrape.check_status(root_folder = project_path)
"""
*******************************************************************************
Script stops here if the file has already been downloaded. An email is sent 
from within the check_status function to notify a user list of this outcome.
*******************************************************************************
"""
# Step 3: Download zip folder and extract files to the download folder
print "Downloading zip file..."
scrape.Download(url = info_dict['Link'],
                file_path = download_path,
                file_name = info_dict['Name'])

"""
*******************************************************************************
STORE NEW DOWNLOAD ON DISK
*******************************************************************************
"""
# Step 4: Delete unnecessary files from unzipped contents
scrape.delete_unrelated(path_name = download_path)

# Step 5: List shapefiles and tables from unzipped contents 
env.workspace = download_path
shps = [path.join(download_path, s) for s in arcpy.ListFeatureClasses()]
tabs = [path.join(download_path, t) for t in arcpy.ListTables()]

# Step 6: Create a file gdb in the "archived" folder for reprojection
print "Creating archive folder..."
zip_fgdb = path.join(archive_path, info_dict['Date String'] + '.gdb')
arcpy.CreateFileGDB_management(out_folder_path = archive_path,
                               out_name = info_dict['Date String'])

# Step 7.1: Project remaining shps to fgdb
print "Projecting shps..."
prj = arcpy.SpatialReference(2876) #State Plane Colorado HARN US foot
arcpy.BatchProject_management(Input_Feature_Class_or_Dataset = shps,
                              Output_Workspace = zip_fgdb,
                              Output_Coordinate_System = prj)

# Step 7.2: Cut dbf tables into fgdb
for t in tabs:
    arcpy.TableToTable_conversion(in_rows = t,
                                  out_path = zip_fgdb,
                                  out_name = t.split('\\').pop().strip('.dbf'))

# Step 8: Delete all unzipped contents from download folder
for f in os.listdir(download_path):
    if path.isfile(path.join(download_path, f)) and not '.zip' in f:
        os.remove(path.join(download_path, f))

"""
*******************************************************************************
CHECK IF LOMRs/PANEL REVS HAPPENED IN BOULDER
*******************************************************************************
"""
# Step 9: Create List of Boulder's FIRM IDs
print "Extracting FIRM/LOMR geometries..."
txts = path.join(scripts, 'BoulderFIRMIDs.txt')
ids = scrape.list_boulder_panels(txt_file = txts)

# Step 10: Check if any FIRM Panels or LOMRs were effected in Boulder
firm = path.join(zip_fgdb, 'S_FIRM_PAN')
lomr = path.join(zip_fgdb, 'S_LOMR')
firm_check, lomr_check = scrape.check_revisions(firm_fc = firm, lomr_fc = lomr)

# Step 11: Compose email if no LOMRs or FIRM panels affect Boulder's floodplains
print "Verifying update..."
scrape.verify_update(firm_result = firm_check,
                    lomr_result = lomr_check,
                    dest_folder = archive_path)
"""
*******************************************************************************
Script stops here if Boulder's floodplains did not change. An email is sent 
from within the verify_update function to notify a user list of this outcome.
*******************************************************************************
CLIP FEMA FLOOD AREAS TO FIRMSs/LOMRs AND TRANSFER ATTRIBUTES
*******************************************************************************
"""
print "Extracting FEMA geometries and attributes..."
# Step 12.1: Define paths, lists and where statements for extracting info
floodFEMA = path.join(zip_fgdb, 'S_FLD_HAZ_AR')
floodSDE = path.join(gis, 'UTIL.Floodplains')
where = "LIFECYCLE IN ('Active', 'Proposed') AND FLOODPLAIN IN ('500 Year', '100 Year', 'Conveyance Zone')"

# Step 12.2: Save the extent of floodplain changes to an arc geometry object
clipper = scrape.dissolve_to_geom(firm_check, lomr_check)

# Step 12.3: Extract information from FEMA and save to a dictionary
fema_geoms = scrape.extract_fema_geoms_and_attrs(floodFEMA, clipper) 

# Step 13: Extract the names of current floodplains and transfer them to FEMA geoms
named_geoms = scrape.extract_named_geoms(floodSDE, where, clipper)
scrape.transfer_attrs(fema_geoms, named_geoms)

"""
*******************************************************************************
CREATE A VERSION, DB CONNECTION, AND MAKE EDITS FOR MANUAL QC-ing
*******************************************************************************
"""
# Step 14: Create a version and a db connection through that version for edits
print "Creating and editing a version of floodplains..."
env.workspace = gisscr; save = path.join(project_path, "scratch")
scrape.create_version_and_db_connection(save)

# Step 15: Perform edits on the version
env.workspace = scrape.new_gisscr
edit_fc = 'UTIL.Floodplains'
edit_fields = sorted([str(f.name) for f in arcpy.ListFields(floodSDE) if not f.required and not any(x in f.name for x in ['_', 'GLOBAL'])])
edit_fields.insert(0, 'SHAPE@')

scrape.edit_floodplain_version(edit_fc, edit_fields, where, clipper, fema_geoms)


#print "Creating scratch floodplain..."
## Step 12: Clear the scratch gdb and clip city floodplains to LOMRs/FIRMs
#flood_og = path.join(zip_fgdb, 'S_FLD_HAZ_AR')
#clipper, flood_scr = scrape.ClipFloodplain(save_dest = scratch, 
#                                           flood_lyr = flood_og)
#
## Step 13.1: Add fields to the FEMA scratch copy
#add_fields = {'FEMAZONE': ['TEXT', 10], 'FLOODPLAIN': ['TEXT', 50]}
#scrape.addFieldsFromDict(in_dict = add_fields, table = flood_scr)
#
#print "Reformatting scratch floodplain..."
## Step 13.2: Reformat values to fit into new schema
#scrape.reformatFEMA(in_table = flood_scr)
#
## Step 13.3: Delete irrelevant fields
#del_fields = [f.name for f in arcpy.ListFields(flood_scr) if not f.required 
#              and f.name not in [k for k in add_fields.iterkeys()]]
#for d in del_fields:
#    arcpy.DeleteField_management(in_table = flood_scr, drop_field = d)
#
#"""
#*******************************************************************************
#TRANSFER DRAINAGE NAMES FROM EXISTING CITY DATA --> FEMA
#*******************************************************************************
#"""
## Step 14: Create a version of floodplains from UTIL_LIVE, owned by GISSCR
#floodSDE = path.join(gis, 'UTIL.Floodplains')
#
#print "Clipping SDE Floodplains..."
## Step 14.2: Clip/dissolve existing named floodplains by drainage
#clip_fc = path.join(scratch, 'FloodNamesSDE')
#arcpy.Clip_analysis(in_features = floodSDE,
#                    clip_features = clipper,
#                    out_feature_class = clip_fc)
#
## Step 14.3: List geometries for easier iteration
#fields = ['SHAPE@', 'DRAINAGE', 'LIFECYCLE']
#listSDE = []
#with arcpy.da.SearchCursor(clip_fc, fields) as sCurs:
#    for row in sCurs:
#        if any(row[2] == stat for stat in ['Active', 'Proposed']):
#            listSDE.append(row)
#            
## Step 3: Add the appropriate fields to the FEMA layer
#add = {'LIFECYCLE': ['TEXT', 16], 
#       'DRAINAGE': ['TEXT', 50],
#       'SOURCE': ['TEXT', 50],
#       'ADOPTYR': ['SHORT', None],
#       'INEFFYR': ['SHORT', None]}
#scrape.addFieldsFromDict(in_dict = add, table = flood_scr)
#
#print "Naming floodplains by drainage..."
## Step 4: Transfer creek names from cut city to clipped FEMA (time the process)
#start = time.time()
#
#fields2 = sorted([k for k in add.iterkeys()])
#fields2.append('SHAPE@')
#with arcpy.da.UpdateCursor(flood_scr, fields2) as uCurs:
#    for row in uCurs:
#        row[0] = int(info_dict['Date String'][:4])
#        row[2] = 9999
#        row[3] = "Active"
#        row[4] = 'FEMA'
#        # define a list to use for comparing geometries b/w SDE and FEMA
#        overlap_list = []
#        areas = []
#        # iterate through each SDE floodplain entry and record any overlaps
#        for item in listSDE:
#            if row[5].equals(item[0]):
#                row[1] = item[1]
#            if row[5].overlaps(item[0]):
#                overlap_list.append(item)
#                areas.append(row[5].intersect(item[0],4).area)
#        if len(overlap_list) == 1:
#            row[1] = overlap_list[0][1] #transfer creek name to FEMA
#        if len(overlap_list) > 1:
#            i = areas.index(max(areas))
#            row[1] = overlap_list[i][1] #transfer creek name from polygon with larger intersecting area
#        uCurs.updateRow(row)
#
## Step 5: Merge the FEMA layer with the city layer (should verify some creek names)
#
#
## Step 6: Dissolve City layer by DRAINAGE, FLOODPLAIN, FEMAZONE
#        
#end = time.time()
#print 'Adding creek attributes to the new floodplain FC took', str(int((end - start)/60)), 'minutes and', str(round((end - start)%60,1)), 'seconds'

"""
*******************************************************************************
TESTING
*******************************************************************************
"""

## Step 12: Extract relevant floodplain info from FEMA
#floodFEMA = path.join(zip_fgdb, 'S_FLD_HAZ_AR')
#floodSDE = path.join(gis, 'UTIL.Floodplains')
#where = "LIFECYCLE IN ('Active', 'Proposed') AND FLOODPLAIN IN ('500 Year', '100 Year', 'Conveyance Zone')"
#sde_fields = ['SHAPE@', 'DRAINAGE']
#
#clipper = scrape.dissolve_to_geom(firm_check, lomr_check)
#fema_geoms = scrape.extract_fema_geoms_and_attrs(floodFEMA, clipper) 
#
#with arcpy.da.SearchCursor(floodSDE, sde_fields, where) as sCurs:
#    named_geoms = []
#    geom = None
#    for row in sCurs:
##        if clipper.contains(row[0].centroid) or row[0].overlaps(clipper):
#        geom = row[0].clip(clipper.extent)
#        named_geoms.append({'SHAPE@': geom, 'DRAINAGE': str(row[1])})
#    
#for d in fema_geoms:
#    d['ADOPTYR'] = int(info_dict['Date String'][:4])
#    d['INEFFYR'] = 9999
#    d['LIFECYCLE'] = 'Active'
#    d['SOURCE'] = 'FEMA'
#    # if an SDE geometry contains the centroid of a FEMA geom, transfer the name over
#    for g in named_geoms:
#        if g['SHAPE@'].contains(d['SHAPE@'].centroid):
#            d['DRAINAGE'] = g['DRAINAGE']
#            break
#
#"""
#6/15: I now have a dictionary that contains all attributes for each geometry.
#The next step is to insert each fema_geom into the GISSCR.UTIL_FloodplainEditor
#and transfer over all the proper attribution. Then, I'll need to change the
#LIFECYCLE of the current floodplains inside clipper to "Inactive". This will set
#me up perfectly to perform manual QAQC on the version before posting changes. 
#"""
#
## Step 13: Create a version of floodplains for editing and attribute transfer
#save = path.join(project_path, "scratch")
#env.workspace = gisscr
#parent = "UTIL.UTIL_LIVE"; parent = "SDE.DEFAULT"
#version = "UTIL_FloodplainEditor"
#permiss = "PRIVATE"
#conn_name = 'new_gisscr'
#v_name = 'GISSCR.{}'.format(version)
#new_gisscr = path.join(save, '{}.sde'.format(conn_name))
#v_fields = sorted([str(f.name) for f in arcpy.ListFields(floodSDE) if not f.required and not any(x in f.name for x in ['_', 'GLOBAL'])]); v_fields.insert(0, 'SHAPE@')
#v_ordered = {i:k for i, k in enumerate(v_fields)}
#
#edit_fc = 'UTIL.Floodplains'
#
## Create version (if it already exists, delete and recreate)
#if any(v_name in v for v in arcpy.ListVersions(gisscr)):
#    arcpy.DeleteVersion_management(gisscr, v_name)
#    
#arcpy.CreateVersion_management(in_workspace = gisscr,
#                               parent_version = parent,
#                               version_name = version,
#                               access_permission = permiss)
#
## Create DB Connection from version
#if not path.isfile(new_gisscr) and not path.exists(new_gisscr):
#    arcpy.CreateDatabaseConnection_management(out_folder_path = save,
#                                              out_name = conn_name,
#                                              database_platform = 'ORACLE',
#                                              instance = 'gisprod2',
#                                              account_authentication = 'DATABASE_AUTH',
#                                              username = 'gisscr',
#                                              password = "gKJTZkCYS937",
#                                              version_type = 'TRANSACTIONAL',
#                                              version = v_name)
#
## Make edits
#env.workspace = new_gisscr
#
## start edit session
#edit = arcpy.da.Editor(new_gisscr)
#edit.startEditing(False, True)
#edit.startOperation()
#
## open an insert cursor for geometry edits
#iCurs = arcpy.da.InsertCursor(edit_fc, v_fields)
#
## cut geometries that cross the FIRM/LOMR boundaries
#with arcpy.da.UpdateCursor(edit_fc, v_fields, where) as uCurs:
#    for row in uCurs:
#        if row[0].overlaps(clipper):
#            row_vals = row[1:] #save all attributes (other than geometry) of the polygon-to-be-cut
#            geoms = row[0].cut(clipper.boundary()) #save the list of clipped geometries
#            uCurs.deleteRow() #delete the geometry that got cut to avoid duplicates
#            for g in geoms: #inspect each new geometry from clipping
#                iRow1 = [g] #create a new row entry with the new geometry
#                iRow1.extend(row_vals) #add attributes to the new geometry
#                if g.area > 0:
#                    iCurs.insertRow(iRow1) #add the new row to the layer
#
## make all existing geometries "Inactive"
#with arcpy.da.UpdateCursor(edit_fc, v_fields, where) as uCurs:
#    for row in uCurs:
#        if clipper.contains(row[0].centroid):
#            row[6] = 'Inactive'
#            uCurs.updateRow(row)
#
## add the new FEMA geometries to versioned floodplains
#for entry in fema_geoms:
#    iRow2 = [entry[k] for k in v_ordered.itervalues()] 
#    iCurs.insertRow(iRow2)
#
#edit.stopOperation()
#edit.stopEditing(True)
#del edit, iCurs
#
## delete items
#if path.exists(new_gisscr):
#    os.remove(new_gisscr)

















































