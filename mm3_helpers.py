#!/usr/bin/python
from __future__ import print_function
def warning(*objs):
    print(time.strftime("%H:%M:%S mm3_helpers:", time.localtime()), *objs, file=sys.stderr)
def information(*objs):
    print(time.strftime("%H:%M:%S mm3_helpers:", time.localtime()), *objs, file=sys.stdout)

# import modules
import sys
import os
import time
import inspect
import yaml
try:
    import cPickle as pickle
except:
    import pickle
import numpy as np

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



### functions ###########################################################
# load the parameters file into a global dictionary for this module
def init_mm3_helpers(param_file_path):
    # load all the parameters into a global dictionary
    global params
    with open(param_file_path, 'r') as param_file:
        params = yaml.safe_load(param_file)
    return

### functions about loading files
# loading the channel id of cell containing peaks
def load_cell_peaks(fov_id):
    '''Returns and array of the cell peaks from the spec file for a given fov number'''
    exp_dir = params['experiment_directory']
    ana_dir = params['analysis_directory']
    if not os.path.exists(exp_dir + ana_dir + 'specs/specs_%03d.pkl' % fov_id):
        warning("Spec file missing for " + fov_id)
        return -1
    else:
        with open(exp_dir + ana_dir + 'specs/specs_%03d.pkl' % fov_id, 'rb') as pkl_file:
            user_picks = pickle.load(pkl_file) # tuple = (drop_peaks, cell_peaks, bgrd_peaks)
    # get the cell-containing peaks
    cell_peaks = user_picks[1]
    cell_peaks = np.array(cell_peaks) # it is currently just a list of ints
    return cell_peaks

# load empty tif for an fov_id (empty for background subtraction)
def load_empty_tif(fov_id):
    exp_dir = params['experiment_directory']
    ana_dir = params['analysis_directory']
    if not os.path.exists(exp_dir + ana_dir + "empties/fov_%03d_emptymean.tif" % fov_id):
        warning("Empty mean .tif file missing for " + fov_id)
        return -1
    else:
        empty_mean = tiff.imread(exp_dir + ana_dir + "empties/fov_%03d_emptymean.tif" % fov_id)
    return empty_mean


# get params is the major function which processes raw TIFF images
def get_tif_params(image_filename, find_channels=True):
    '''This is a damn important function for getting the information
    out of an image. It loads a tiff file, pulls out the image data, and the metadata,
    including the location of the channels if flagged.

    it returns a dictionary like this for each image:

    { 'filename': image_filename,
             'metadata': image_metadata,
             'image_size' : image_size, # [image.shape[0], image.shape[1]]
             'channels': cp_dict,
             'analyze_success': True,
             'fov': -1, # fov (zero indexed)
             'sent_to_write': False,
             'write_success': False}

    Called by
    mm3_Compile.py __main__

    Calls
    mm3.extract_metadata
    mm3.find_channels
    '''
    unpaused.wait()
    try:
        # open up file and get metadata
        try:
            with tiff.TiffFile(image_filename) as tif:
                image_data = tif.asarray()
                image_metadata = extract_metadata(tif)
        except:
            time.sleep(2)
            with tiff.TiffFile(image_filename) as tif:
                image_data = tif.asarray()
                image_metadata = extract_metadata(tif)

        # make the image 3d and crop the top & bottom per the image_vertical_crop parameter
        if len(image_data.shape) == 2:
            image_data = np.expand_dims(image_data, 0)
        if image_vertical_crop >= 0:
            image_data = image_data[:,image_vertical_crop:image_data.shape[1]-image_vertical_crop,:]
        else:
            padsize = abs(image_vertical_crop)
            image_data = np.pad(image_data, ((0,0), (padsize, padsize), (0,0)), mode='edge')

        # fix the image orientation and get the number of planes
        image_data = fix_orientation_perfov(image_data, image_filename)
        image_planes = image_data.shape[0]

        # if the image data has more than 1 plane restrict image_data to just the first
        if len(image_data.shape) > 2:
            ph_index = np.argmax([np.mean(image_data[ci]) for ci in range(image_data.shape[0])])
            image_data = image_data[ph_index]

        # save the shape data
        image_size = [image_data.shape[0], image_data.shape[1]]

        # find channels if desired
        if find_channels:
            # structure for channel dimensions
            channel_params = []
            # Structure of channel_params
            # 0 = peak position ('peak_px')
            # 1 = index of max (the closed end)
            # 2 = index of min (the open end)
            # 3 = length of the channel (min - max)

            # Detect peaks in the x projection (i.e. find the channels).
            projection_x = image_data.sum(axis = 0)
            # find_peaks_cwt is a finction which attempts to find the peaks in a 1-D array by
            # convolving it with a wave. here the wave is the default wave used by the algorythm
            # but the minimum signal to noise ratio is specified
            peaks = spsig.find_peaks_cwt(projection_x, np.arange(channel_width-5,channel_width+5),
                                         min_snr = channel_detection_snr)

            # If the left-most peak position is within half of a channel separation,
            # discard the channel from the list.
            if peaks[0] < (channel_midline_separation / 2):
                peaks = peaks[1:]
            # If the difference between the right-most peak position and the right edge
            # of the image is less than half of a channel separation, discard the channel.
            if image_data.shape[0] - peaks[len(peaks)-1] < (channel_midline_separation / 2):
                peaks = peaks[:-1]

            # Find the average channel ends for the y-projected image
            projection_y = image_data.sum(axis = 1)
            # diff returns the array of the differences between each element and its neighbor
            # in a given array. View takes a snapshot of data in memory and allows it to be
            # reinterpreted as annother data type. this appears to be the index of the
            # maximum of the derivative of the uper 2/3's of the y projection rebinned
            image_deriv_max = np.diff(projection_y[:int(projection_y.shape[0]*(1./3.))].view(np.int32)[0::2]).argmax()
            # the same only the indexl of the min of the derivative of the  lower 2/3's
            # of the projection plus 2/3 of the "height" of the y projection
            image_deriv_min = np.diff(projection_y[int(projection_y.shape[0]*(2./3.)):].view(np.int32)[0::2]).argmin() + int(projection_y.shape[0]*(2./3.))

            # Slice up the image into an array of channel strips
            channel_strips = []
            for peak in peaks:
                # Structure of channel_strips
                # 0 = peak position, 1 = image of the strip (AKA the channel) itself
                channel_strips.append([peak, image_data[0:image_data.shape[0], peak-crop_half_width:peak+crop_half_width]])

            # Find channel starts and ends based on the maximum derivative of the channel profile;
            # min of the first derivative is usually the open end and max is usually the closed end.

            # THE FOLLOWING IS SIMILAR TO WHAT THE CODE ALREADY DID TO THE WHOLE IMAGE ONLY NOW IT IS
            # DOING ANALYSIS OF THE IMAGES OF INDIVIDUAL CHANNELS! i.e. it is a first order correction
            # on the previous calculations done at the whole image level
            # loop through the list of channel strip structures that we created

            # create these slice bounds to ensure we are within the image
            px_window = 20 # Search for a channel bounds in 20px windows around the image global bounds
            low_for_max = max(0, image_deriv_max-(px_window))
            high_for_max = min(image_deriv_max+px_window, image_data.shape[0])
            low_for_min = max(0, image_deriv_min-px_window)
            high_for_min = min(image_deriv_min+(px_window), image_data.shape[0])

            for strip in channel_strips:
                # get the projection of the image of the channel strip onto the y axis
                slice_projection_y = strip[1].sum(axis = 1)
                # get the derivative of the projection
                first_derivative = np.diff(slice_projection_y.view(np.int32)[0::2])

                # find the postion of the maximum value of the derivative of the projection
                # of the slice onto the y axis within the distance of px_window from the edge of slice
                maximum_index = first_derivative[low_for_max:high_for_max].argmax()
                # same for the min
                minimum_index = first_derivative[low_for_min:high_for_min].argmin()
                # attach the calculated data to the list channel_params, corrected
                channel_params.append([strip[0], # peak position (x)
                    int(maximum_index + low_for_max), # close end position (y)
                    int(minimum_index + low_for_min), # open end position (y)
                    int(abs((minimum_index + low_for_min) - (maximum_index + low_for_max))), # length y
                    False]) # not sure what false is for

            # Guide a re-detection of the min/max indices to smaller windows of the modes for this image
            # here mode is meant in the statistical sence ie mode([1,2,2,3,3,3,3,4]) give 3
            # channel_modes is a list of the modes (and a list of ther frequencies) for each of the
            # coordinates sorted in each element of the channel_params list elements
            channel_modes = spstats.mode(channel_params, axis = 0)
            # channel_medians is a list of the medians in the same fashion
            channel_medians = spstats.nanmedian(channel_params, axis = 0)

            # Sanity-check boundaries:
            #  Reset modes
            channel_modes = spstats.mode(channel_params, axis = 0)
            channel_medians = spstats.nanmedian(channel_params, axis = 0)
            max_baseline = 0
            min_baseline = 0
            len_baseline = 0
            # set min_baseline
            try:
                if channel_modes[0][0][2] > 0:
                    min_baseline = int(channel_modes[0][0][2])
                # use median information if modes are no use
                else:
                    min_baseline = int(channel_medians[2])
                # if everything is unreasonable COMPLAIN!
                if min_baseline <= 0:
                    warning("No reasonable baseline minumum found!")
                    warning("Image:",image_filename)
                    warning("Medians:",channel_medians)
                    warning("Modes:",channel_modes)
                    raise
            except:
                warning('%s: error in mode/median analysis; maybe the device is delaminated?' % image_filename.split("/")[-1])
                print("-")
                return [image_filename, -1]

            # set max_baseline
            if channel_modes[0][0][1] > 0:
                max_baseline = int(channel_modes[0][0][1])
            # use median information if modes are no use
            else:
                max_baseline = int(channel_medians[1])
            # if everything is unreasonable COMPLAIN!
            if max_baseline <= 0:
                warning("%s: no reasonable baseline maximum found." % image_filename.split("/")[-1])
                print("-")
                return [image_filename, -1]

            # set len_baseline
            if channel_modes[0][0][3] > 0:
                len_baseline = channel_modes[0][0][3]
            # use median information if modes are no use
            else:
                len_baseline = channel_medians[3]

            # check each channel for a length that is > 50% different from the mode length
            # 20150525: using 10% as a threshold for reassignment is problematic for SJW103
            # dual-trench devices because the channels on either side of the double-tall FOVs are not the same.
            # doing a C style for loop an alternative is to use "for n,channel in enumerate(channel_params)"
            # assigments to the list using the index n will stick!
            for n in range(0,len(channel_params)):
                if float(abs(channel_params[n][3] - len_baseline)) / float(len_baseline) > 0.5:
                    information("Correcting  diff(len) > 0.3...")
                    information("...")
                    if abs(channel_params[n][1] - max_baseline) < abs(channel_params[n][2] - min_baseline):
                        channel_params[n][2] = int(channel_params[n][1]) + int(len_baseline)
                    else:
                        channel_params[n][1] = int(channel_params[n][2]) - int(len_baseline)
                    channel_params[n][3] = int(abs(channel_params[n][1] - channel_params[n][2]))

            # check each channel for a closed end that is inside the image boundaries
            for n in range(0,len(channel_params)):
                if channel_params[n][1] < 0:
                    information("Correcting [n][1] < 0 in",image_filename,"at peak",channel_params[n][0])
                    information("...", max_baseline, min_baseline, int(max_baseline), int(min_baseline))
                    channel_params[n][1] = max_baseline
                    channel_params[n][2] = min_baseline
                    channel_params[n][3] = abs(channel_params[n][1] - channel_params[n][2])

            # check each channel for an open end that is inside the image boundaries
            for n in range(0,len(channel_params)):
                if channel_params[n][2] > image_data.shape[0]:
                    information("Correcting [n][2] > image_data.shape[0] in",image_filename,"at peak",channel_params[n][0])
                    information("...", max_baseline, min_baseline, int(max_baseline), int(min_baseline))
                    channel_params[n][1] = max_baseline
                    channel_params[n][2] = min_baseline
                    channel_params[n][3] = abs(channel_params[n][1] - channel_params[n][2])

            # create a dictionary of channel starts and ends
            cp_dict = {cp[0]:
                      {'closed_end_px': cp[1], 'open_end_px': cp[2]} for cp in channel_params}

        else:
            cp_dict = -1

        # return the file name, the data for the channels in that image, and the metadata
        return { 'filename': image_filename,
                 'metadata': image_metadata, # image metadata is a dictionary.
                 'image_size' : image_size,
                 'channels': cp_dict,
                 'analyze_success': True,
                 'fov': -1, # fov is found later with kmeans clustering
                 'sent_to_write': False,
                 'write_success': False,
                 'write_plane_order' : False} # this is found after get_params
    except:
        warning('Failed get_params for ' + image_filename.split("/")[-1])
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])
        print(traceback.print_tb(sys.exc_info()[2]))
        return {'filename': image_filename, 'analyze_success': False}

# finds metdata in a tiff image.
def extract_tif_metadata(tif, source='mm3_nd2ToTIFF'):
    '''This function pulls out the metadata from a tif file and returns it as a dictionary.
    Depending on the source (Nikon Elements or homebrewed script/program), it uses different
    routines as indicated by the parameter source. tif is an opened tif file (using the package
    tifffile)



    arguments:
        fname (tifffile.TiffFile): TIFF file object from which data will be extracted
    returns:
        dictionary of values:
            'jdn' (float)
            'x' (float)
            'y' (float)
            'plane_names' (list of strings)

    Called by
    mm3.get_tif_params

    '''

    idata = { 'jdn': 0.0,
              'x': 0.0,
              'y': 0.0,
              'plane_names': []}

    for page in tif:
        #print("Page found.")
        for tag in page.tags.values():
            #print("Checking tag",tag.name,tag.value)
            t = tag.name, tag.value
            t_string = u""
            time_string = u""
            # Interesting tag names: 65330, 65331 (binary data; good stuff), 65332
            # we wnat to work with the tag of the name 65331
            # if the tag name is not in the set of tegs we find interesting then skip this cycle of the loop
            if tag.name not in ('65331', '65332', 'strip_byte_counts', 'image_width', 'orientation', 'compression', 'new_subfile_type', 'fill_order', 'max_sample_value', 'bits_per_sample', '65328', '65333'):
                #print("*** " + tag.name)
                #print(tag.value)
                pass
            #if tag.name == '65330':
            #    return tag.value
            if tag.name in ('65331'):
                # make info list a list of the tag values 0 to 65535 by zipoing up a paired list of two bytes, at two byte intervals i.e. ::2
                # note that 0X100 is hex for 256
                infolist = [a+b*0x100 for a,b in zip(tag.value[0::2], tag.value[1::2])]
                # get char values for each element in infolist
                for c_entry in range(0, len(infolist)):
                    # the element corresponds to an ascii char for a letter or bracket (and a few other things)
                    if infolist[c_entry] < 127 and infolist[c_entry] > 64:
                        # add the letter to the unicode string t_string
                        t_string += chr(infolist[c_entry])
                    #elif infolist[c_entry] == 0:
                    #    continue
                    else:
                        t_string += " "

                # this block will find the dTimeAbsolute and print the subsequent integers
                # index 170 is counting seconds, and rollover of index 170 leads to increment of index 171
                # rollover of index 171 leads to increment of index 172
                # get the position of the array by finding the index of the t_string at which dTimeAbsolute is listed not that 2*len(dTimeAbsolute)=26
                #print(t_string)

                arraypos = t_string.index("dXPos") * 2 + 16
                xarr = tag.value[arraypos:arraypos+4]
                b = ''.join(chr(i) for i in xarr)
                idata['x'] = float(struct.unpack('<f', b)[0])

                arraypos = t_string.index("dYPos") * 2 + 16
                yarr = tag.value[arraypos:arraypos+4]
                b = ''.join(chr(i) for i in yarr)
                idata['y'] = float(struct.unpack('<f', b)[0])

                arraypos = t_string.index("dTimeAbsolute") * 2 + 26
                shortarray = tag.value[arraypos+2:arraypos+10]
                b = ''.join(chr(i) for i in shortarray)
                idata['jdn'] = float(struct.unpack('<d', b)[0])

                # extract plane names
                il = [a+b*0x100 for a,b in zip(tag.value[0::2], tag.value[1::2])]
                li = [a+b*0x100 for a,b in zip(tag.value[1::2], tag.value[2::2])]

                strings = list(zip(il, li))

                allchars = ""
                for c_entry in range(0, len(strings)):
                    if 31 < strings[c_entry][0] < 127:
                        allchars += chr(strings[c_entry][0])
                    elif 31 < strings[c_entry][1] < 127:
                        allchars += chr(strings[c_entry][1])
                    else:
                        allchars += " "

                allchars = re.sub(' +',' ', allchars)

                words = allchars.split(" ")

                #print(words)

                planes = []
                for idx in [i for i, x in enumerate(words) if x == "sOpticalConfigName"]:
                    try: # this try is in case this is just an imported function
                        if Goddard:
                            if words[idx-1] == "uiCompCount":
                                planes.append(words[idx+1])
                        else:
                            planes.append(words[idx+1])
                    except:
                        planes.append(words[idx+1])
                idata['plane_names'] = planes
    return idata



### functions about converting dates and times
### Functions
def days_to_hmsm(days):
    hours = days * 24.
    hours, hour = math.modf(hours)
    mins = hours * 60.
    mins, min = math.modf(mins)
    secs = mins * 60.
    secs, sec = math.modf(secs)
    micro = round(secs * 1.e6)
    return int(hour), int(min), int(sec), int(micro)

def hmsm_to_days(hour=0, min=0, sec=0, micro=0):
    days = sec + (micro / 1.e6)
    days = min + (days / 60.)
    days = hour + (days / 60.)
    return days / 24.

def date_to_jd(year,month,day):
    if month == 1 or month == 2:
        yearp = year - 1
        monthp = month + 12
    else:
        yearp = year
        monthp = month
    # this checks where we are in relation to October 15, 1582, the beginning
    # of the Gregorian calendar.
    if ((year < 1582) or
        (year == 1582 and month < 10) or
        (year == 1582 and month == 10 and day < 15)):
        # before start of Gregorian calendar
        B = 0
    else:
        # after start of Gregorian calendar
        A = math.trunc(yearp / 100.)
        B = 2 - A + math.trunc(A / 4.)
    if yearp < 0:
        C = math.trunc((365.25 * yearp) - 0.75)
    else:
        C = math.trunc(365.25 * yearp)
    D = math.trunc(30.6001 * (monthp + 1))
    jd = B + C + D + day + 1720994.5
    return jd

def datetime_to_jd(date):
    days = date.day + hmsm_to_days(date.hour,date.minute,date.second,date.microsecond)
    return date_to_jd(date.year, date.month, days)


### functions about trimming and padding images
# cuts out a channel from an tiff image (that has been processed)
def cut_slice(image_pixel_data, channel_loc):
    '''Takes an image and cuts out the channel based on the slice location
    slice location is the list with the peak information, in the form
    [peak_id, [[y1, y2],[x1, x2]]]. returns the channel slice as a numpy array.
    The numpy array will be a stack if there are multiple planes.

    if you want to slice all the channels from a picture with the channel_masks
    dictionary use a loop like this:

    for channel_loc in channel_masks[fov_id]: # fov_id is the fov of the image
        channel_slice = cut_slice[image_pixel_data, channel_loc]
        # ... do something with the slice

    NOTE: this function is for images that have gone through the
          rotation in process_tif
    '''
    channel_id = channel_loc[0] # the id is the peak location and is the first element
    channel_slice = np.zeros([image_pixel_data.shape[0],
                              channel_loc[1][0][1]-channel_loc[1][0][0],
                              channel_loc[1][1][1]-channel_loc[1][1][0]])
    #print(channel_id, channel_slice.shape)
    channel_slicer = np.s_[channel_loc[1][0][0]:channel_loc[1][0][1],
                           channel_loc[1][1][0]:channel_loc[1][1][1],:] # slice obj
    channel_slice = image_pixel_data[channel_slicer]
    if np.any([a < 1 for a in channel_slice.shape]):
        raise ValueError('channel_slice shapes must be positive (%s, %s)' % (str(channel_loc[0]), str(channel_slice.shape)))
    return channel_id, channel_slice

# remove margins of zeros from 2d numpy array
def trim_zeros_2d(array):
    # make the array equal to the sub array which has columns of all zeros removed
    # "all" looks along an axis and says if all of the valuse are such and such for each row or column
    # ~ is the inverse operator
    # using logical indexing
    array = array[~np.all(array == 0, axis = 1)]
    # transpose the array
    array = array.T
    # make the array equal to the sub array which has columns of all zeros removed
    array = array[~np.all(array == 0, axis = 1)]
    # transpose the array again
    array = array.T
    # return the array
    return array


### functions abous subtraction
# worker function for doing subtraction
def subtract_phase(dataset):
    '''subtract_phase_only is the main worker function for doign alignment and subtraction.
    Modified from subtract_phase_only by jt on 20160511
    The subtracted image returned is the same size as the image given. It may however include
    data points around the edge that are meaningless but not marked.

    parameters
    ---------
    dataset : list of length two with; [image, empty_mean]

    returns
    ---------
    (subtracted_image, offset) : tuple with the subtracted_image as well as the ammount it
        was shifted to be aligned with the empty. offset = (x, y), negative or positive
        px values.
    '''
    try:
        if matching_length is not None:
            pass
    except:
        matching_length = 180

    try:
        # get out data and pad
        cropped_channel, empty_channel = dataset # [channel slice, empty slice]
        # rescale empty to levels of channel image
        #empty_channel = rescale_intensity(empty_channel,
        #                                  out_range=(np.amin(cropped_channel[:,:,0]),
        #                                             np.amax(cropped_channel[:,:,0])))

        ### Pad empty channel.
        # Rough padding amount for empty to become template in match_template
        start_padding = (25, 25, 25, 25) # (top, bottom, left, right)

        # adjust padding for empty so padded_empty is same size as channel later.
        # it is important that the adjustment is made on the bottom and right sides,
        # as later the alignment is measured from the top and left.
        y_diff = cropped_channel.shape[0] - empty_channel.shape[0]
        x_diff = cropped_channel.shape[1] - empty_channel.shape[1]

        # numpy.pad-compatible padding tuple: ((top, bottom), (left, right))
        empty_paddings = ((start_padding[0], start_padding[1] + y_diff), # add y_diff to sp[1]
                          (start_padding[2], start_padding[3] + x_diff)) # add x_diff to sp[3]

        # edge-pad the empty channel using these paddings
        padded_empty = np.pad(empty_channel, empty_paddings, 'edge')

        ### Align channel to empty using match template.
        # get a vertical chunk of the image of the empty channel
        empty_subpart = padded_empty[:matching_length+start_padding[0]+start_padding[1]]
        # get a vertical chunk of the channel to be subtracted from
        chan_subpart = cropped_channel[:matching_length,:,0] # phase data = 0

        # equalize histograms for alignment
        empty_subpart = equalize_hist(empty_subpart)
        chan_subpart = equalize_hist(chan_subpart)

        # use match template to get a correlation array and find the position of maximum overlap
        match_result = match_template(empty_subpart, chan_subpart)
        # get row and colum of max correlation value in correlation array
        y, x = np.unravel_index(np.argmax(match_result), match_result.shape)

        # this is how much it was shifted in x and y.
        # important to store for getting exact px position later
        offset = (x - start_padding[2], y - start_padding[0])

        ### pad the original cropped channel image.
        # align the data between the empty image and the cropped images
        # using the offsets to create a padding that adjusts the location of
        # the channel
        channel_paddings = ((y, start_padding[0] + start_padding[1] - y), # include sp[0] with sp[1]
                            (x, start_padding[2] + start_padding[3] - x), # include sp[2] with sp[3]
                            (0,0))

        # the difference of padding on different sides relocates the channel to same
        # relative location as the empty channel (in the padded version.)
        shifted_padded_channel = np.pad(cropped_channel.astype('int32'),
                                        channel_paddings,
                                        mode="edge")

        # trim down the pad-shifted channel to the same region where the empty image has data
        channel_for_sub = shifted_padded_channel[start_padding[0]:-1*start_padding[1],
                                                 start_padding[2]:-1*start_padding[3]]
        empty_for_sub = padded_empty[start_padding[0]:-1*start_padding[1],
                                     start_padding[2]:-1*start_padding[3]]

        ### rescale the empty image intensity based on the pixel intensity ratios
        # calculate the ratio of pixel intensities
        pxratios = channel_for_sub[:,:,0].astype('float')/empty_for_sub.astype('float')
        # calculate the rough peak of intensity values
        pxrdist = np.histogram(pxratios, range=(0.5,1.5), bins=100)
        # get the peak value for rescaling the empty image
        distcenters = pxrdist[1][:-1]+np.diff(pxrdist[1])/2
        pxrpeak = distcenters[np.argmax(pxrdist[0])]
        # rescale the empty image
        empty_for_sub = (empty_for_sub.astype('float')/pxrpeak).astype('uint16')

        # add dimension to empty channel to give it Z=1 size
        if len(empty_for_sub.shape) < 3:
            # this function as called adds a third axis to empty channel which is flat now
            empty_for_sub = np.expand_dims(empty_for_sub, axis = 2)
        padded_empty_3d0 = np.zeros_like(empty_for_sub)
        for color in xrange(1, cropped_channel.shape[2]):
            # depth-stack the non-phase planes of the cropped image with zero arrays of same size
            empty_for_sub = np.dstack((empty_for_sub, padded_empty_3d0))

        ### Compute the difference between the empty and channel phase contrast images
        # subtract the empty image from the cropped channel image
        channel_subtracted = channel_for_sub.astype('int32') - empty_for_sub.astype('int32')

        channel_subtracted[:,:,0] *= -1 # make cells high-intensity
        # Reset the zero level in the image by subtracting the min value
        channel_subtracted[:,:,0] -= np.min(channel_subtracted[:,:,0])
        # add one to everything so there are no zeros in the image
        channel_subtracted[:,:,0] += 1
        # Stack the phase-contrast image used for subtraction to the bottom of the stack
        channel_subtracted = np.dstack((channel_subtracted, channel_for_sub[:,:,0]))

        return((channel_subtracted, offset))
    except:
        warning("Error in subtracting_phase:")
        warning(sys.exc_info()[1])
        warning(traceback.print_tb(sys.exc_info()[2]))
        raise

# for doing subtraction when just starting and there is a backlog
def subtract_backlog(fov_id):
    return_value = -1
    try:
        information('subtract_backlog: Subtracting backlog of images FOV %03d.' % fov_id)

        # load cell peaks and empty mean
        cell_peaks = mm3.load_cell_peaks(fov_id) # load list of cell peaks from spec file
        empty_mean = mm3.load_empty_tif(fov_id) # load empty mean image
        empty_mean = mm3.trim_zeros_2d(empty_mean) # trim any zero data from the image
        information('subtract_backlog: There are %d cell peaks for FOV %03d.' % (len(cell_peaks), fov_id))

        # aquire lock, giving other threads which may be blocking a chance to clear
        lock_acquired = hdf5_locks[fov_id].acquire(block = True)

        # peaks_images will be a list of [fov_id, peak, images, empty_mean]
        with h5py.File(experiment_directory + analysis_directory +
                       'originals/' + 'original_%03d.hdf5' % fov_id, 'r', libver='earliest') as h5f:

            for peak in sorted(cell_peaks):
                images = h5f[u'channel_%04d' % peak][:] # get all the images (and whole stack)
                plane_names = h5f[u'channel_%04d' % peak].attrs['plane_names'] # get plane names

                # move the images into a long list of list with the image next to empty mean.
                images_with_empties = []
                for image in images:
                    images_with_empties.append([image, empty_mean])
                del images

                # set up multiprocessing
                spool = Pool(num_blsubtract_subthreads) # for 'subpool of alignment/subtraction '.
                # send everything to be processed
                pool_result = spool.map_async(subtract_phase, images_with_empties,
                                              chunksize = 10)
                spool.close()
                information('subtract_backlog: Subtraction started for FOV %d, peak %04d.' % (fov_id, peak))

                # just loop around waiting for the peak to be done.
                try:
                    while (True):
                        time.sleep(1)
                        if pool_result.ready():
                            break
                    # inform user once this is done
                    information("subtract_backlog: Completed peak %d in FOV %03d (%d timepoints)" %
                                (peak, fov_id, len(images_with_empties)))
                except KeyboardInterrupt:
                    raise

                if not pool_result.successful():
                    warning('subtract_backlog: Processing pool not successful for peak %d.' % peak)
                    raise AttributeError

                # get the results and clean up memory
                subtracted_data = pool_result.get() # this is a list of (sub_image, offset)
                subtracted_images = zip(*subtracted_data)[0] # list of subtracted images
                offsets = zip(*subtracted_data)[1] # list of offsets for x and y
                # free some memory
                del pool_result
                del subtracted_data
                del images_with_empties

                # write the subtracted data to disk
                with h5py.File(experiment_directory + analysis_directory + 'subtracted/subtracted_%03d.hdf5' % fov_id, 'a', libver='earliest') as h5s:
                    # create data set, use first image to set chunk and max size
                    h5si = h5s.create_dataset("subtracted_%04d" % peak,
                                              data=np.asarray(subtracted_images, dtype=np.uint16),
                                              chunks=(1, subtracted_images[0].shape[0],
                                                      subtracted_images[0].shape[1], 1),
                                              maxshape=(None, subtracted_images[0].shape[0],
                                                        subtracted_images[0].shape[1], None),
                                              compression="gzip", shuffle=True)

                    # rearrange plane names
                    plane_names = plane_names.tolist()
                    plane_names.append(plane_names.pop(0))
                    plane_names.insert(0, 'subtracted_phase')
                    h5si.attrs['plane_names'] = plane_names

                    # create dataset for offset information
                    # create and write first metadata
                    h5os = h5s.create_dataset(u'offsets_%04d' % peak,
                                              data=np.array(offsets),
                                              maxshape=(None, 2))

            # move over metadata once peaks have all peaks have been written
            with h5py.File(experiment_directory + analysis_directory + 'subtracted/subtracted_%03d.hdf5' % fov_id, 'a', libver='earliest') as h5s:
                sub_mds = h5s.create_dataset("metadata", data=h5f[u'metadata'],
                                             maxshape=(None, 3))

        # return 0 to the parent loop if everything was OK
        return_value = 0
    except:
        warning("subtract_backlog: Failed for FOV: %03d" % fov_id)
        warning(sys.exc_info()[1])
        warning(traceback.print_tb(sys.exc_info()[2]))
        return_value = 1

    # release lock
    hdf5_locks[fov_id].release()

    return return_value
