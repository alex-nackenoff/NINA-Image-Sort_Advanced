import os
from pathlib import Path
import shutil
import sys
from io import StringIO
import pandas as pd
#comment out this if not using discord alert
from discordwebhook import Discord

#insert discord webhook url below inside quotes, or comment out if not using discord alert 
discord = Discord(url="") # url for your personal discord bot for alerts
calibration = ["FLAT", "DARK", "DARKFLAT", "BIAS", "Snapshot", "FlatWizard"]

local_path = "D:/NINA_Local_Ingest/" # format is "C:/Folder/" with quotes and forward slash. Needs to match NINA save directory
remote_path = "Z:/Pictures/Astro/NINA_Ingest/" # leave empty with quotes if not using robocopy

all_path = [local_path, remote_path]
all_valid_paths = []
for real in all_path:
     if os.path.exists(real):
        all_valid_paths.append(real) # only runs script in directories that are accessible, ie won't attempt to run on remote robocopy folder if shooting in remote [off the grid] location


for valid in all_valid_paths:
    
    os.chdir(valid)
 
    all_subdirs = [d for d in os.listdir('.') if os.path.isdir(d)]
    latest_subdir = max(all_subdirs, key=os.path.getmtime) # only runs on most recently edited folder, which should be current project (day)
    os.chdir(latest_subdir) # changes to most recently changed folder, ie. new images
    sys.stdout = open('Unfit_Lights_logfile.txt', 'w') # creates log of print outputs

    folders = [f for f in os.listdir() if os.path.isdir(f) and f not in calibration]

    for folder in folders:
        a = StringIO()   
        os.chdir(folder)
        os.chdir("LIGHT")
        sort_folder = "unfit"
        isExist = os.path.exists(sort_folder)
        if not isExist:
            os.makedirs(sort_folder)
            print("Created " + sort_folder + " Folder in " + os.getcwd())
        else:
            print(sort_folder + " Folder Already Exists!")

        images = [f for f in os.listdir() if '.fits' in f.lower()]

        if not images: # graceful exit if target folder exists but no successful subframes were captured in NINA (eg. clouds)
            print ("No Images to Sort")
        else:
            df1 = pd.read_csv('ImageMetaData.csv')

            # HFR Cutoff
            mean_hfr=df1['HFR'].mean()
            median_hfr=df1['HFR'].median()
            stdev_hfr=df1['HFR'].std()
            hfr_cutoff=median_hfr*(1.15) # 15% above median HFR cutoff, arbitrary, modify for your needs 
            hfr_cut=df1.loc[((df1['HFR']>hfr_cutoff) | (df1['HFR']<0.1), 'HFR')] # reject if above HFR cutoff OR HFR = 0 (no stars)
            sorted_4_hfr=len(hfr_cut) # counter for reporting

            # Star Cutoff
            star_cutoff=df1['DetectedStars'].median()*(0.5) # 50% below median star cutoff, arbitrary
            star_cut=df1.loc[((df1['DetectedStars']<star_cutoff, 'DetectedStars'))]
            sorted_4_stars=len(star_cut)

            # Guiding Cutoff
            guiding_cutoff=2.2 # maximum pixel scale in arcseconds per pixel, modify for your needs
            guide_cut=df1.loc[((df1['GuidingRMSArcSec']>guiding_cutoff, 'GuidingRMSArcSec'))]
            sorted_4_guiding=len(guide_cut)

            # Sort
            result=df1.loc[((df1['HFR']>hfr_cutoff) | (df1['HFR']<0.1) | (df1['DetectedStars']<star_cutoff) | (df1['GuidingRMSArcSec']>guiding_cutoff),"FilePath")] # reject if satisfies any condition (OR conditions)
            sort_files = [file for file in result]
            
            for drop in sort_files:
                bad_image=(os.path.basename(drop)) # trims full path to just 'file.fits' so filename can be modified in either local or remote directories
                if os.path.isfile(bad_image): # checks if file exists to be moved (if already moved eg)
                    new_path = 'unfit/' + bad_image
                    shutil.move(bad_image, new_path) # moves bad images to unfit directory
                            
            #Stats
            total_images=len(df1['HFR']) # just to grab total number of images, HFR column is easy
            total_cut_images=len(sort_files)
            exposure=df1['Duration'][0] # to calculate usable imaging time
            sort_cut_percent=f"{total_cut_images/total_images:.0%}" # % of subexposures rejected
            remain=(total_images-total_cut_images)*exposure/60/60 # usable imaging time
            usable_imaging="%.2fh" % remain #usable imaging time
                
        os.chdir("..")
        os.chdir("..")
        
        test1 = "Moved " + str(sorted_4_stars) + " files due to stars"
        test2 = "Moved " + str(sorted_4_hfr) + " files due to HFR"
        test3 = "Moved " + str(sorted_4_guiding) + " files due to Guiding"
            
        a.write("Analyzing " + str(folder) +"......"+ "\n    " + "Moved " + str(total_cut_images) + " ("+ sort_cut_percent +")" + " total files")
        a.write("\n   Total Usable Images: " + str(usable_imaging))
        if sorted_4_stars != 0:
            a.write("\n    " + test1)
        if sorted_4_hfr != 0:
            a.write("\n    " + test2)
        if sorted_4_hfr != 0:
            a.write("\n    " + test3)
        print(a.getvalue())
        # comment out below if you don't want Discord alerts
        if valid == local_path:  # only runs discord alert once per locale (avoid duplicate)
            discord.post(content=(a.getvalue()))

