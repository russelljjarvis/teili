# -*- coding: utf-8 -*-
"""Summary
"""
# @Author: mmilde
# @Date:   2017-12-27 12:07:15
# @Last Modified by:   mmilde
# @Last Modified time: 2018-05-17 09:24:42

"""
Function for external interfaces such as event-based camera, i.e. DVS
functions in this module convert data from or to brian2 compatible formats
especially, there are functions to convert data coming from dvs camera
"""

import os
import numpy as np
import struct
import itertools


def skip_header(file_read):
    '''skip header

    Args:
        file_read (TYPE): Description
    '''
    line = file_read.readline()
    while line.startswith(b'#'):
        if (line == b'#!END-HEADER\r\n'):
            break
        else:
            line = file_read.readline()


def read_events(file_read, xdim, ydim):
    """A simple function that read events from cAER tcp

    Args:
        file_read (TYPE): Description
        xdim (TYPE): Description
        ydim (TYPE): Description

    Returns:
        TYPE: Description
    """

    #raise Exception
    data = file_read.read(28)

    if(len(data) == 0):
        return [-1], [-1], [-1], [-1], [-1], [-1]

    # read header
    eventtype = struct.unpack('H', data[0:2])[0]
    eventsource = struct.unpack('H', data[2:4])[0]
    eventsize = struct.unpack('I', data[4:8])[0]
    eventoffset = struct.unpack('I', data[8:12])[0]
    eventtsoverflow = struct.unpack('I', data[12:16])[0]
    eventcapacity = struct.unpack('I', data[16:20])[0]
    eventnumber = struct.unpack('I', data[20:24])[0]
    eventvalid = struct.unpack('I', data[24:28])[0]
    next_read = eventcapacity * eventsize  # we now read the full packet
    data = file_read.read(next_read)
    counter = 0  # eventnumber[0]
    # return arrays
    x_addr_tot = []
    y_addr_tot = []
    pol_tot = []
    ts_tot = []
    spec_type_tot = []
    spec_ts_tot = []

    if(eventtype == 1):  # something is wrong as we set in the cAER to send only polarity events
        while(data[counter:counter + eventsize]):  # loop over all event packets
            aer_data = struct.unpack('I', data[counter:counter + 4])[0]
            timestamp = struct.unpack('I', data[counter + 4:counter + 8])[0]
            x_addr = (aer_data >> 17) & 0x00007FFF
            y_addr = (aer_data >> 2) & 0x00007FFF
            x_addr_tot.append(x_addr)
            y_addr_tot.append(y_addr)
            pol = (aer_data >> 1) & 0x00000001
            pol_tot.append(pol)
            ts_tot.append(timestamp)
            # print (timestamp, x_addr, y_addr, pol)
            counter = counter + eventsize
    elif(eventtype == 0):
        spec_type_tot = []
        spec_ts_tot = []
        while(data[counter:counter + eventsize]):  # loop over all event packets
            special_data = struct.unpack('I', data[counter:counter + 4])[0]
            timestamp = struct.unpack('I', data[counter + 4:counter + 8])[0]
            spec_type = (special_data >> 1) & 0x0000007F
            spec_type_tot.append(spec_type)
            spec_ts_tot.append(timestamp)
            if(spec_type == 6 or spec_type == 7 or spec_type == 9 or spec_type == 10):
                print(timestamp, spec_type)
            counter = counter + eventsize

    return (np.array(x_addr_tot), np.array(y_addr_tot), np.array(pol_tot), np.array(ts_tot), np.array(spec_type_tot), np.array(spec_ts_tot))


def aedat2numpy(datafile, length=0, version='V2', debug=0, camera='DVS128', unit='ms'):
    """
    load AER data file and parse these properties of AE events:
        - timestamps (in us),
        - x,y-position [0..127]x[0..127] for DVS128 [0..239]x[0..127] for DAVIS240
        - polarity (0/1)

    Args:
        datafile (str, optional): Aedat recording as provided by jAER or cAER
        length (int, optional): how many bytes(B) should be read; default 0=whole file
        version (str, optional): which file format version is used:
            - "dat" = V1 (old)
            - "aedat" jAER AEDAT 2.0 = V2
            - "aedat" cAER AEDAT 3.1 = V3
        debug (int, optional): Flag to provide more detailed report. 0 = silent, 1 (default) = print summary,
            >=2 = print all debug
        camera (str, optional): Description
        unit: output unit of timestamps specified as a string:
            - 'ms' (default), 'us' or 'sec'.

    Returns:
        numy.ndarray: (xpos, ypos, ts, pol) 2D numpy array containing data of all events

    Raises:
        ValueError: Indicates that a camera was specified which is not supported or the AEDAT file version is not supported
    """
    try:
        aerdatafh = open(datafile, 'rb')
    except FileNotFoundError:
        raise FileNotFoundError('Please specify an aedat file to convert.')
    k = 0  # line number
    p = 0  # pointer, position on bytes
    lt = aerdatafh.readline()

    # Check the .aedat format:
    if (version == 'V3'):
        # cAER AEDAT 3.1

        # Check the headerfile:
        if (lt.decode(encoding='utf-8')[9:12] == '2.0'):
            # The file version is AEDAT 2.0. Wrong version specified.
            raise ValueError(
                "Wrong .aedat version specified. \n Please enter version = 'V2' ")
        if (camera == 'DVS128'):
            raise ValueError(
                "Unsupported camera version. \n Please enter camera = 'DAVIS240'")

        skip_header(aerdatafh)

        xdim = 240
        ydim = 180

        ts_events_tmp = []
        x_events_tmp = []
        y_events_tmp = []
        p_events_tmp = []
        while(1):
            x, y, p, ts_tot, spec_type, spec_type_ts = read_events(
                aerdatafh, xdim, ydim)
            if(len(ts_tot) > 0 and ts_tot[0] == -1):
                break
            x_events_tmp.append(x)
            # Set the coordinate (0,0) at the bottom left corner:
            # NOTE: cAER orgin is at the upper left corner.
            if (camera == 'DVS128'):
                y_events_tmp.append(128 - y)
            elif (camera == 'DAVIS240'):
                y_events_tmp.append(180 - y)
            # Set the timestamps according to the specified units
            if unit == 'us':
                ts_events_tmp.append(ts_tot)
            elif unit == 'ms':
                ts_events_tmp.append(ts_tot / 1000)
            elif unit == 'sec':
                ts_events_tmp.append(ts_tot / 1e6)
            else:
                raise ValueError(
                    "Units not supported. Please select one of these: us, ms, sec")
            p_events_tmp.append(p)
        Events = np.zeros([4, len(list(itertools.chain(*ts_events_tmp)))])
        Events[0, :] = list(itertools.chain(*x_events_tmp))
        Events[1, :] = list(itertools.chain(*y_events_tmp))
        Events[2, :] = list(itertools.chain(*ts_events_tmp))
        Events[3, :] = list(itertools.chain(*p_events_tmp))
        aerdatafh.close()
        return (Events)

    elif (version == 'V2') or (version == 'V1'):

        # Check the headerfile:
        if (lt.decode(encoding='utf-8')[9:12] == '3.1'):
            # The file version is AEDAT 3.1. Wrong version specified.
            raise ValueError(
                "Wrong .aedat version specified. \n Please enter version = 'V3' ")

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
            print("using the old .dat format")
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
        while lt.startswith(b'#'):
            p += len(lt)
            k += 1
            lt = aerdatafh.readline()
            if debug >= 2:
                print(str(lt))
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
                # Set the coordinate (0,0) at the bottom left corner:
                # NOTE: jAER orgin is at the bottom right corner.
                if (camera == 'DVS128'):
                    xaddr.append(128 - x_addr)
                elif (camera == 'DAVIS240'):
                    xaddr.append(240 - x_addr)
                yaddr.append(y_addr)
                # Set the timestamps according to the specified units
                if unit == 'us':
                    timestamps.append(ts)
                elif unit == 'ms':
                    timestamps.append(ts / 1000)
                elif unit == 'sec':
                    timestamps.append(ts / 1e6)
                else:
                    raise ValueError(
                        "Units not supported. Please select one of these: us, ms, sec")
                pol.append(a_pol)
            aerdatafh.seek(p)
            s = aerdatafh.read(aeLen)
            p += aeLen
        if debug > 0:
            try:
                print("read %i (~ %.2fM) AE events, duration= %.2fs" % (len(timestamps), len(
                    timestamps) / float(10 ** 6), (timestamps[-1] - timestamps[0]) * td))
                n = 5
                print("showing first %i:" % (n))
                print("timestamps: %s \nX-addr: %s\nY-addr: %s\npolarity: %s" %
                      (timestamps[0:n], xaddr[0:n], yaddr[0:n], pol[0:n]))
            except:
                print("failed to print statistics")
        Events = np.zeros([4, len(timestamps)])
        # Set the coordinate (0,0) at the upper left corner:
        # NOTE: jAER orgin is at the bottom right corner.
        Events[0, :] = xaddr
        Events[1, :] = yaddr
        Events[2, :] = timestamps
        Events[3, :] = pol
        return Events

    else:
        raise ValueError("Unsupported AEDAT file version")
        return


def dvs2ind(Events=None, event_directory=None, resolution='DAVIS240', scale=True):
    """Summary Function which converts events extracted from an aedat file using aedat2numpy
    into 1D vectors of neuron indices and timestamps. Funcion only returns index and timestamp
    list for existing types (e.g. On & Off events)

    Args:
        Events (None, optional): 4D numpd.ndarray which contains pixel location (x,y), timestamps and polarity ((4,#events))
        event_directory (None, optional): Path to stored events
        resolution (str/int, optional): Resolution of the camera.
        scale (bool, optional): Flag to rescale the timestampts from micro- to milliseconds

    Returns:
        indices_on (1d numpy.array): Unique indices which maps the pixel location of the camera to the 1D neuron indices of ON events
        ts_on (1d numpy.array): Unique timestamps of active indices of ON events
        indices_off (1d numpy.array): Unique indices which maps the pixel location of the camera to the 1D neuron indices of OFF events
        ts_off (1d numpy.array): Unique timestamps of active indices of OFF events
    """
    if event_directory is not None:
        assert type(event_directory) == str, 'event_directory must be a string'
        assert event_directory[
            -4:] == '.npy', 'Please specify a numpy array (.npy) which contains the DVS events.\n Aedat files can be converted using function aedat2numpy.py'
        Events = np.load(event_directory)
    if Events is not None:
        assert event_directory is None, 'Either you specify a path to load Events using event_directory. Or you pass the event numpy directly. NOT Both.'
    if np.size(Events, 0) > np.size(Events, 1):
        Events = np.transpose(Events)

    # extract tempory indices to retrieve
    # Boolean logic to get indices of on and off events, respectively
    cInd_on = Events[3, :] == 1
    cInd_off = Events[3, :] == 0

    # Initialize 1D arrays for neuron indices and timestamps
    indices_on = np.zeros([int(np.sum(cInd_on))])
    spiketimes_on = np.zeros([int(np.sum(cInd_on))])
    # Polarity is either 0 or 1 so the entire length minus the sum of the
    # polarity give the proportion of off events
    indices_off = np.zeros([int(np.sum(cInd_off))])
    spiketimes_off = np.zeros([int(np.sum(cInd_off))])

    if type(resolution) == str:
        # extract the x-resolution (i.e. the resolution along the x-axis of the
        # camera)
        resolution = int(resolution[-3:])

    # The equation below follows index = x + y*resolution
    # To retrieve the x and y coordinate again from the index see ind2px
    indices_on = Events[0, cInd_on] + Events[1, cInd_on] * resolution
    indices_off = Events[0, cInd_off] + Events[1, cInd_off] * resolution
    if scale:
        # The DVS timestamps are in microseconds. We need to convert them to
        # milliseconds for brian
        spiketimes_on = np.ceil(Events[2, cInd_on] * 10**(-3))
        spiketimes_off = np.ceil(Events[2, cInd_off] * 10**(-3))

    else:
        # The flag scale is used to prevent rescaling of timestamps if we use
        # artifically generated stimuli
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

        doubleEntries = np.logical_and(np.logical_and(
            ts_on_tmp >= mask_t, ts_on_tmp <= mask_t + delta_t), mask_i == ind_on_tmp)
        # uniqueEntries = np.invert(doubleEntries)
        # print np.sum(doubleEntries)
        if np.sum(doubleEntries) > 1:
            # Find first occurence on non-unique entries
            tmp = np.where(doubleEntries == True)
            # keep the first occurance of non-unique entry
            doubleEntries[tmp[0][0]] = False
            uniqueEntries = np.invert(doubleEntries)
            ts_on_tmp = ts_on_tmp[uniqueEntries]
            ind_on_tmp = ind_on_tmp[uniqueEntries]

    for i in range(len(spiketimes_off)):
        mask_t = spiketimes_off[i]
        mask_i = indices_off[i]

        doubleEntries = np.logical_and(np.logical_and(
            ts_off_tmp >= mask_t, ts_off_tmp <= mask_t + delta_t), mask_i == ind_off_tmp)
        # uniqueEntries = np.invert(doubleEntries)
        # print np.sum(doubleEntries)
        if np.sum(doubleEntries) > 1:
            # Find first occurence on non-unique entries
            tmp = np.where(doubleEntries == True)
            # keep the first occurance of non-unique entry
            doubleEntries[tmp[0][0]] = False
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


def dvs_csv2numpy(datafile='tmp/aerout.csv', debug=False):
    """
    load AER csv logfile and parse these properties of AE events:
        - timestamps (in us),
        - x,y-position [0..127]
        - polarity (0/1)

    Args:
        datafile (str, optional): path to the csv file to read
        debug (bool, optional): Flag to print more details about conversion.

    Returns:
        numpy.ndarray: (ts, xpos, ypos, pol) 4D numpy array containing data of all events

    Deleted Parameters:
        exp_name (str, optional): Description
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
