@echo off
title Sort NINA images

cmd /k "cd /d D:\NINA_Local_Ingest && conda activate nina && python NINA_sort_Advanced_for_HFR_RMS_Stars.py && exit"
