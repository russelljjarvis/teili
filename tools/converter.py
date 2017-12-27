"""
functions in this module convert data from or to brian2 compatible formats
especially, there are functions to convert data coming from dvs camera
"""

import os
import numpy as np
import struct


def aedat2numpy(datafile='/tmp/aerout.aedat', length=0, version='V2', debug=0, camera='DVS128'):
    """
    load AER data file and parse these properties of AE events:
        - timestamps (in us),
        - x,y-position [0..127]
        - polarity (0/1)
        @param datafile - path to the file to read
        @param length - how many bytes(B) should be read; default 0=whole file
        @param version - which file format version is used: "aedat" = v2, "dat" = v1 (old)
        @param debug - 0 = silent, 1 (default) = print summary, >=2 = print all debug
        @param camera='DVS128' or 'DAVIS240'
        @return (ts, xpos, ypos, pol) 4-tuple of lists containing data of all events;

    Args:
        datafile (str, optional): Description
        length (int, optional): Description
        version (str, optional): Description
        debug (int, optional): Description
        camera (str, optional): Description

    Returns:
        TYPE: Description

    Raises:
        ValueError: Description
    """
    # constants
    # V3 = "aedat3"
    # V2 = "aedat" # current 32bit file format
    # V1 = "dat"  # old format
    EVT_DVS = 0  # DVS event type
    EVT_APS = 1  # APS event

    aeLen = 8  # 1 AE event takes 8 bytes
    readMode = '>II'  # struct.unpack(), 2x ulong, 4B+4B
    td = 0.000001  # timestep is 1us
    if(camera == 'DVS128'):
        xmask = 0x00fe
        xshift = 1
        ymask = 0x7f00
        yshift = 8
        pmask = 0x1
        pshift = 0
    elif(camera == 'DAVIS240'):  # values take from scripts/matlab/getDVS*.m
        xmask = 0x003ff000
        xshift = 12
        ymask = 0x7fc00000
        yshift = 22
        pmask = 0x800
        pshift = 11
        eventtypeshift = 31
    else:
        raise ValueError("Unsupported camera: %s" % (camera))
    if (version == 'V1'):
        print ("using the old .dat format")
        aeLen = 6
        readMode = '>HI'  # ushot, ulong = 2B+4B
    aerdatafh = open(datafile, 'rb')
    k = 0  # line number
    p = 0  # pointer, position on bytes
    statinfo = os.stat(datafile)
    if length == 0:
        length = statinfo.st_size
    # print ("file size", length)
    # header
    lt = aerdatafh.readline()
    while lt and lt[0] == "#":
        p += len(lt)
        k += 1
        lt = aerdatafh.readline()
        if debug >= 2:
            print (str(lt))
        continue
    # variables to parse
    timestamps = []
    xaddr = []
    yaddr = []
    pol = []
    # read data-part of file
    aerdatafh.seek(p)
    s = aerdatafh.read(aeLen)
    p += aeLen
    # print (xmask, xshift, ymask, yshift, pmask, pshift)
    while p < length:
        addr, ts = struct.unpack(readMode, s)
        # parse event type
        if(camera == 'DAVIS240'):
            eventtype = (addr >> eventtypeshift)
        else:  # DVS128
            eventtype = EVT_DVS
        # parse event's data
        if(eventtype == EVT_DVS):  # this is a DVS event
            x_addr = (addr & xmask) >> xshift
            y_addr = (addr & ymask) >> yshift
            a_pol = (addr & pmask) >> pshift
            if debug >= 3:
                print("ts->", ts)  # ok
                print("x-> ", x_addr)
                print("y-> ", y_addr)
                print("pol->", a_pol)
            timestamps.append(ts)
            xaddr.append(x_addr)
            yaddr.append(y_addr)
            pol.append(a_pol)
        aerdatafh.seek(p)
        s = aerdatafh.read(aeLen)
        p += aeLen
    if debug > 0:
        try:
            print ("read %i (~ %.2fM) AE events, duration= %.2fs" % (len(timestamps), len(timestamps) / float(10 ** 6), (timestamps[-1] - timestamps[0]) * td))
            n = 5
            print ("showing first %i:" % (n))
            print ("timestamps: %s \nX-addr: %s\nY-addr: %s\npolarity: %s" % (timestamps[0:n], xaddr[0:n], yaddr[0:n], pol[0:n]))
        except:
            print ("failed to print statistics")
    Events = np.zeros([4, len(timestamps)])
    Events[0, :] = xaddr
    Events[1, :] = yaddr
    Events[2, :] = timestamps
    Events[3, :] = pol
    return Events




def dvs2ind(Events=None, eventDirectory=None, resolution='DAVIS240', scale=True):
    """Summary Function which converts events extracted from an aedat file using aedat2numpy
    into 1D vectors of neuron indices and timestamps. Funcion only returns index and timestamp
    list for existing types (e.g. On & Off events)

    Args:
        Events (None, optional): 4D numpd.ndarray which contains pixel location (x,y), timestamps and polarity ((4,#events))
        eventDirectory (None, optional): Path to stored events
        resolution (str/int, optional): Resolution of the camera.
        scale (bool, optional): Flag to rescale the timestampts from micro- to milliseconds

    Returns:
        indices_on (1d numpy.array): Unique indices which maps the pixel location of the camera to the 1D neuron indices of ON events
        ts_on (1d numpy.array):  Unique timestamps of active indices of ON events
        indices_off (1d numpy.array): Unique indices which maps the pixel location of the camera to the 1D neuron indices of OFF events
        ts_off (1d numpy.array):  Unique timestamps of active indices of OFF events
    """
    if eventDirectory is not None:
        assert type(eventDirectory) == str, 'eventDirectory must be a string'
        assert eventDirectory[
            -4:] == '.npy', 'Please specify a numpy array (.npy) which contains the DVS events.\n Aedat files can be converted using function aedat2numpy.py'
        Events = np.load(eventDirectory)
    if Events is not None:
        assert eventDirectory is None, 'Either you specify a path to load Events using eventDirectory. Or you pass the event numpy directly. NOT Both.'
    if np.size(Events, 0) > np.size(Events, 1):
        Events = np.transpose(Events)

    # extract tempory indices to retrieve
    cInd_on = Events[3, :] == 1  # Boolean logic to get indices of on and off events, respectively
    cInd_off = Events[3, :] == 0

    # Initialize 1D arrays for neuron indices and timestamps
    indices_on = np.zeros([int(np.sum(cInd_on))])
    spiketimes_on = np.zeros([int(np.sum(cInd_on))])
    # Polarity is either 0 or 1 so the entire length minus the sum of the polarity give the proportion of off events
    indices_off = np.zeros([int(np.sum(cInd_off))])
    spiketimes_off = np.zeros([int(np.sum(cInd_off))])

    if type(resolution) == str:
        resolution = int(resolution[-3:])  # extract the x-resolution (i.e. the resolution along the x-axis of the camera)

    # The equation below follows index = x + y*resolution
    # To retrieve the x and y coordinate again from the index see ind2px
    indices_on = Events[0, cInd_on] + Events[1, cInd_on] * resolution
    indices_off = Events[0, cInd_off] + Events[1, cInd_off] * resolution
    if scale:
        # The DVS timestamps are in microseconds. We need to convert them to milliseconds for brian
        spiketimes_on = np.ceil(Events[2, cInd_on] * 10**(-3))
        spiketimes_off = np.ceil(Events[2, cInd_off] * 10**(-3))

    else:
        # The flag scale is used to prevent rescaling of timestamps if we use artifically generated stimuli
        spiketimes_on = np.ceil(Events[2, cInd_on])
        spiketimes_off = np.ceil(Events[2, cInd_off])

    # Check for double entries within 100 us
    ts_on_tmp = spiketimes_on
    ind_on_tmp = indices_on
    ts_off_tmp = spiketimes_off
    ind_off_tmp = indices_off
    delta_t = 1

    for i in range(len(spiketimes_on)):
        mask_t = spiketimes_on[i]
        mask_i = indices_on[i]

        doubleEntries = np.logical_and(np.logical_and(ts_on_tmp >= mask_t, ts_on_tmp <= mask_t + delta_t), mask_i == ind_on_tmp)
        # uniqueEntries = np.invert(doubleEntries)
        # print np.sum(doubleEntries)
        if np.sum(doubleEntries) > 1:
            tmp = np.where(doubleEntries == True)  # Find first occurence on non-unique entries
            doubleEntries[tmp[0][0]] = False  # keep the first occurance of non-unique entry
            uniqueEntries = np.invert(doubleEntries)
            ts_on_tmp = ts_on_tmp[uniqueEntries]
            ind_on_tmp = ind_on_tmp[uniqueEntries]

    for i in range(len(spiketimes_off)):
        mask_t = spiketimes_off[i]
        mask_i = indices_off[i]

        doubleEntries = np.logical_and(np.logical_and(ts_off_tmp >= mask_t, ts_off_tmp <= mask_t + delta_t), mask_i == ind_off_tmp)
        # uniqueEntries = np.invert(doubleEntries)
        # print np.sum(doubleEntries)
        if np.sum(doubleEntries) > 1:
            tmp = np.where(doubleEntries == True)  # Find first occurence on non-unique entries
            doubleEntries[tmp[0][0]] = False  # keep the first occurance of non-unique entry
            uniqueEntries = np.invert(doubleEntries)
            ts_off_tmp = ts_off_tmp[uniqueEntries]
            ind_off_tmp = ind_off_tmp[uniqueEntries]

    indices_off = ind_off_tmp
    ts_off = ts_off_tmp
    indices_on = ind_on_tmp
    ts_on = ts_on_tmp
    return_on = False
    return_off = False
    # normalize timestamps
    if np.size(ts_on) != 0:
        ts_on -= np.min(ts_on)
        return_on = True
    if np.size(ts_off) != 0:
        ts_off -= np.min(ts_off)
        return_off = True
    if return_on == True and return_off == True:
        return indices_on, ts_on, indices_off, ts_off
    elif return_on == True:
        return indices_on, ts_on
    elif return_off == True:
        return indices_off, ts_off


def DVScsv2numpy(datafile='tmp/aerout.csv', exp_name='Experiment', debug=False):
    """
    load AER csv logfile and parse these properties of AE events:
        - timestamps (in us),
        - x,y-position [0..127]
        - polarity (0/1)
        @param datafile - path to the file to read
        @param debug - 0 = silent, 1 (default) = print summary, >=2 = print all debug
        @return (ts, xpos, ypos, pol) 4-tuple of lists containing data of all events;

    Args:
        datafile (str, optional): Description
        exp_name (str, optional): Description
        debug (bool, optional): Description

    Returns:
        TYPE: Description
    """
    import pandas as pd

    logfile = datafile

    df = pd.read_csv(logfile, header=0)

    df.dropna(inplace=True)
    # Process timestamps: Start at zero
    df['timestamp'] = df['timestamp'].astype(int)

    # Safe raw input
    df['x_raw'] = df['x']
    df['y_raw'] = df['y']
    x_list = []
    y_list = []
    time_list = []
    pol_list = []
    x_list = df['x_raw']
    y_list = df['y_raw']
    time_list = df['timestamp']
    pol_list = df['pol']
    timestep = time_list[0]

    # Get new coordinates with more useful representation
    #df['x'] = df['y_raw']
    #df['y'] = 128 - df['x_raw']
    # discard every third event
    #new_ind = 0
    #Events = np.zeros([4, len(df['timestamp'])/3])
    Events_x = []
    Events_y = []
    Events_time = []
    Events_pol = []
    counter = 0
    for j in range(len(df['timestamp'])):
        if counter % 3 == 0:
            if (timestep == time_list[j]):
                #Events[0, new_ind] = x_list[j]
                Events_x.append(x_list[j])
                Events_y.append(y_list[j])
                Events_time.append(time_list[j])
                Events_pol.append(pol_list[j])
                #new_ind += 1
                timestep = time_list[j]
            else:
                counter += 1
                timestep = time_list[j]
        elif counter % 3 == 1:
            if (timestep == time_list[j]):
                continue
            else:
                counter += 1
                timestep = time_list[j]
        elif counter % 3 == 2:
            if (timestep == time_list[j]):
                continue
            else:
                counter += 1
                timestep = time_list[j]
    Events = np.zeros([4, len(Events_time)])
    Events[0, :] = Events_x
    Events[1, :] = Events_y
    Events[2, :] = Events_time
    Events[3, :] = Events_pol
    if debug == True:
        print(Events[0, 0:10])
        print(Events[1, 0:10])
        print(Events[2, 0:10])
        print(Events[3, 0:10])
    return Events
