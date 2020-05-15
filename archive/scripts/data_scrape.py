"""
Author: Jesse Nestler
Date Created: Wed Feb 14 16:03:20 2018
Purpose: Provide all necessary functions for downloading, verifying, and
reclassifying data from FEMA to conform to the City's PROD2 standards. 
"""

"""
*******************************************************************************
IMPORT LIBRARIES
*******************************************************************************
"""
# organizational libraries
import os
from os import path
import datetime

# spatial libraries
import arcpy
from arcpy import env

# web scraping libraries
import urllib2 
from zipfile import ZipFile
from bs4 import BeautifulSoup as bs

# email libraries
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

"""
*******************************************************************************
DEFINE FUNCTIONS AND CLASSES
*******************************************************************************
"""
class HaltException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

"""
*******************************************************************************
"""
def flood_email(main_body):
    """
    Used to send email notification (encoded in HTML) of success or failure of 
    the process.
    
    :param main_body: {str} the main body of the email
    :return: {none} sends an email
    """
    # today
    global today
    today = datetime.datetime.today().strftime("%A, %d %B %Y at %H:%M")
    
    # from/to addresses
    sender = "nestj1@bouldercolorado.gov"
    password = "cohabit.besotted.ready"
    recipients = ["nestlerj@bouldercolorado.gov"]#, "shepc2@bouldercolorado.gov"]
    
    # message
    msg = MIMEMultipart('alternative')
    msg['From'] = sender
    msg['To'] = "; ".join(recipients)
    msg['Subject'] = "Floodplain Update Notification"
    
    # message intro, outro
    start =  """\
            <html>
                <head></head>
                <body>
                    <p>
                    Dear Human,<br><br>
                    This is an automated email notification regarding the most  
                    recent attempt to update the City of Boulder's Floodplain 
                    feature class in PROD2. The process was performed on 
                    {exec_datetime}, and yielded the following result:
                    </p>
                </body>
            </html>
            """.format(exec_datetime = today)

    end =   """\
            <html>
                <head></head>
                <body>
                    <p>
                    Beep Boop,<br><br>
                    End Transmision
                    </p>
                </body>
            </html>
            """
    
    body = start + main_body + end
    
    msg.attach(MIMEText(body, 'html'))
    
    # create SMTP object
    server = smtplib.SMTP(host = 'smtp.office365.com', port = 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    
    # log in
    server.login(sender, password)
    
    # send email
    server.sendmail(sender, recipients, msg.as_string())

"""
*******************************************************************************
"""
def text_to_date_time(date_string):
    """
    Takes a date string in "yyyymmdd" format and transforms it into a datetime
    object
    
    :param date_string: {str} A string of numbers representing a date in "yyymmdd" format
    :return: {datetime} A datetime object of the date_string
    """
    year = int(date_string[:4])
    month = int(date_string[4:6])
    day = int(date_string[6:])
    date = datetime.datetime(year, month, day, 0, 0)
    return date

"""
*******************************************************************************
"""
def format_date_time(date_string):
    """
    Takes a date string in "yyyymmdd" format and transforms it into a formatted
    date string for emails.
    
    :param date_string: {str} A string of numbers representing a date in "yyymmdd" format
    :retun: {str} "Weekday, Day Mon Year"
    """
    date = text_to_date_time(date_string).strftime("%A, %d %B %Y")
    return date

"""
*******************************************************************************
"""
def scrape_info():
    """
    This function automatically scrapes the download link for flood updates in
    Boulder County. It requires no inputs.
    
    :return: {dict} {'Link': url, 'Name': file_name, 'Date String': 'YYYYMMDD'}
    """
    global root, scrape_date, dt_date, format_date
    # Relevant data scraping urls
    root = "https://hazards.fema.gov/femaportal/NFHL/"
    url = root + "searchResult"
    downloadID = '08013C' #Boulder County's FIRM ID
    
    # query the website and return the html instance to the variable 'page'
    page = urllib2.urlopen(url)
    soup = bs(page, 'lxml')
    
    # find the row specific to Boulder's FIRM and scrape the download query
    tags = soup.find_all('a')
    link = [tag.attrs['href'] for tag in tags if downloadID in tag.attrs['href']][0]
    
    # define the download url and encode the query properly
    download_url = root + link.replace(' ', '%20')
    
    # extract name of the zip file from FEMAs website
    web_file_name = link.split('=').pop()
    
    # extract the release date of the zip file
    scrape_date = web_file_name.strip('.zip').split('_')[1] #string version
#    scrape_date = '20171207'
    dt_date = text_to_date_time(scrape_date) #datetime object version
    format_date = format_date_time(scrape_date) #formatted version
    
    # return values
    return {'Link': download_url, 
            'Name': web_file_name, 
            'Date String': scrape_date}

"""
*******************************************************************************
"""
def check_status(root_folder = None):
    """
    Checks whether floodplains have been updated by evaluating if a
    zip file from the same release date is saved on disk.
    
    :param root_folder: {str} The file path to the project workspace
    :return: {none} sends an email notification if update already occurred
    """
    try:
        for paths, dirs, files in os.walk(root_folder):
            # tests if any directories in path have release date in their name
            t1 = any(scrape_date in d for d in dirs)
            # tests if any files in dirs have release date in their name
            t2 = any(scrape_date in f for f in files)
            if t1 or t2:
                # define email body
                email = """\
                        <html>
                            <head></head>
                            <body>
                                <p>
                                FEMA Effective shapefiles have not been updated
                                since {date}. As a result, no new shapefiles were 
                                downloaded to disk and the City's Effective 
                                delineations remain unchanged in PROD2.<br><br>
                                <strong>No further action is required.</strong>
                                </p>
                            </body>
                        </html>
                        """.format(date = format_date)
                # raise exception to stop script from running
                raise HaltException("An email notification was sent")
                
    except HaltException as e:
        # send email notification
        flood_email(email)
        print e.value

"""
*******************************************************************************
"""
def download(url = None, file_path = None, file_name = None):
    """
    Downloads FEMA zip files from their website
    
    :param url: {str} The URL from which the zip file is being downloaded
    :param file_path: {str} The file path to the download folder
    :param file_name: {str} The name of the download file
    :return: {file} adds file to disk/server space
    """
    # open the download url
    resp = urllib2.urlopen(url)
    # define zip file path
    loc = path.join(file_path, file_name)
    # open the zip file path and download from the web
    with open(loc, 'wb') as z:
        z.write(resp.read())
    # unzip the contents to the same path as the zip file
    with ZipFile(loc) as x:
        x.extractall(file_path)

"""
*******************************************************************************
"""
def delete_unrelated(path_name = None):
    """
    Deletes all files in the download folder that do not have the following 
    keywords: ['BFE', 'FIRM_PAN', 'FLD_HAZ_AR', 'LOMR', 'SUBMITTAL', 'XS', '.zip']
    
    :param path_name: {str} The file path containing unzipped FEMA contents
    :return: {none} Deletes files from disk
    """
    # define keywords that trigger the script to keep a file
    keepers = ['BFE', 'FIRM_PAN', 'FLD_HAZ_AR', 'LOMR', 'SUBMITTAL', 
               'XS', '.zip']
    for file_name in os.listdir(path_name):
        # test whether any keywords are in file_name
        t1 = any(k in file_name for k in keepers)
        # test whether file_name starts with "L_"
        t2 = file_name.startswith('L_')
        # if the file fails both tests, delete file
        if not t1 and not t2:
            os.remove(path.join(path_name, file_name))

"""
*******************************************************************************
""" 
def list_boulder_panels(txt_file = None):
    """
    Lists the FIRM Panel numbers that correspond to areas in and around Boulder.
    
    :param txt_file: {str} File path of the text file containing Boulder's FIRM panels.
    :return: {list} Boulder's FIRM Panel ID strings
    """
    global boulder_ids
    # get Boulder's Panel #s from a text file and store them to a list
    boulder_ids = []
    with open(txt_file, 'r') as t:
        for i in t.readlines():
            boulder_ids.append(i.strip('\n'))
    
    return boulder_ids

"""
*******************************************************************************
"""       
def check_revisions(firm_fc = None, lomr_fc = None):
    """
    Checks whether any FIRM panels in or near Boulder were revised. Also checks 
    if any LOMRs were effected in or near Boulder.
    
    :param firm_fc: {str} The file path to the fc containing FIRMs (S_FIRM_PAN)
    :param lomr_fc: {str} The file path to the fc containing LOMRs (S_LOMR)
    :return: {dict} Two dictionaries containing info on FIRM/LOMR updates
                    {'County': {bool}, 'Boulder': {bool}, 'Geoms': {list}}    
    """
    global firm_info, lomr_info
    # define variables for FIRM Panels
    firm_list = []
    overall_firm_bool = False; boulder_firm_bool = False
    firm_fields = ['EFF_DATE', 'PANEL', 'SHAPE@']
    
    # define variables for LOMRs
    lomr_list = []; boulder_lomr = []
    overall_lomr_bool = False; boulder_lomr_bool = False
    lomr_fields = ['EFF_DATE', 'SHAPE@', 'STATUS']
    
    # find all new lomrs in the county
    with arcpy.da.SearchCursor(lomr_fc, lomr_fields) as sCurs1:
        for row in sCurs1:
            # test whether the lomr is new
            t1 = (row[0].year == dt_date.year and row[0].month == dt_date.month)
            # test whether the lomr is effective
            t2 = row[2] == 'Effective'
            # if lomr is new and effective, add to list
            if t1 and t2:
                overall_lomr_bool = True
                lomr_list.append(row[1])
        
    # step into the FIRM feature class
    with arcpy.da.SearchCursor(firm_fc, firm_fields) as sCurs2:
        for row in sCurs2:
            # tests if FIRM revisions occurred in current release date
            t1 = row[0] == dt_date
            # tests if a panel is in/near Boulder
            t2 = any(str(row[1]) == panel for panel in boulder_ids)
            # if there are new panels in the county
            if t1:
                overall_firm_bool = True
            # if a panel overlaps Boulder
            if t2:
                for lomr in lomr_list:
                    # if a lomr overlaps a Boulder panel, add it to list
                    if lomr.overlaps(row[2]):
                        boulder_lomr_bool = True
                        boulder_lomr.append(lomr)
            # if a panel in/near Boulder was updated, add it to list
            if t1 and t2:
                boulder_firm_bool = True
                firm_list.append(row[2])
    
    firm_info = {'County': overall_firm_bool, 
                 'Boulder': boulder_firm_bool, 
                 'Geoms': firm_list}
    lomr_info = {'County': overall_lomr_bool, 
                 'Boulder': boulder_lomr_bool, 
                 'Geoms': boulder_lomr}
    return firm_info, lomr_info

"""
*******************************************************************************
"""
def verify_update(firm_result = None, lomr_result = None, dest_folder = None):
    """
    Checks whether updates to PROD2 are necessary based on the result of the 
    check_revisions function. If no LOMRs or FIRM Panels were updated in/near 
    the city, it stops the script from running and sends an email notification.
    
    :param firm_result: {dict} Dictionary from check_revisions containing FIRM info
    :param lomr_result: {dict} Dictionary from check_revisions containing LOMR info
    :param dest_folder: {str} The location of all archived fgdbs for FEMA downloads
    :return: {none} Sends an email if no updates happened in Boulder
    """
    try:
        # tests if Boulder has revised FIRM Panels
        t1 = firm_result['Boulder']
        # tests if Boulder has new Effective LOMRs
        t2 = lomr_result['Boulder']
        # tests if County has revised FIRM Panels
        t3 = firm_result['County']
        # tests if County has new Effective LOMRs
        t4 = lomr_result['County']
        
        # if no FIRMs were revised in Boulder
        if not t1:
            # if no LOMRs were effected in Boulder
            if not t2:
                # if FIRMs were revised in the County
                if t3:
                    # if LOMRs were effected in County
                    if t4:
                        # Email that LOMRs and FIRMs in County changed, but none in Boulder
                        email = """\
                                <html>
                                    <head></head>
                                    <body>
                                        <p>
                                        <ul type="circle">
                                            <li>
                                            FEMA Effective shapefiles were updated
                                            on {update}.
                                            </li>
                                            <li>
                                            New LOMRs were effected within
                                            Boulder County, but none were 
                                            effected inside the City of Boulder.
                                            </li>
                                            <li>
                                            FIRM Panels were revised within
                                            Boulder County, but none were 
                                            revised inside the City of Boulder.
                                            </li>
                                        </ul>
                                        </p>
                                        <p>
                                        Since the  Effective Floodplains 
                                        inside the City of Boulder did not 
                                        change, UTIL.Floodplains was not 
                                        updated.
                                        </p>
                                        <p>
                                        Linework and other spatially referenced 
                                        materials for this update can be found 
                                        <a href="{folder}">here</a>, in the 
                                        file geodatabase entitled "{d_string}.gdb".
                                        </p>
                                        <p>
                                        <strong>No further action is required.</strong>
                                        </p>
                                    </body>
                                </html>
                                """.format(update = format_date,
                                           d_string = scrape_date,
                                           folder = dest_folder)
                    else:
                        # Email that County FIRMs were revised, but none in Boulder
                        email = """\
                                <html>
                                    <head></head>
                                    <body>
                                        <p>
                                        <ul type="circle">
                                            <li>
                                            FEMA Effective shapefiles were updated
                                            on {update}.
                                            </li>
                                            <li>
                                            No new LOMRs exist in Boulder County 
                                            for this update.
                                            </li>
                                            <li>
                                            FIRM Panels were revised within
                                            Boulder County, but none were 
                                            revised inside the City of Boulder.
                                            </li>
                                        </ul>
                                        </p>
                                        <p>
                                        Since the  Effective Floodplains 
                                        inside the City of Boulder did not 
                                        change, UTIL.Floodplains was not 
                                        updated.
                                        </p>
                                        <p>
                                        Linework and other spatially referenced 
                                        materials for this update can be found 
                                        <a href="{folder}">here</a>, in the 
                                        file geodatabase entitled "{d_string}.gdb".
                                        </p>
                                        <p>
                                        <strong>No further action is required.</strong>
                                        </p>
                                    </body>
                                </html>
                                """.format(update = format_date,
                                           d_string = scrape_date,
                                           folder = dest_folder)
                else:
                    if t4:
                        # Email that County LOMRs were effected, but none in Boulder
                        email = """\
                                <html>
                                    <head></head>
                                    <body>
                                        <p>
                                        <ul type="circle">
                                            <li>
                                            FEMA Effective shapefiles were updated
                                            on {update}.
                                            </li>
                                            <li>
                                            New LOMRs were effected within
                                            Boulder County, but none were 
                                            effected inside the City of Boulder.
                                            </li>
                                            <li>
                                            No FIRM Panels were revised in
                                            Boulder County for this update.
                                            </li>
                                        </ul>
                                        </p>
                                        <p>
                                        Since the  Effective Floodplains 
                                        inside the City of Boulder did not 
                                        change, UTIL.Floodplains was not 
                                        updated.
                                        </p>
                                        <p>
                                        Linework and other spatially referenced 
                                        materials for this update can be found 
                                        <a href="{folder}">here</a>, in the 
                                        file geodatabase entitled "{d_string}.gdb".
                                        </p>
                                        <p>
                                        <strong>No further action is required.</strong>
                                        </p>
                                    </body>
                                </html>
                                """.format(update = format_date,
                                           d_string = scrape_date,
                                           folder = dest_folder)
                    else:
                        # Email that nothing in County or Boulder has changed.
                        email = """\
                                <html>
                                    <head></head>
                                    <body>
                                        <p>
                                        <ul type="circle">
                                            <li>
                                            FEMA Effective shapefiles were updated
                                            on {update}.
                                            </li>
                                            <li>
                                            No new LOMRs exist in Boulder County 
                                            for this update.
                                            </li>
                                            <li>
                                            No FIRM Panels were revised in
                                            Boulder County for this update.
                                            </li>
                                        </ul>
                                        </p>
                                        <p>
                                        Since the  Effective Floodplains 
                                        inside the Boulder County did not 
                                        change, UTIL.Floodplains was not 
                                        updated.
                                        </p>
                                        <p>
                                        Linework and other spatially referenced 
                                        materials for this update can be found 
                                        <a href="{folder}">here</a>, in the 
                                        file geodatabase entitled "{d_string}.gdb".
                                        </p>
                                        <p>
                                        <strong>No further action is required.</strong>
                                        </p>
                                    </body>
                                </html>
                                """.format(update = format_date,
                                           d_string = scrape_date,
                                           folder = dest_folder)
        if email:
            # raise exception to stop script from running
            raise HaltException("An email notification was sent")
        
    except UnboundLocalError:
        pass
    except HaltException as e:
        # send email notification
        flood_email(email)
        print e.value

"""
*******************************************************************************
"""
def dissolve_to_geom(firm_dict = None, lomr_dict = None):
    """
    Creates a dissolved polygon geometry object from a list of polygons created 
    in the check_revisions function.
    
    :param firm_dict: {dict} Dictionary from check_revisions containing FIRM info
    :param lomr_dict: {dict} Dictionary from check_revisions containing LOMR info
    :return: {arc geometry obj} An arc polygon object
    """
    global dissolve_list
    # aggragate LOMR/FIRM polys and dissolve into an arcpy.Geometry() object
    dissolve_list = []
    checks = [firm_dict, lomr_dict]
    for v in checks:
        # tests if Boulder had any updated FIRM or LOMR geometries
        if v['Boulder']:
            for g in v['Geoms']:
                dissolve_list.append(g)
    
    dissolve = arcpy.Dissolve_management(in_features = dissolve_list,
                                         out_feature_class = arcpy.Geometry())
    
    return dissolve[0]

#"""
#*******************************************************************************
#"""
#def ClipFloodplain(save_dest = None, flood_lyr = None):
#    """
#    Clips FEMA's floodplain feature class to areas inside the city that have 
#    been changed (either through a LOMR process or through a FIRM Panel 
#    Revision).
#    
#    ----
#    
#    INPUTS:
#        save_dest (str):
#            The file path of the destination to save clipped floodplains.
#        
#        flood_lyr (str):
#            The file path to the freshly downloaded FEMA floodplain.
#    """
#    global clip
#    # set workspace
#    env.workspace = save_dest
#    # list all feature classes in that workspace except boulder_panels
#    scratch_fcs = [path.join(save_dest, f) for f in arcpy.ListFeatureClasses() 
#                   if f != 'boulder_panels']
#    
#    # if the save_dest has files inside, delete them all
#    if len(scratch_fcs) > 0:
#        for s in scratch_fcs:
#            arcpy.Delete_management(in_data = s)
#    
#    # clip floodplains to dissolved LOMRs/FIRMs
#    dissolve_list = []
#    checks = {'FIRM': firm_info, 'LOMR': lomr_info}
#    for k,v in checks.iteritems():
#        # tests if Boulder had any updated FIRM or LOMR geometries
#        t1 = v['Boulder']
#        # tests if there are more than one geometry objects in geom list
#        t2 = len(v['Geoms']) > 1
#        # if there are geometries inside Boulder
#        if t1 and t2:
#            # dissolve the LOMRs/FIRMs
#            d_name = 'Boulder' + k + scrape_date
#            dissolve = path.join(save_dest, d_name); dissolve_list.append(dissolve)
#            arcpy.Dissolve_management(in_features = v['Geoms'],
#                                      out_feature_class = dissolve)
#    
#    # dissolve the LOMRs/FIRMs together into a single feature class
#    if len(dissolve_list) > 1:
#        dissolve = path.join(save_dest, 'ClippingGeometry')
#        arcpy.Dissolve_management(in_features = dissolve_list,
#                                  out_feature_class = dissolve)
#    
#    # clip the floodplain to the dissolved LOMRs/FIRMs
#    clip = path.join(save_dest, 'ClippedFloodplains')
#    arcpy.Clip_analysis(in_features = flood_lyr, 
#                        clip_features = dissolve, 
#                        out_feature_class = clip)
#    
#    # return the file path to the clipped floodplains
#    return dissolve, clip
#
#"""
#*******************************************************************************
#"""
#def reformatFEMA(in_table = None):
#    '''
#    Reformats FEMA schema into more useable formats for city
#    purposes. 
#    
#    Specifically, the script identifies 500-, 100-, and
#    Conveyance zones based off of their "FLD_ZONE" and "ZONE_SUBTY". It
#    also combines "FLD_ZONE", "STATIC_BFE", and "DEPTH" fields into
#    more readable "FEMAZONE" delineations.
#    
#    ----
#    
#    INPUTS:
#        in_table (str):
#            File path to the re-projected FEMA flood area feature class.
#
#        fields (list):
#            List of fields to examine and reformat. Defined within
#            the module as "fois" (fields of interest) and made default.
#    '''
#    # define fields to reformat
#    fois = ['FLD_ZONE', 'ZONE_SUBTY', 'FEMAZONE', 'STATIC_BFE', 'DEPTH', 
#            'FLOODPLAIN']
#    
#    # step into the feature class
#    with arcpy.da.UpdateCursor(in_table, fois) as uCurs:
#        for row in uCurs:
#            if 'A' in row[0]: # if the polygon is in 100 yr delin...
#                if row[1] == 'FLOODWAY': # designate conveyance zones
#                    row[2] = row[0]
#                    row[5] = 'Conveyance Zone'
#                else: # designate 100 yr zones
#                    row[5] = '100 Year'
#                    if 'H' in row[0]: # transfer elevations for AH
#                        row[2] = row[0] + str(row[3])[:-2]
#                    elif 'O' in row[0]: # transfer depths for AO
#                        row[2] = row[0] + str(row[4])[:-2]
#                    else:
#                        row[2] = row[0]
#            elif any(f in row[1] for f in ['0.2 PCT', 'LEVEE']): # designate 500 yr
#                row[2] = row[0]
#                row[5] = '500 Year'
#            else: # designate areas with reduced flood risk
#                row[5] = 'Reduced Risk'
#            uCurs.updateRow(row)
#
#    with arcpy.da.UpdateCursor(in_table, 'FLOODPLAIN') as uCurs:
#        for row in uCurs:
#            if row[0] == 'Reduced Risk':
#                uCurs.deleteRow()
#
#"""
#*******************************************************************************
#"""
#def addFieldsFromDict(in_dict = None, table = None):
#    """
#    Adds fields from a dictionary whose key is the name of the field-to-add
#    and whose value is a list of field type and field length. If the field does
#    not require a length, write "None" in place of a number.
#    
#    -----
#    
#    INPUTS:
#        in_dict (dictionary):
#            Dictionary of fields to add. {"FIELDNAME": [field_type, field_length]}.
#            If the field does not require a length, write "None" in place of a 
#            number in the dictionary's value.
#        
#        in_table (str):
#            File path to the re-projected FEMA flood area feature class. The 
#            default is the clipped floodplains from the ClipFloodplain function.
#    """
#    table_fields = [f.name for f in arcpy.ListFields(table)]
#    
#    for key, value in in_dict.iteritems():
#        if key not in table_fields: # if the field does not already exist, add it
#            arcpy.AddField_management(in_table = table,
#                                      field_name = key,
#                                      field_type = value[0],
#                                      field_length = value[1])

"""
*******************************************************************************
"""
def extract_fema_geoms_and_attrs(in_table = None, cutting_geom_obj = None):
    '''
    Extracts delineations and attributes from FEMA's "S_FLD_HAZ_AR" and saves 
    them to a dictionary.
    
    :param in_table: {str} The file path to the re-projected FEMA floodplain fc (S_FLD_HAZ_AR)
    :param cutting_geom_obj: {arc geometry object} The boundary of FIRM/LOMR updates
    :return: {list} A list of dictionaries describing each unique floodplain polygon
                    [{'SHAPE@': <geom obj>, 'FLOODPLAIN': "str", 'FEMAZONE': "str"},...]
    '''
    # define fields to reformat
    fois = ['FLD_ZONE', 'ZONE_SUBTY', 'STATIC_BFE', 'DEPTH', 'SHAPE@']
    
    # create a list of geometries and populate it with calc'd values
    geom_w_attrs = []
    
    # step into the feature class
    with arcpy.da.SearchCursor(in_table, fois) as sCurs:
        for row in sCurs:
            cur_dict = {}
            if row[4].within(cutting_geom_obj):
                cur_dict['SHAPE@'] = row[4]
                if 'A' in row[0]: # if the polygon is in 100 yr delin...
                    if row[1] == 'FLOODWAY': # designate conveyance zones
                        cur_dict['FLOODPLAIN'] = 'Conveyance Zone'
                        cur_dict['FEMAZONE'] = row[0]
                    else: # designate 100 yr zones
                        cur_dict['FLOODPLAIN'] = '100 Year'
                        if 'H' in row[0]: # transfer elevations for AH
                           cur_dict['FEMAZONE'] = row[0] + str(row[2])[:-2]
                        elif 'O' in row[0]: # transfer depths for AO
                            cur_dict['FEMAZONE'] = row[0] + str(row[3])[:-2]
                        else:
                            cur_dict['FEMAZONE'] = row[0]
                elif any(f in row[1] for f in ['0.2 PCT', 'LEVEE']): # designate 500 yr
                    cur_dict['FEMAZONE'] = row[0]
                    cur_dict['FLOODPLAIN'] = '500 Year'
            
            # delete zones with minimal flood hazard
            if len(cur_dict) > 1: geom_w_attrs.append(cur_dict)
    
    return geom_w_attrs

"""
*******************************************************************************
"""
def extract_named_geoms(sde_floodplains = None, where_clause = None, 
                        clipping_geom_obj = None):
    """
    Clips SDE flood delineations to the boundary of FEMA floodplain changes, and 
    then saves the geometry and DRAINAGE name to a list of dictionaries.
    
    :param sde_floodplains: {str} The file path to the UTIL.Floodplains layer
    :param where_clause: {str} The where clause used to isolate polygons of interest
    :param clipping_geom_obj: {arc geom obj} The geometry object representing 
                              the boundaries of the LOMR/FIRM update
    :return: {list} [{"SHAPE@": <Poly obj>, "DRAINAGE": "drain name"},...]
    """
    sde_fields = ['SHAPE@', 'DRAINAGE']
    
    with arcpy.da.SearchCursor(sde_floodplains, sde_fields, where_clause) as sCurs:
        named_geoms = []
        geom = None
        for row in sCurs:
    #        if clipper.contains(row[0].centroid) or row[0].overlaps(clipper):
            geom = row[0].clip(clipping_geom_obj.extent)
            named_geoms.append({'SHAPE@': geom, 'DRAINAGE': str(row[1])})
    
    return named_geoms
            
"""
*******************************************************************************
"""
def transfer_attrs(fema_dict_list = None, sde_dict_list = None):
    """
    Transfers creek names from the current SDE geometries to the FEMA updated 
    geometries.
    
    :param fema_dict_list: {list} A list of dictionaries containing the attribute 
                            info associated with every updated polygon
    :param sde_dict_list: {list} A list of dictionaries containing geometry 
                           objects and their drainage names.
    :return: {none} The function modifies the fema_dict_list input
    """
    for d in fema_dict_list:
        d['ADOPTYR'] = int(scrape_date[:4])
        d['INEFFYR'] = 9999
        d['LIFECYCLE'] = 'Active'
        d['SOURCE'] = 'FEMA'
        # if an SDE geometry contains the centroid of a FEMA geom, transfer the name
        for g in sde_dict_list:
            if g['SHAPE@'].contains(d['SHAPE@'].centroid):
                d['DRAINAGE'] = g['DRAINAGE']
                break   

"""
*******************************************************************************
"""
def create_version_and_db_connection(save_path = None):
    """
    Creates a version called "GISSCR.UTIL_FloodplainEditor" along with a database 
    connection that enables edits through this script
    
    :param save_path: {str} The file path to save the temporary database connection.
    :return: {none} The function modifies arc verions and db connections
    """
    global new_gisscr
    parent = "SDE.DEFAULT"
    version = "UTIL_FloodplainEditor"
    permiss = "PRIVATE"
    
    conn_name = 'new_gisscr'
    v_name = 'GISSCR.{}'.format(version)
    new_gisscr = path.join(save_path, '{}.sde'.format(conn_name))
    
    # Create version (if it already exists, delete and recreate)
    if any(v_name in v for v in arcpy.ListVersions(env.workspace)):
        arcpy.DeleteVersion_management(env.workspace, v_name)
        
    arcpy.CreateVersion_management(in_workspace = env.workspace,
                                   parent_version = parent,
                                   version_name = version,
                                   access_permission = permiss)
    
    # Create DB Connection from version
    if not path.isfile(new_gisscr) and not path.exists(new_gisscr):
        arcpy.CreateDatabaseConnection_management(out_folder_path = save_path,
                                                  out_name = conn_name,
                                                  database_platform = 'ORACLE',
                                                  instance = 'gisprod2',
                                                  account_authentication = 'DATABASE_AUTH',
                                                  username = 'gisscr',
                                                  password = "gKJTZkCYS937",
                                                  version_type = 'TRANSACTIONAL',
                                                  version = v_name)

"""
*******************************************************************************
"""
def edit_floodplain_version(edit_fc_name = None, fields = None, where_clause = None, 
                 comparison_geom = None, insert_geoms = None):
    """
    Performs specific edits on the SDE floodplains layer.
    
        1: Cuts polygons that cross the clipper boundary. This ensures that 
        when new FEMA polygons are dropped in, they don't overlap with existing 
        geometries. This also ensures that polygons tie in properly at confluences.
        
        2: Changes the lifecycle of existing floodplains within the LOMR/FIRM area 
        to "Inactive" 
        
        3: Inserts new FEMA geometries with assoc. attributes
    
    Once this process finishes, the GIS Technician in charge of QAQC should inspect 
    the version manually and make edits.
    
    :param edit_fc_name: {str} The name of the fc to be editted
    :param fields: {list} A list of field names that will be updated
    :param where_clause: {str} A SQL query str used in Update Cursors
    :param comparison_geom: {arc geom obj} The boundary of floodplain updates
    :param insert_geoms: {list} The list of dictionaries containing updated FEMA info
    :return: {none} The function sends an email notifying a user group of next steps.
    """
    try:
        # start edit session
        edit = arcpy.da.Editor(env.workspace)
        edit.startEditing(False, True)
        edit.startOperation()
        
        # open an insert cursor for geometry edits
        iCurs = arcpy.da.InsertCursor(edit_fc_name, fields)
        
        # cut geometries that cross the FIRM/LOMR boundaries
        with arcpy.da.UpdateCursor(edit_fc_name, fields, where_clause) as uCurs:
            for row in uCurs:
                if row[0].overlaps(comparison_geom):
                    row_vals = row[1:] #save all attributes (other than geometry) of the polygon-to-be-cut
                    geoms = row[0].cut(comparison_geom.boundary()) #save the list of clipped geometries
                    uCurs.deleteRow() #delete the geometry that got cut to avoid duplicates
                    for g in geoms: #inspect each new geometry from clipping
                        iRow1 = [g] #create a new row entry with the new geometry
                        iRow1.extend(row_vals) #add attributes to the new geometry
                        if g.area > 0:
                            iCurs.insertRow(iRow1) #add the new row to the layer
        
        # make all existing geometries "Inactive"
        with arcpy.da.UpdateCursor(edit_fc_name, fields, where_clause) as uCurs:
            for row in uCurs:
                if comparison_geom.contains(row[0].centroid):
                    row[6] = 'Inactive'
                    uCurs.updateRow(row)
        
        # add the new FEMA geometries to versioned floodplains
        v_ordered = {i:k for i, k in enumerate(fields)} # order fields correctly
        for entry in insert_geoms:
            iRow2 = [entry[k] for k in v_ordered.itervalues()] 
            iCurs.insertRow(iRow2)
        
        edit.stopOperation()
        edit.stopEditing(True)
        del edit, iCurs
        
        # delete new db connection
        if path.exists(new_gisscr):
            os.remove(new_gisscr)
        
        # send email notifying success
        main_email = """\
        <html>
            <head></head>
            <body>
                <p>
                New shapefiles of FEMA Effective Floodplain delineations have 
                been made available from <a href="{website}">FEMA's Search 
                Portal</a>. These new shapefiles were released on 
                {newdate}. Because of this update, the City's Effective 
                delineations in PROD2 must change.
                </p>
                <p>
                A version called "UTIL_FloodplainEditor" has been created 
                under the GISSCR user, and it has been programmatically 
                edited to reflect these new updates. The updates still need 
                to be QA/QC'd and posted to UTIL_LIVE. 
                </p>
                <p>
                <strong> When versioned edits have been completed and posted, 
                please delete "UTIL_FloodplainEditor". </strong>
                </p>
            </body>
        </html>
        """.format(newdate = format_date, website = root)
            
        flood_email(main_email)
        
    except Exception as e:
        print e.message

























                       





























