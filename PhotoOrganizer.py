## g:\Workspace\python64-37\python.exe G:\+Essam\Pics-WS\PyPhotoScripts\PhotoOrganizer.py -src G:\+Essam\Pics-WS\s10e\Camera -dst G:\+Essam\Pics -bin G:\+Essam\Pics-WS\BIN\S10bin
#------------------------------------------------------

import os, sys, argparse, re, csv, uuid, hashlib, imagehash, shutil, math, json, functools
from pathlib import Path
from datetime import datetime
import piexif
from piexif import ExifIFD, ImageIFD
from piexif._exceptions import InvalidImageDataError
from PIL import Image
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from attr_dict import LazyAttrDict

Image.MAX_IMAGE_PIXELS = None
#-------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser()
parser.add_argument('--src', '-src', help="Path to loop in", type= str , default= None)
parser.add_argument('--dst', '-dst', help="Move to that distention path", type= str, default=None)
parser.add_argument('--bin', '-bin', help="Path to Bin to store duplicate (smaller)", type= str, default=None)
parser.add_argument('--binAtReplaceOnly', '-binAtReplaceOnly', help="Move to bin when replace existing image only, ignore moving the source", action='store_true')
parser.add_argument('--noVideo', '-noVideo', help="Do not process videos, Images only")
parser.add_argument('--videoOnly', '-videoOnly', action='store_true', help="Process Video Only no Images")
parser.add_argument('--replaceDateInName', '-replace', help="Replace date in name instead of rename", action='store_true')
parser.add_argument('--insertExif', '-iexif', help="insert date found in name if it is yyyymmdd_hhmmss", action='store_true')
parser.add_argument('--overwrite', '-overwrite', help="Overwrite files, destination will equal source", action='store_true')
parser.add_argument('--copy', '-copy', action='store_true', help="Copy instead of Move from src to dst")
parser.add_argument('--check', '-check', action='store_true', help="Check existance only NO move NO Copy")
parser.add_argument('--forceRename', '-force', help="force rename from exif Taken Date", action='store_true')
parser.add_argument('--suffix', '-sfx', help="Suffix to add at the end of the new name", type= str , default= '')
parser.add_argument('--hdb', '-hdb', help="Hash DB path", type= str , default= None)

args=parser.parse_args()

if(not args.src and not args.hdb):
    parser.print_help()
    exit(1)

takenDate = None
basePath = args.src
overwrite = args.overwrite
moveToPath = args.dst if (overwrite == False) else args.src
#fcsv = open(basePath[basePath.rindex("\\")+1 if "\\" in basePath else "lol" :] + '.csv', 'wt')
#writer  = csv.writer(fcsv, delimiter=",")
#lst = os.listdir(unicode(fpath, 'utf-8'))
f=None;
count = 0

#-------------------------------------------------------------------------------------------
def renameToDate(path, srcName, dstName, ext, moveToPath = args.dst, binPath = args.bin, NoDate=False, videoProp = None):
    binPath, binPathNoExt, msg, dirPath, oldvidProps = args.bin, None, '', path, None
    try:
        if(args.replaceDateInName == True):
            #print(dstName, srcName, videoProp)
            if(len(re.findall("^[0-9]{8}_[0-9]{6}[+_]*[0-9]*.*$", srcName))>0):
                dstName = re.sub("^[0-9]{8}_[0-9]{6}[+_]*[0-9]*", dstName, srcName)
            else:
                dstName = '{}_{}'.format(dstName, srcName)

        if(srcName == dstName):
            msg = ''#' - Date Found in Name'

        dstNameNoExt = os.path.splitext(dstName)[0]
        srcNameNoExt = os.path.splitext(srcName)[0]

        dstPathNoExt = os.path.join(path, dstNameNoExt)
        dstPath = os.path.join(path, dstNameNoExt + ext)
        srcPath = os.path.join(path, srcNameNoExt + ext)

        if(moveToPath != None):
            dirName = os.path.join(dstName[0:4], dstName[0:4]+'_'+dstName[4:6]) if NoDate == False else 'No_Date'
            dirPath = os.path.join(moveToPath, dirName) if (overwrite == False) else moveToPath
            dstPathNoExt = os.path.join(dirPath, dstNameNoExt)
            dstPath = os.path.join(dirPath, dstNameNoExt + ext)
            if(not os.path.exists(dirPath)):
                os.makedirs(dirPath)

        if(binPath != None):
            binDirName = dstName[0:4]+'_'+dstName[4:6] if NoDate == False else 'No_Date'
            binDirPath = os.path.join(binPath, binDirName)
            binPathNoExt = os.path.join(binDirPath, dstNameNoExt)
            binPath = os.path.join(binDirPath, dstNameNoExt + ext)
            if(not os.path.exists(binDirPath)):
                os.makedirs(binDirPath)

        if True: #(dstPath != srcPath):
            c, forceAddSuffix = 0, False
            BinndedName = binPathNoExt + ' '+ str(uuid.uuid4().hex[:8]) + ext
            BinndedName = None
            sizeSrc = getFileSizeMb(srcPath)

            if(isImage(ext)):
                hashSrc = getHash(srcPath)
                imgs = getExistingImgByHash(hashSrc)

                if(len(imgs)>0): ## If Image already exists
                    try:
                        maxSize = max(img.size for img in imgs)


                        if(maxSize > sizeSrc or maxSize == sizeSrc):
                            BinndedName = move(srcPath, BinndedName, hashSrc) if (args.copy == False) else 'NO ACTION DUE TO COPY'
                            print(f"{os.path.basename(srcPath)} {hashSrc} >> {os.path.basename(BinndedName)} --- Same HASH - Old >= New - BIN/SKIP {msg}")

                        elif(maxSize < sizeSrc):
                            existingWithSameParentDir = [i for i in imgs if os.path.dirname(i.path) == os.path.dirname(dstPath)]
                            existPath = [i.path for i in existingWithSameParentDir if i.size == min(img.size for img in existingWithSameParentDir)]
                            existPath = existPath[0] if(len(existPath)>0) else None

                            if(existPath != None):
                                BinndedName = move(existPath, BinndedName, hashSrc)
                                print(os.path.basename(existPath) + ' >> ' + os.path.basename(BinndedName) + ' --- Same HASH - Old < New - BIN Old'  + msg)
                            else:
                                existPath = "Not in same path"

                            msg += f' - old: {existPath}'
                            dstPath = move(srcPath, dstPath, hashSrc)
                            print(os.path.basename(srcPath) + ' >> ' + os.path.basename(dstPath) + ' --- Same HASH - Old < New - REPLACE Old with NEW'  + msg)

                    except Exception as x:
                        PrintError(x, f'{srcPath} hash {hashSrc}')

                else: ## image not exists, add it
                    dstPath = move(srcPath, dstPath, hashSrc)
                    print(os.path.basename(srcPath) + " >> " + os.path.basename(dstPath) + ' --- MOVED' + msg)

                return ## if image return after finish the above else do the following for video

            ## below loop for VIDEO processing
            while True:
                if(not os.path.exists(dstPath) ):
                    dstPath = move(srcPath, dstPath)
                    c=0
                    print(os.path.basename(srcPath) + " >> " + os.path.basename(dstPath) + ' --- MOVED' + msg)
                    #writer.writerow([os.path.basename(srcPath) + " >> " + os.path.basename(dstPath) + ' --- MOVED' + msg])
                    break

                else: # new name is already exists
                    if(not os.path.exists(dstPath) ):
                        dstPath = [i.path for i in db[hashSrc].imgs if i.size == min(img.size for img in db[hashSrc].imgs)][0]
                        msg += ' - same hash found but Smaller Image'

                    if(c == 0):
                        sizeExisting, hashExisting = getFileSizeMb(dstPath), getHash(dstPath)

                    if(c == 0 and not forceAddSuffix):
                        if(videoProp != None):
                            oldvidProps = getVideoProps(dstPath)

                        BinndedName = binPathNoExt + ' '+ str(uuid.uuid4().hex[:8]) + ext
                        BinndedName = None

                        msg += f' - old: {oldvidProps["encdate"]}'

                        if(oldvidProps == videoProp and sizeExisting == sizeSrc):
                            BinndedName =  move(srcPath, BinndedName) if (args.copy == False) else 'NO ACTION DUE TO COPY'
                            print(os.path.basename(srcPath) + ' >> ' + os.path.basename(BinndedName) + ' --- Same HASH - BIN/SKIP - SAME SIZE' + msg)
                            break # SKIP

                        elif(sizeExisting > sizeSrc and videoProp == None) or \
                        (sizeExisting > sizeSrc and videoProp != None and videoProp['duration'] == oldvidProps['duration']) :
                            BinndedName = move(srcPath, BinndedName) if (args.copy == False) else 'NO ACTION DUE TO COPY'
                            print(os.path.basename(srcPath) + ' >> ' + os.path.basename(BinndedName) + ' --- Same HASH - BIN/SKIP - Old > New'  + msg)
                            break # SKIP

                        elif(sizeExisting < sizeSrc and videoProp == None) or \
                        (sizeExisting < sizeSrc and videoProp != None and videoProp['duration'] == oldvidProps['duration']):
                            BinndedName =  move(dstPath, BinndedName) if (args.copy == False) else 'NO ACTION DUE TO COPY'
                            move(srcPath, dstPath)
                            print(os.path.basename(srcPath) + ' >> ' + os.path.basename(BinndedName) + ' --- Same HASH - BIN - REPLACE OLD with NEW'  + msg)
                            break # REPLACE

                        else:
                            forceAddSuffix = True
                            continue

                    else:
                        c += 1

                        if(dstName == srcName):
                            dstPath = os.path.join(dirPath, dstNameNoExt + str("_%03d" %c) + ('_CHECK' if videoProp != None else '') + ext)
                        else:
                            dstPath = dstPathNoExt + str("_%03d" %c) + ('_CHECK' if videoProp != None else '') + ext
                        continue
        else:
            print(os.path.basename(srcPath) + ' & ' + os.path.basename(dstPath) + ' --- Nothing Changed'  + msg)
    except Exception as e:
        PrintError(e, srcName)
    finally:
        return

#-------------------------------------------------------------------------------------------
def move(src, dst=None, hsh=None, size=None):
    binPath, binIt = args.bin, False
    if(dst == None and binPath != None):#if(binIt == True and binPath != None):
        binIt = True
        name = os.path.basename(src)
        nameNoExt, ext = os.path.splitext(name)

        dst = src
        binDirName = name[0:4]+'_'+name[4:6] #if NoDate == False else 'No_Date'
        binDirPath = os.path.join(binPath, binDirName)
        binPathNoExt = os.path.join(binDirPath, nameNoExt)
        binPath = os.path.join(binDirPath, nameNoExt + ext)
        if(not os.path.exists(binDirPath)):
            os.makedirs(binDirPath)
        dst  = binPath #binPathNoExt + ' '+ str(uuid.uuid4().hex[:8]) + ext

    ext = os.path.splitext(dst)[1]
    sfx = ' {}'.format(args.suffix) if(args.suffix != '') else ''
    esfx = re.findall(sfx, dst)
    sfx = '' if esfx else sfx

    #hshLbl = f" [{hsh}]"
    eh = re.findall('\[[0-9a-f]{16}\]', dst)
    dst = dst.replace(eh[0], f'{sfx}[{hsh}]') if(eh and hsh) else dst.replace(ext, f'{sfx} [{hsh}]{ext}') if (hsh) else dst.replace(ext,'{}{}'.format(sfx, ext))
    dst = dst.replace(ext, f'{str(uuid.uuid4().hex[:8])}{ext}') if(binIt) else dst

    #if('mp4' in ext):
    #    a=0
    #dst = dst.replace(ext,'{}{}'.format(sfx, ext)) if(not esfx) else dst

    #dst = re.sub('\s{2}\[[0-9a-f]{16}\]'+ext+'|'+ext, r' [{}]{}'.format(hsh, ext), dst) if(hsh != None) else dst
    #dst = re.sub('(.*)(\[[0-9a-f]{16}\])*(.*)*('+ext+')', r'\1[{}]\3\4'.format(hsh), dst) if(hsh != None) else dst
    #dst = re.sub('\s{2}\[[0-9a-f]{16}\](.*)'+ext+'|'+ext, r' [{}]\1{}'.format(hsh, ext), dst) if(hsh != None) else dst

    if(args.check):
        return dst
    if(args.copy and not binIt):
        shutil.copy(src, dst)

    elif((args.copy and binIt) or (not args.copy)):
        shutil.move(src, dst)
    return dst
#-------------------------------------------------------------------------------------------
def insertExif(exif, filePath):
    try:
        try:
            exif_bytes = piexif.dump(exif)
        except InvalidImageDataError:
            del exif["1st"]
            exif_bytes = piexif.dump(exif)
        piexif.insert(exif_bytes, filePath)

    except Exception as e:
        #PrintError(e, filePath)
        rs = re.findall("[0-9]+[\s]in[\s][a-zA-Z0-9]+",str(e))

        if(len(rs)>0):
            rs = rs[0].split(' ')

        if(len(rs) == 3):
            del exif[str(rs[2])][int(rs[0])]
            insertExif(exif, filePath)
        else:
            PrintError(e, filePath)
    finally:
        return exif

#-------------------------------------------------------------------------------------------

def getTakenDate(fileRoot, fname, ext):
    filePath = os.path.join(fileRoot, fname)
    takenDate = imageDate = exif = None
    if(ext.lower() not in ['.jpg', '.jpeg']):
        return {'takenDate': takenDate, 'exif': exif}

    rootBaseName = os.path.basename(filePath)
    try:
        exif = piexif.load(filePath)

        #utf16_bytearray = tuple(bytearray("ON: " + re.sub("_[0-9]{11}_o", "", fname), 'utf-16'))
        #exif['0th'][piexif.ImageIFD.XPComment] = utf16_bytearray
        #exif['0th'][piexif.ImageIFD.DocumentName] = "ON: " + re.sub("_[0-9]{11}_o", "", fname)
        #exif['0th'][piexif.ImageIFD.ImageDescription] = rootBaseName
        #exif['Exif'][piexif.ExifIFD.ImageUniqueID] = rootBaseName
        #insertExif(exif, filePath)

        if("Exif" in exif and ExifIFD.DateTimeOriginal in exif["Exif"]):
           takenDate = exif["Exif"][ExifIFD.DateTimeOriginal].decode()
        elif("0th" in exif and ImageIFD.DateTime in exif["0th"]):
            imageDate = exif["0th"][ImageIFD.DateTime].decode()
            if(imageDate != None):
                exif['Exif'][piexif.ExifIFD.DateTimeOriginal] = imageDate
                insertExif(exif, filePath)

        takenDate = takenDate if takenDate != None else imageDate

        if(takenDate != None and args.insertExif):
            renameToDate(fileRoot, fname, getFormattedNameDate(takenDate), ext, moveToPath)

    except Exception as e:
        #raise e
        PrintError(e, fname)
    finally:
        return {'takenDate': takenDate, 'exif': exif}

#-------------------------------------------------------------------------------------------

def getFormattedNameDate(strDate, format ="%Y%m%d%H%M%S", outFormat="%Y%m%d_%H%M%S"):
    return datetime.strptime(strDate.replace('-','').replace('_','').replace(' ','').replace(':',''), format).strftime(outFormat)

#-------------------------------------------------------------------------------------------

def getFormattedExifDate(strDate, format ="%Y%m%d%H%M%S"):
    return datetime.strptime(strDate.replace('-','').replace('_','').replace(' ','').replace(':',''), format).strftime("%Y:%m:%d %H:%M:%S")

#-------------------------------------------------------------------------------------------

def processVideo(root, fname, ext):
    noErr = True

    if(isVideo(ext)):
        vdateName = re.findall("(20[0-9]{6}_[0-9]{6})|([a-zA-Z]*-?20[0-9]{6}-WA[0-9]{4})|(20[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{6})|(20[0-9]{2}-[0-9]{2}-[0-9]{2}[\s][0-9]{2}.[0-9]{2}.[0-9]{2})", fname, re.IGNORECASE)
        vdateName = [a for a in vdateName[0] if len(a) >0][0] if len(vdateName)>0 else None
        #vdateName = vdateName.replace('vid-','').replace('-','').replace('.','').replace(' ','_') if vdateName != None else None

        #if(len(vdateName) == 0):
        try:
            #vdateName = re.sub('[a-zA-Z]*-?(20[0-9]{2})[-]?([0-9]{2})[-]?([0-9]{2})[-]?[_]?[\s]?WA?([0-9]{2})?[.]?([0-9]{2})?[.]?([0-9]{2})?',r'\1\2\3_\4\5\6', vdateName, re.IGNORECASE) if vdateName != None else None
            filePath = os.path.join(root, fname)
            vprop = getVideoProps(filePath)

            #print(vprop)

            encDate = vprop['encdate']
            encDate = encDate if (encDate != None and vdateName != encDate) else vdateName
            renameToDate(root, fname, encDate, ext, videoProp = vprop)
            ##elif vdateName != None: renameToDate(root, fname, vdateName, ext, videoProp = vprop)

        except Exception as e:
            PrintError(e, fname)
            noErr = False
        finally:
            return noErr

#-------------------------------------------------------------------------------------------

def getVideoProps(filePath):

    try:
        MI.Open(filePath)
        encDate = MI.Get(Stream.General, 0, "Encoded_Date") #print(encDate)
        encDate = MI.Get(Stream.General, 0, "File_Modified_Date_Local") if encDate == None or encDate == '' else encDate
        encDate = re.findall("20[0-9]{2}-[0-9]{2}-[0-9]{2}\s[0-9]{2}:[0-9]{2}:[0-9]{2}", encDate, re.IGNORECASE)
        encDate = encDate[0] if len(encDate)>0 else None
        encDate = str(encDate).replace('-','').replace(':','').replace(' ','_') if encDate != None else None
        duration = MI.Get(Stream.Video, 0, "Duration")
        duration = MI.Get(Stream.General, 0, "Duration") if type(duration) == str else duration
        duration = 0 if type(duration) != str else duration
        
        vprop = {
                'bitrate' : MI.Get(Stream.Video, 0, "BitRate"),
                'duration': math.ceil(float(duration)/1000),
                'framerate': MI.Get(Stream.Video, 0, "FrameRate"),
                'width': MI.Get(Stream.Video, 0, "Width"),
                'height': MI.Get(Stream.Video, 0, "Height"),
                'format': MI.Get(Stream.Video, 0, "Format"),
                'bitdepth':MI.Get(Stream.Video, 0, "BitDepth"),
                'encdate': encDate}
    except Exception as ex:
        PrintError(ex, filePath)
    return vprop

#-------------------------------------------------------------------------------------------
def isVideo(ext):
    return ext.lower() in ['.mp4','.m4v','.mov','.3gp','.avi','.mp3','.aac', '.mts', '.vob', '.wmv']
#-------------------------------------------------------------------------------------------
def isImage(ext):
    return ext.lower() in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']
#-------------------------------------------------------------------------------------------
def PrintError(e, fname):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    pyname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(fname + " | " + str(e).replace("\n", ", ") + " | " + pyname +":" + str(exc_tb.tb_lineno) +" | " + str(type(e)))
    #writer.writerow([fname + " | " + str(e).replace("\n", ", ") + " | " + pyname +":" + str(exc_tb.tb_lineno) +" | " + str(type(e))])
#-------------------------------------------------------------------------------------------
def getFileSizeMb(path):
     return round(os.path.getsize(path)/(1024*1024.0), 2)
#-------------------------------------------------------------------------------------------
def getHash(path):
    if(isVideo(os.path.splitext(path)[1])):
        return None
    try:
        return str(imagehash.phash(Image.open(path))).replace("\'",'')
    except Exception as ex:
        PrintError(ex, path)
        return None
#-------------------------------------------------------------------------------------------
def createHashDB():
    if(not args.hdb): return 
    db = {}
    for root, dirs, files in os.walk(args.hdb):
        for file in files:
            filePath = os.path.join(root, file)
            ext = os.path.splitext(filePath)[1]
            if(not isImage(ext)):
                continue
            try:
                ihash = re.findall('\[[0-9a-f]{16}\]',filePath)
                hasHash = bool(ihash)
                ihash = ihash[0] if(ihash) else f"[{getHash(filePath)}]"

                dst = filePath.replace(ihash, f'{ihash}') if(hasHash) else filePath.replace(ext, f' {ihash}{ext}')
                shutil.move(filePath, dst)
                filePath = dst

                ihash = ihash.replace('[','').replace(']','')

                if(ihash != None):
                    img = {'path':filePath, 'size':getFileSizeMb(filePath)}
                    if(ihash in db):
                        if(img['path'] not in db[ihash]['imgs']):
                            db[ihash]['notes'] ='dup'
                            db[ihash]['imgs'].append(img)
                    else:
                        db[ihash]={'imgs':[img]}
            except Exception as e:
                PrintError(e, os.path.basename(filePath))
                continue
    open(os.path.join(args.hdb,'ihdb.json'),'w').write(json.dumps(db, indent=4))
    sys.exit(100)
#-------------------------------------------------------------------------------------------
def getExistingImgByHash(hsh):
    return [LazyAttrDict({'path':str(img), 'size': getFileSizeMb(img)}) for img in Path(args.dst).rglob(f'*[[]{hsh}[]]*')]
#-------------------------------------------------------------------------------------------
def main():

    db = {} #LazyAttrDict(json.loads(open(dbPath).read()))
    createHashDB() if(args.hdb != None) else None

    f=None;
    count, vProp, sameHashFound, hashFound = 0, None, False, 'no'
    hashs = {}

    for root, dirs, files in os.walk(basePath):
        print(f'** DIR: {root} **')
        #writer.writerow(['** DIR: %s **'%root])
        for fname in files:

            fpath = root
            filePath = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1]

            takenDate = imageDate = vProp = None

            if(isVideo(ext)):
                if(args.noVideo):
                    continue
                else:
                    if(processVideo(root, fname, ext) == True):
                        count = count + 1
                        continue
                    #vProp = getVideoProps(filePath)
            if(args.videoOnly):
                continue

            if(not isImage(ext)):
                continue

            count = count + 1
            skip = re.findall("^([0-9]{8}_[0-9]{4,6})(.*)"+ext+"$", fname, re.IGNORECASE) #|^([0-9]{8}_[0-9]{4})(.*)"+ext+"$

            try:
                if(len(skip)>0):

                    dstName = fname
                    if(args.forceRename):
                        EXIF = getTakenDate(root, fname, ext)
                        continue

                    if(args.insertExif):
                        date = re.findall("[0-9]{8}_[0-9]{6}", skip[0][0])[0]
                        EXIF = getTakenDate(root, fname, ext)
                        exif = EXIF['exif']
                        exif['Exif'][piexif.ExifIFD.DateTimeOriginal] = getFormattedExifDate(date)
                        insertExif(exif, filePath)

                    renameToDate(root, fname, dstName, ext, videoProp = vProp)
                    continue

                EXIF = getTakenDate(root, fname, ext)
                takenDate = EXIF['takenDate']
                exif = EXIF['exif']

                if(takenDate != None):
                    renameToDate(fpath, fname, getFormattedNameDate(takenDate), ext)

                elif(takenDate == None):
                    eml = re.findall("20[0-9]{2}-[0-9]{2}-[0-9]{2}[\s]{1}[0-9]{4}", fname, re.IGNORECASE) if '.eml' in fname else []
                    whatsapp = re.findall("IMG-[0-9]{8}-WA[0-9]{4}|^[0-9]{8}_[0-9]{4}", fname, re.IGNORECASE)
                    dateNameHyphen = re.findall("[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{6}", fname, re.IGNORECASE)
                    dateName = re.findall("[IMG_]*20[0-9]{6}_[0-9]{6}", fname)
                    datePattern = re.findall("20[0-9]{6}-[0-9]{6}", fname)
                    ssdatePattern = re.findall("[screenshot_]*20[0-9]{2}-*[0-9]{2}-*[0-9]{2}-*_*t*[\s]*[0-9]{2}-*[\.]*[0-9]{2}-*[\.]*[0-9]{2}", fname)
                    flickrPattern = re.findall("_[0-9]{11}_o", fname)
                    fbPattern = re.findall("fb_img_[0-9]{10}", fname)
                    newDocPattern = re.findall("new-doc-20[0-9]{2}-[0-9]{2}-[0-9]{2}", fname)


                    if(len(eml) > 0):
                        date = eml[0]
                        print(eml)
                        renameToDate(fpath, fname, getFormattedNameDate(date, "%Y%m%d%H%M", "%Y%m%d_%H%M") +' - ' + fname[0:-22], ext) #datetime.strptime(date, "%Y%m%d").strftime("%Y%m%d_%H%M%S"), ext)

                        continue
                    if(len(whatsapp) > 0):
                        date,sq = re.findall("[0-9]{8}-WA[0-9]{4}", str(whatsapp[0].upper()))[0].upper().split('-WA')
                        if(exif != None):
                            exif['Exif'][piexif.ExifIFD.DateTimeOriginal] = getFormattedExifDate(date, "%Y%m%d") #datetime.strptime(date, "%Y%m%d").strftime("%Y:%m:%d %H:%M:%S")
                            insertExif(exif, filePath)
                        renameToDate(fpath, fname, getFormattedNameDate(date, "%Y%m%d", "%Y%m%d_")+ sq, ext) #datetime.strptime(date, "%Y%m%d").strftime("%Y%m%d_%H%M%S"), ext)

                        continue

                    elif(len(dateNameHyphen) > 0):
                        date = dateNameHyphen[0]
                        if(exif != None):
                            exif['Exif'][piexif.ExifIFD.DateTimeOriginal] = getFormattedExifDate(date)#datetime.strptime(date, "%Y-%m-%d-%H%M%S").strftime("%Y:%m:%d %H:%M:%S")
                            insertExif(exif, filePath)
                        renameToDate(fpath, fname, getFormattedNameDate(date), ext)#datetime.strptime(date, "%Y-%m-%d-%H%M%S").strftime("%Y%m%d_%H%M%S"), ext)
                        continue

                    elif(len(dateName) > 0):
                        date = re.findall("20[0-9]{6}_[0-9]{6}", dateName[0])[0] #dateName[0].replace("IMG_",'')
                        if(takenDate == None and exif != None):
                            exif['Exif'][piexif.ExifIFD.DateTimeOriginal] = getFormattedExifDate(date) #datetime.strptime(date, "%Y%m%d_%H%M%S").strftime("%Y:%m:%d %H:%M:%S")
                            insertExif(exif, filePath)
                        renameToDate(fpath, fname, date, ext)
                        continue

                    elif(len(datePattern)>0):
                        date = datePattern[0]
                        if(takenDate == None and exif != None):
                            exif['Exif'][piexif.ExifIFD.DateTimeOriginal] = getFormattedExifDate(date) #datetime.strptime(date, "%Y%m%d-%H%M%S").strftime("%Y:%m:%d %H:%M:%S")
                            insertExif(exif, filePath)
                        renameToDate(fpath, fname, date.replace('-','_'), ext)
                        continue

                    elif(len(ssdatePattern)>0):
                        ssdatePattern = re.findall("20[0-9]{2}-*[0-9]{2}-*[0-9]{2}-*_*t*[\s]*[0-9]{2}-*[\.]*[0-9]{2}-*[\.]*[0-9]{2}", ssdatePattern[0])[0]
                        ssdatePattern = ssdatePattern.replace('t','_').replace('-','').replace(' ','_').replace('.','')
                        if(takenDate == None and exif != None):
                            exif['Exif'][piexif.ExifIFD.DateTimeOriginal] = getFormattedExifDate(ssdatePattern) #datetime.strptime(ssdatePattern.replace('-','').replace('_',''), "%Y%m%d%H%M%S").strftime("%Y:%m:%d %H:%M:%S")
                            insertExif(exif, filePath)
                        renameToDate(fpath, fname, getFormattedNameDate(ssdatePattern), ext)
                        continue

                    elif(len(fbPattern)>0):
                        fbPattern = re.sub("fb_img_", "", fbPattern[0])
                        dt = datetime.fromtimestamp(int(fbPattern)).strftime("%Y%m%d%H%M%S")
                        if(takenDate == None and exif != None):
                            exif['Exif'][piexif.ExifIFD.DateTimeOriginal] = getFormattedExifDate(dt)
                            insertExif(exif, filePath)
                        renameToDate(fpath, fname, getFormattedNameDate(dt), ext)
                        continue


                    elif(len(newDocPattern)>0):
                        newDocPattern = re.sub("new-doc-", "", newDocPattern[0])
                        if(takenDate == None and exif != None):
                            exif['Exif'][piexif.ExifIFD.DateTimeOriginal] = getFormattedExifDate(newDocPattern, "%Y%m%d")
                            insertExif(exif, filePath)
                        renameToDate(fpath, fname, getFormattedNameDate(newDocPattern, "%Y%m%d"), ext)
                        continue

                    elif(len(flickrPattern)>0):
                        renameToDate(fpath, fname, fname.replace(flickrPattern[0] + ext, ''), ext, NoDate=True)
                        continue

                    else:
                        renameToDate(fpath, fname, fname, ext, NoDate=True)

            except Exception as e:
                PrintError(e, fname)
                takenDate = None

            finally:
                f.close() if f != None else ''

    print(str(count))
#-------------------------------------------------------------------------------------------
if(__name__ == '__main__'):

    try:
        #os.chdir("C:\\Program Files\\MediaInfo")
        from MediaInfoDLL3 import MediaInfo, Stream
        MI = MediaInfo()
    except Exception as e:
        print (e)
    finally:
        try:
            main()
        except Exception as me:
            PrintError(me,'')

#-------------------------------------------------------------------------------
class Decorators:
    #-------------------------------------------------------------------------------------------------------------------
    @classmethod
    def tryIt(self, continueExcution=True):
        def decorator_repeat(func):
            @functools.wraps(func)
            def wrapper_decorator(self, *args, **kwargs):
                value = None
                try:
                    value = func(self, *args, **kwargs)
                    return value
                except Exception as ex:
                    self.log(0,'ERROR: {}', self.formatError(ex, func.__name__))
                    return continueExcution if (continueExcution == True) else sys.exit(0)
            return wrapper_decorator
        return decorator_repeat
#-----------------------------------------------------------------------------------------------------------------------