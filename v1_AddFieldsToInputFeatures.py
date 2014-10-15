######################################################################
## Author:  Chieko Maene
## Date:    April 5, 2011
## Version: ArcGIS 10.0
## Purpose: This script will find 1st order and 2nd order adjacent neighbors for a polygon
##          features.
## Acknowledgment: The codes I looked at are by:
##          Miles Hitchen (greatest, in VB, found in Forums.Esri.Com),
##          Esri (CalcFields.py in ArcGIS Resource Center 10)
##          Esri (SelectByNeighbours.py in ArcGIS Resource Center 10)
## Note:    I cannot make an elegant code yet. My codes tend to be "spaghetti codes".
##          I also tend to keep codes even if not necessary for fear of messing it up. Be aware. 
## Input:   There are four input parameters:
##               1) Browse to a polygon feature class
##               2) Select a field that represents feature/polygon IDs
##               3) Create a name for a field to store 1st order neighbor polygons
##               4) Create a name for a field to store 2nd order neighbor polygons
######################################################################

import arcpy
import sys
import traceback

try:
    sWksp = arcpy.env.scratchWorkspace = "in_memory"
    arcpy.env.overwriteOutput = True
    # Get the input feature layer
    inputFC = arcpy.GetParameterAsText(0)
    idfieldName = arcpy.GetParameterAsText(1)
    newField = arcpy.GetParameterAsText(2)
    newField2 = arcpy.GetParameterAsText(3)
        
    # Make a feature layer for SelectByLocation
    lyrFC = arcpy.MakeFeatureLayer_management(inputFC)
    
    # Make sure the input layer is a polygon shape type
    inDesc = arcpy.Describe(lyrFC)
    if inDesc.shapeType <> "Polygon":
        arcpy.AddError("\nInput shape type has to be polygons.")
        sys.exit("Input is a wrong shape type.\n")
    arcpy.env.workspace = inDesc.path
    
    # Add "user-named" new fields to store lists of 1st order neighbor polygon IDs 
    if newField not in arcpy.ListFields(lyrFC):
        arcpy.AddField_management(lyrFC, newField, "TEXT")
    # Add "user-named" new fields to store lists of 2nf order neighbor polygon IDs if requested 
    if newField2 <> "":
        if newField2 not in arcpy.ListFields(lyrFC):
            arcpy.AddField_management(lyrFC, newField2, "TEXT")

    updCursor = arcpy.UpdateCursor(lyrFC)
    updRow = updCursor.next()

    while updRow:
        # This is a temporary layer for SelectByLocation - i.e. to capture 1st neighbor polygons
        arcpy.MakeFeatureLayer_management(lyrFC, "allFC")
        # Next feature layer will hold the current row/updRow only - will be used to find both 1st and 2nd order neighbors
        # A bit awkward.. Must be a better way to do this part but I don't know it yet. I tried updRow.shape but didn't work well 
        # AddFieldDelimiters supposedly helps creating a proper SQL statement no matter what input format type (shp,gdb,etc) we use
        delimitedField = arcpy.AddFieldDelimiters(lyrFC, inDesc.OIDFieldName)
        rowOID = updRow.getValue(inDesc.OIDFieldName)
        sqlExp = delimitedField + " = " + str(rowOID)
        arcpy.MakeFeatureLayer_management(lyrFC, "rowFC", sqlExp)

        # Select 1st order neighboring polygons - ones that touch a boundary of the current row
        arcpy.SelectLayerByLocation_management("allFC", "BOUNDARY_TOUCHES", "rowFC", "", "NEW_SELECTION")

        # Check if selection was made.. make a list of feature "user-selected" ids only if neighboring polygons are found
        inDesc1 = arcpy.Describe("allFC")
        if inDesc1.FIDSet <> "":
            neighborList = ";"
            idField = ""
            srcCursor = arcpy.SearchCursor("allFC")
            srcRow = srcCursor.next()
            while srcRow:
                # Get the "user-selected" id value of the current selected row and store as string
                idField = str(getattr(srcRow, idfieldName))
                # get FID of the current selected row
                OIDfield = getattr(srcRow, inDesc1.OIDFieldName)
                # Store the "user-selected id" values as long as FID of the selected is not the same as the current feature/row's 
                if OIDfield <> rowOID:
                    neighborList = neighborList + idField + ";"
                srcRow = srcCursor.next()
            # Clean up the list by getting rid of extra ; 
            if neighborList == ";":
                neighborList = ""
            else:
                neighborList = neighborList[1:len(neighborList)-1]
                # python native way: setattr(updRow, newField, neighborList)
            updRow.setValue(newField, neighborList)

            if newField2 <> "":
                # This is a temporary layer for SelectByLocation - i.e. to capture 2nd neighbor polygons
                arcpy.MakeFeatureLayer_management(lyrFC, "allFC2")
                # Now we will find 2nd order neighboring polygons.
                # Select polygons that touch the current selections/1st order neighbors
                arcpy.SelectLayerByLocation_management("allFC2", "BOUNDARY_TOUCHES", "allFC", "", "NEW_SELECTION")
                # subtract the 1st order neighboring polygons away..
                arcpy.SelectLayerByLocation_management("allFC2", "BOUNDARY_TOUCHES", "rowFC", "", "REMOVE_FROM_SELECTION")

                # Check if 2nd selection was made.. make a list of feature "user-selected" ids only if neighboring polygons are found         
                inDesc2 = arcpy.Describe("allFC2")
                if inDesc2.FIDSet <> "":
                    neighborList2 = ";"
                    idField2 = ""
                    srcCursor2 = arcpy.SearchCursor("allFC2")
                    srcRow2 = srcCursor2.next()
                    while srcRow2:
                        # Get the "user-selected" id value of the current selected row and store as string
                        idField2 = str(getattr(srcRow2, idfieldName))
                        # Get FID of the current selected row  
                        OIDfield2 = getattr(srcRow2, inDesc2.OIDFieldName)
                        # Store the "user-selected id" values as long as FID of the selected is not the same as the current feature/row's
                        if OIDfield2 <> rowOID:
                            neighborList2 = neighborList2 + idField2 + ";"
                        srcRow2 = srcCursor2.next()
                    # Clean up the list by getting rid of extra ; 
                    if neighborList2 == ";":
                        neighborList2 = ""
                    else:
                        neighborList2 = neighborList2[1:len(neighborList2)-1]
                    # Set value of the new fields (neighbors & neighbors2) with the list values
                    # python native way: setattr(updRow, newField2, neighborList2)
                    updRow.setValue(newField2, neighborList2)
            updCursor.updateRow(updRow)
        updRow = updCursor.next()

    # Clean up cursors and variables to avoid data locks
    del updCursor, updRow, srcCursor, srcRow
    if newField2 <> "":
        del srcCursor2, srcRow2
##    del curFID, sqlExp, inputFC, idfieldName
##    del inDesc, inDesc2, inDesc3, newField, idField, idField2, FIDfield, FIDfield2
##    del newField2, neighborList, neighborList2

    # Clean up temporary feature layers used to create selections
##    arcpy.DeleteFeatures_management("allFC")
##    arcpy.DeleteFeatures_management("rowFC")
##    arcpy.DeleteFeatures_management("allFC2")

except:              
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]
    pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n    " + \
            str(sys.exc_type)+ ": " + str(sys.exc_value) + "\n"
    arcpy.AddError(pymsg)
    
    msgs = "GP ERRORS:\n" + arcpy.GetMessages(2) + "\n"
    arcpy.AddError(msgs)