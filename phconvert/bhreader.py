#
# phconvert - Convert files to Photon-HDF5 format
#
# Copyright (C) 2014-2015 Antonino Ingargiola <tritemio@gmail.com>
#
"""
SPC Format (Beker & Hickl)
--------------------------

48-bit element in little endian (<) format

Drawing (note: each char represents 2 bits)::

    bit: 64        48                          0
         0000 0000 XXXX XXXX XXXX XXXX XXXX XXXX
                   '-------' '--' '--'   '-----'
    field names:       a      c    b        d

         0000 0000 XXXX XXXX XXXX XXXX XXXX XXXX
                   '-------' '--' '--' '-------'
    numpy dtype:       a      c    b    field0

    macrotime = [ b  ] [     a     ]  (24 bit)
    detector  = [ c  ]                (8 bit)
    nanotime  = [  d  ]               (12 bit)

    overflow bit: 13, bit_mask = 2^(13-1) = 4096
"""

import numpy as np


def load_spc(fname):
    """Load data from Becker & Hickl SPC files.

    Returns:
        3 numpy arrays: timestamps, detector, nanotime
    """
    spc_dtype = np.dtype([('field0', '<u2'), ('b', '<u1'), ('c', '<u1'),
                          ('a', '<u2')])
    data = np.fromfile(fname, dtype=spc_dtype)

    nanotime =  4095 - np.bitwise_and(data['field0'], 0x0FFF)
    detector = data['c']

    # Build the macrotime (timestamps) using in-place operation for efficiency
    timestamps = data['b'].astype('int64')
    np.left_shift(timestamps, 16, out=timestamps)
    timestamps += data['a']

    # extract the 13-th bit from data['field0']
    overflow = np.bitwise_and(np.right_shift(data['field0'], 13), 1)
    overflow = np.cumsum(overflow, dtype='int64')

    # Add the overflow bits
    timestamps += np.left_shift(overflow, 24)

    return timestamps, detector, nanotime


def load_set(fname_set):
    """Return a dict with data from the Becker & Hickl .SET file.
    """
    identification = bh_set_identification(fname_set)
    sys_params = bh_set_sys_params(fname_set)
    return dict(identification=identification, sys_params=sys_params)


def bh_set_identification(fname_set):
    """Return a dict containing the IDENTIFICATION section of .SET files.
    """
    with open(fname_set, 'rb') as f:
        line = f.readline()
        assert line.strip().endswith(b'IDENTIFICATION')
        identification = {}
        line = f.readline().strip()
        while not line.startswith(b'*END'):
            item = [s.strip() for s in line.split(':')]
            if len(item) == 1:
                value = ' '.join([identification[key], item[0]])
            else:
                key = item[0]
                value = ':'.join(item[1:])
            identification[key] = value
            line = f.readline().strip()
    return identification

def bh_set_sys_params(fname_set):
    """Return a dict containing the SYS_PARAMS section of .SET files.
    """
    with open(fname_set, 'rb') as f:
        ## Make a dictionary of system parameters
        start = False
        sys_params  = {}
        for line in f.readlines():
            line = line.strip()
            if line == 'SYS_PARA_BEGIN:':
                start = True
                continue
            if line == 'SYS_PARA_END:':
                break
            if start and line.startswith('#'):
                fields = line[5:-1].split(',')

                if fields[1] == 'B':
                    value = bool(fields[2])
                elif fields[1] in ['I', 'U', 'L']:
                    value = int(fields[2])
                elif fields[1] == 'F':
                    value = float(fields[2])
                elif fields[1] == 'S':
                    value = fields[2]
                else:
                    value = fields[1:]

                sys_params[fields[0]] = value
    return sys_params

def bh_decode(s):
    """Decode strings from Becker & Hickl system parameters (.SET file)."""
    s = s.replace('SP_', '')
    s = s.replace('_ZC', ' ZC Thresh.')
    s = s.replace('_LL', ' Limit Low')
    s = s.replace('_LH', ' Limit High')
    s = s.replace('_FD', ' Freq. Div.')
    s = s.replace('_OF', ' Offset')
    s = s.replace('_HF', ' Holdoff')
    s = s.replace('TAC_G', 'TAC Gain')
    s = s.replace('TAC_R', 'TAC Range')
    s = s.replace('_TC', ' Time/Chan')
    s = s.replace('_TD', ' Time/Div')
    s = s.replace('_FQ', ' Threshold')
    return s

def bh_print_sys_params(sys_params):
    """Print a summary of the Becker & Hickl system parameters (.SET file)."""
    for k, v in sys_params.iteritems():
        if 'TAC' in k: print '%s\t %f' % (bh_decode(k), v)
    print
    for k, v in sys_params.iteritems():
        if 'CFD' in k: print '%s\t %f' % (bh_decode(k), v)
    print
    for k, v in sys_params.iteritems():
        if 'SYN' in k: print '%s\t %f' % (bh_decode(k), v)

