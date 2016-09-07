#!/usr/bin/python
from __future__ import print_function
def warning(*objs):
    print(time.strftime("%H:%M:%S Error:", time.localtime()), *objs, file=sys.stderr)
def information(*objs):
    print(time.strftime("%H:%M:%S", time.localtime()), *objs, file=sys.stdout)

# import modules
import sys
import os
import time
import inspect
import getopt
import yaml
import traceback
import fnmatch
import math
import subprocess as sp
import numpy as np
from freetype import *
#from PIL import Image, ImageFont, ImageDraw, ImageMath

# user modules
# realpath() will make your script run, even if you symlink it
cmd_folder = os.path.realpath(os.path.abspath(
                              os.path.split(inspect.getfile(inspect.currentframe()))[0]))
if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)

# This makes python look for modules in ./external_lib
cmd_subfolder = os.path.realpath(os.path.abspath(
                                 os.path.join(os.path.split(inspect.getfile(
                                 inspect.currentframe()))[0], "external_lib")))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)

import tifffile as tiff

### functions ##################################################################
def make_label(text, face, size=12, angle=0):
    '''Uses freetype to make a time label.

    Parameters:
    -----------
    text : string
        Text to be displayed
    filename : string
        Path to a font
    size : int
        Font size in 1/64th points
    angle : float
        Text angle in degrees
    '''
    face.set_char_size( size*64 )
    angle = (angle/180.0)*math.pi
    matrix = FT_Matrix( (int)( math.cos( angle ) * 0x10000 ),
                         (int)(-math.sin( angle ) * 0x10000 ),
                         (int)( math.sin( angle ) * 0x10000 ),
                         (int)( math.cos( angle ) * 0x10000 ))
    flags = FT_LOAD_RENDER
    pen = FT_Vector(0,0)
    FT_Set_Transform( face._FT_Face, byref(matrix), byref(pen) )
    previous = 0
    xmin, xmax = 0, 0
    ymin, ymax = 0, 0
    for c in text:
        face.load_char(c, flags)
        kerning = face.get_kerning(previous, c)
        previous = c
        bitmap = face.glyph.bitmap
        pitch  = face.glyph.bitmap.pitch
        width  = face.glyph.bitmap.width
        rows   = face.glyph.bitmap.rows
        top    = face.glyph.bitmap_top
        left   = face.glyph.bitmap_left
        pen.x += kerning.x
        x0 = (pen.x >> 6) + left
        x1 = x0 + width
        y0 = (pen.y >> 6) - (rows - top)
        y1 = y0 + rows
        xmin, xmax = min(xmin, x0),  max(xmax, x1)
        ymin, ymax = min(ymin, y0), max(ymax, y1)
        pen.x += face.glyph.advance.x
        pen.y += face.glyph.advance.y

    L = np.zeros((ymax-ymin, xmax-xmin),dtype=np.ubyte)
    previous = 0
    pen.x, pen.y = 0, 0
    for c in text:
        face.load_char(c, flags)
        kerning = face.get_kerning(previous, c)
        previous = c
        bitmap = face.glyph.bitmap
        pitch  = face.glyph.bitmap.pitch
        width  = face.glyph.bitmap.width
        rows   = face.glyph.bitmap.rows
        top    = face.glyph.bitmap_top
        left   = face.glyph.bitmap_left
        pen.x += kerning.x
        x = (pen.x >> 6) - xmin + left
        y = (pen.y >> 6) - ymin - (rows - top)
        data = []
        for j in range(rows):
            data.extend(bitmap.buffer[j*pitch:j*pitch+width])
        if len(data):
            Z = np.array(data,dtype=np.ubyte).reshape(rows, width)
            L[y:y+rows,x:x+width] |= Z[::-1,::1]
        pen.x += face.glyph.advance.x
        pen.y += face.glyph.advance.y

    return L

def find_img_min_max(image_names, tifdir):
    '''find_img_max_min returns the average minimum and average maximum
    intensity for a set of tiff images.

    Parameters
    ----------
    image_names : list
        list of image names (string)
    tifdir : string
        path prefix to where the tiff images are

    Returns
    -------
    avg_min : float
        average minimum intensity value
    avg_max : float
        average maximum intensity value
    '''
    min_list = []
    max_list = []
    for image_name in image_names:
        image = tiff.imread(tifdir + image_name)
        min_list.append(np.min(image))
        max_list.append(np.max(image))
    avg_min = np.mean(min_list)
    avg_max = np.min(max_list)
    return avg_min, avg_max

### main #######################################################################
if __name__ == "__main__":
    '''You must have ffmpeg installed, which you can get using homebrew:
    https://trac.ffmpeg.org/wiki/CompilationGuide/MacOSX

    By Steven
    Edited 20151128 jt
    Edited 20160830 jt
    '''

    # hard parameters
    FFMPEG_BIN = "/usr/local/bin/ffmpeg" # location where FFMPEG is installed
    fontface = Face("/Library/Fonts/Andale Mono.ttf")

    # soft defaults, overridden by command line parameters if specified
    param_file = ""
    specify_fovs = []

    # switches
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:o:")
    except getopt.GetoptError:
        print('No arguments detected (-f -o).')
    for opt, arg in opts:
        if opt == '-f':
            param_file = arg
        if opt == '-o':
            arg.replace(" ", "")
            [specify_fovs.append(int(argsplit)) for argsplit in arg.split(",")]

    # Load the project parameters file into a dictionary named p
    if len(param_file) == 0:
        raise ValueError("A parameter file must be specified (-f <filename>).")
    information('Loading experiment parameters...')
    with open(param_file) as pfile:
        p = yaml.load(pfile)

    # path to tiff files as a string.
    tifdir = p['experiment_directory'] + p['image_directory']

    # start the movie making
    try:
        for fov in range(1, p['num_fovs']+1): # for every FOV

            # skip FOVs as specified above
            if len(specify_fovs) > 0 and not (fov + 1) in specify_fovs:
                continue
            if start_fov > -1 and fov + 1 < start_fov:
                continue

            # grab the images for this fov
            images = fnmatch.filter(os.listdir(tifdir), p['file_prefix'] + "t*xy%03dc*.tif" % (fov))
            if len(images) == 0:
                raise ValueError("No images found to export for fov %d." % fov)
            information("Found %d files to export." % len(images))

            # get min max pixel intensity for scaling the data
            imin = {}
            imax = {}
            imin['phase'], imax['phase'] = find_img_min_max(images[::100], tifdir)

            # use first image to set size of frame
            image = tiff.imread(tifdir + images[0])
            if image.shape[0] < 10:
                image = image[0] # get phase plane
            size_x, size_y = image.shape[1], image.shape[0] # does not worked for stacked tiff

            # set command to give to ffmpeg
            command = [FFMPEG_BIN,
                    '-y', # (optional) overwrite output file if it exists
                    '-f', 'rawvideo',
                    '-vcodec','rawvideo',
                    '-s', '%dx%d' % (size_x, size_y), # size of one frame
                    '-pix_fmt', 'rgb48le',
                    '-r', '%d' % p['fps'], # frames per second
                    '-i', '-', # The imput comes from a pipe
                    '-an', # Tells FFMPEG not to expect any audio
                    # options for the h264 codec
                    '-vcodec', 'h264',
                    '-pix_fmt', 'yuv420p',

                    # options for mpeg4 codec
                    #'-vcodec', 'mpeg4',
                    #'-qscale:v', '4', # set quality scale from 1 (high) to 31 (low)
                    #'-b:v', '1024k', # set output bitrate
                    #'-vf', 'scale=iw*0.5:ih*0.5', # rescale output
                    #'-bufsize', '300k',

                    # set the movie name
                    p['movie_directory'] + p['file_prefix'] + '%03d.mp4' % fov]

            pipe = sp.Popen(command, stdin=sp.PIPE)

            # display a frame and send it to write
            for n, i in enumerate(images):
                # skip images not specified by param file.
                if n < p['image_start'] or n > p['image_end']:
                    continue

                image = tiff.imread(tifdir + i) # get the image

                if image.shape[0] < 10:
                    image = image[0] # get phase plane

                # process phase image
                phase = image.astype('float64')
                # normalize
                phase -= imin['phase']
                phase[phase < 0] = 0
                phase /= (imax['phase'] - imin['phase'])
                phase[phase > 1] = 1
                # three color stack
                image = np.dstack((phase, phase, phase))

                # put in time stamp
                seconds = float(int(i.split(p['file_prefix'] + "t")[1].split("xy")[0]) *
                                p['seconds_per_time_index'])
                mins = seconds / 60
                hours = mins / 60
                timedata = "%dhrs %02dmin" % (hours, mins % 60)
                r_timestamp = np.fliplr(make_label(timedata, fontface, size=48,
                                                   angle=180)).astype('float64')
                r_timestamp = np.pad(r_timestamp, ((size_y - 10 - r_timestamp.shape[0], 10),
                                                   (size_x - 10 - r_timestamp.shape[1], 10)),
                                                   mode = 'constant')
                r_timestamp /= 255.0
                r_timestamp = np.dstack((r_timestamp, r_timestamp, r_timestamp))

                image = 1 - ((1 - image) * (1 - r_timestamp))

                # shoot the image to the ffmpeg subprocess
                pipe.stdin.write((image * 65535).astype('uint16').tostring())
            pipe.stdin.close()
        except:
            warning("Error making .mp4 for %d." %fov)
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])
            print(traceback.print_tb(sys.exc_info()[2]))
