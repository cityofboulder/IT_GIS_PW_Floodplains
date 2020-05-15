# standard libraries
import os
import sys
import getpass
import time
import traceback
from os import path

# third party libraries
import arcpy
from arcpy import env

# personal modules
sys.path.append(r"S:\PW\PWShare\GIS\Scripts\Modules")
import floodplain_functions as scrape
import useful_script_tools as ust

# local database connections
username = getpass.getuser()
user = path.join(r"C:\Users", username)
sde_path = path.join(user, "AppData", "Roaming", "ESRI", "ArcGISPro", "Favorites")
# PROD2 connections
gis_prod2 = path.join(sde_path, "gis on gisprod2.sde")
gisscr_prod2 = path.join(sde_path, "gisscr on gisprod2.sde")

"""
*******************************************************************************
"""
# project directory
project_path = path.abspath(os.getcwd())

scripts = path.join(project_path, 'scripts')
download_path = path.join(project_path, 'downloads')
archive_path = path.join(project_path, 'archived')
final = path.join(project_path, 'final.gdb')
scratch = path.join(project_path, 'scratch.gdb')

# environment settings
env.overwriteOutput = True

"""
*******************************************************************************
"""
if __name__ == '__main__':
    # logging setup
    start = time.time()
    log = ust.setup_log()
    
    """
    ***************************************************************************
    START SCRIPT
    ***************************************************************************
    """
    try:
        ust.log_time(log, "Started...\n")
        """
        ***********************************************************************
        """
        # Step 1: Scrape download info from FEMA
        ust.log_time(log, "Gathering release info from FEMA...")
        info_dict = scrape.scrape_info()
        
        # Step 2: Check if the file has already been downloaded to disk
        ust.log_time(log, "Checking status of FEMA download...")
        email = scrape.check_status(root_folder = project_path)
        if email:
            sys.exit(0)
        """
        ***********************************************************************
        Script stops here if the file has already been downloaded.
        ***********************************************************************
        """
        # Step 3: Download zip folder and extract files to the download folder
        ust.log_time(log, "Downloading zip file from FEMA's website...")
        scrape.download(url = info_dict['Link'],
                        file_path = download_path,
                        file_name = info_dict['Name'])
        
        # Step 4: Delete unnecessary files from unzipped contents
        ust.log_time(log, "Deleting irrelevant FEMA data...")
        scrape.delete_unrelated(path_name = download_path)
        
        # Step 5: List shapefiles and tables from unzipped contents 
        env.workspace = download_path
        shps = [path.join(download_path, s) for s in arcpy.ListFeatureClasses()]
        tabs = [path.join(download_path, t) for t in arcpy.ListTables()]
        
        # Step 6: Create a file gdb in the "archived" folder for reprojection
        ust.log_time(log, "Creating archive folder...")
        zip_fgdb = path.join(archive_path, info_dict['Date String'] + '.gdb')
        arcpy.CreateFileGDB_management(out_folder_path = archive_path,
                                       out_name = info_dict['Date String'])
        
        # Step 7.1: Project remaining shps to fgdb
        ust.log_time(log, "Projecting shapefiles to archive fgdb...")
        prj = arcpy.SpatialReference(2876) #State Plane Colorado HARN US foot
        arcpy.BatchProject_management(Input_Feature_Class_or_Dataset = shps,
                                      Output_Workspace = zip_fgdb,
                                      Output_Coordinate_System = prj)
        
        # Step 7.2: Cut dbf tables into fgdb
        ust.log_time(log,  "Adding .dbf tables to archive fgdb...")
        for t in tabs:
            arcpy.TableToTable_conversion(in_rows = t,
                                          out_path = zip_fgdb,
                                          out_name = t.split('\\').pop().strip('.dbf'))
        
        # Step 8: Delete all unzipped contents from download folder
        ust.log_time(log, "Deleting shapefiles from download folder...")
        for f in os.listdir(download_path):
            if path.isfile(path.join(download_path, f)) and not '.zip' in f:
                os.remove(path.join(download_path, f))
        
        # Step 9: Create List of Boulder's FIRM IDs
        ust.log_time(log, "Summarizing Boulder's FIRM Panels...")
        txts = path.join(scripts, 'BoulderFIRMIDs.txt')
        ids = scrape.list_boulder_panels(txt_file = txts)
        
        # Step 10: Check if any FIRM Panels or LOMRs were effected in Boulder
        ust.log_time(log, "Checking if updates occurred in Boulder...")
        firm = path.join(zip_fgdb, 'S_FIRM_PAN')
        lomr = path.join(zip_fgdb, 'S_LOMR')
        firm_check, lomr_check = scrape.check_revisions(firm_fc = firm, lomr_fc = lomr)
        
        # Step 11: Compose email if no LOMRs or FIRM panels affect Boulder's floodplains
        ust.log_time(log, "Verifying update...")
        email = scrape.verify_update(firm_result = firm_check, 
                                     lomr_result = lomr_check, 
                                     dest_folder = archive_path)
        if email:
            sys.exit(0)
        """
        ***********************************************************************
        Script stops here if Boulder's floodplains did not change.
        ***********************************************************************
        """
        # Step 12.1: Define paths, lists and where statements for extracting info
        ust.log_time(log, "Extracting FEMA geometries and attributes...")
        floodFEMA = path.join(zip_fgdb, 'S_FLD_HAZ_AR')
        floodSDE = path.join(gis_prod2, 'UTIL.Floodplains')
        where = """LIFECYCLE IN ('Active', 'Proposed') AND FLOODPLAIN IN 
                   ('500 Year', '100 Year', 'Conveyance Zone')"""
        
        # Step 12.2: Save the extent of floodplain changes to a geometry object
        ust.log_time(log, "Extracting the boundary of floodplain changes...")
        clipper = scrape.dissolve_to_geom(firm_check, lomr_check)
        
        # Step 12.3: Extract information from FEMA and save to a dictionary
        ust.log_time(log, "Extracting FEMA geometries and attributes...")
        fema_geoms = scrape.extract_fema_geoms_and_attrs(floodFEMA, clipper) 
        
        # Step 13: Extract the names of current floodplains and transfer them to FEMA geoms
        ust.log_time(log, "Extracting and transferring drainage names...")
        named_geoms = scrape.extract_named_geoms(floodSDE, where, clipper)
        scrape.transfer_attrs(fema_geoms, named_geoms)
        
        # Step 14: Create a version and a db connection through that version for edits
        ust.log_time(log, "Creating a version and db connection...")
        env.workspace = gisscr_prod2
        scrape.create_version_and_db_connection(project_path)
        
        # Step 15: Perform edits on the version
        ust.log_time(log, "Performing edits on UTIL_FloodplainEditor...")
        env.workspace = scrape.new_gisscr
        edit_fc = 'UTIL.Floodplains'
        edit_fields = sorted([str(f.name) for f in arcpy.ListFields(floodSDE) if 
                              not f.required and not any(x in f.name for x in 
                                                         ['_', 'GLOBAL'])])
        edit_fields.insert(0, 'SHAPE@')
        email = scrape.edit_floodplain_version(edit_fc, edit_fields, where, 
                                               clipper, fema_geoms)
        
        # Step 16: Send success email
        scrape.flood_email(email)
        ust.log_time(log, "Ready for manual QA/QC edits.")

    except SystemExit:
        # send email notification
        scrape.flood_email(email)
        # log this outcome
        ust.log_time(log, "Floodplain delineations haven't changed in Boulder...\n")
        
    except Exception as e:
        # catch unknown exception and write to log
        error = "{}\n\n{}\n".format(e.args[0], traceback.format_exc())
        log.write(error)
        print error
    
    finally:
        # Extract time taken to run script
        total = time.time() - start
        mins = str(int((total)/60))
        secs = str(round((total)%60,0))
        # write outcome to log
        ust.log_time(log, "Process took {} minutes and {} seconds".format(mins, secs))
        log.close(); del log
















