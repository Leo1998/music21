# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Name:         meter.tools.py
# Purpose:      Tools for working with meter
#
# Authors:      Christopher Ariza
#               Michael Scott Cuthbert
#
# Copyright:    Copyright © 2009-2012, 2015, 2021 Michael Scott Cuthbert
#               and the music21 Project
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------
import collections
import fractions
import re
from typing import Optional, Tuple, List

from music21 import common
from music21 import environment
from music21.exceptions21 import MeterException, Music21Exception, TimeSignatureException

environLocal = environment.Environment('meter.tools')

MeterTerminalTuple = collections.namedtuple('MeterTerminalTuple',
                                            'numerator denominator tempoIndication')
NumDenomTuple = Tuple[int, int]
NumDenomTupleList = List[NumDenomTuple]


validDenominators = [1, 2, 4, 8, 16, 32, 64, 128]  # in order
validDenominatorsSet = set(validDenominators)


def slashToTuple(value: str) -> Optional[MeterTerminalTuple]:
    '''
    Returns a three-element MeterTerminalTuple of numerator, denominator, and optional
    tempo indication.

    >>> meter.tools.slashToTuple('3/8')
    MeterTerminalTuple(numerator=3, denominator=8, tempoIndication=None)
    >>> meter.tools.slashToTuple('7/32')
    MeterTerminalTuple(numerator=7, denominator=32, tempoIndication=None)
    >>> meter.tools.slashToTuple('slow 6/8')
    MeterTerminalTuple(numerator=6, denominator=8, tempoIndication='slow')
    '''
    tempoIndication = None
    # split by numbers, include slash
    valueNumbers, valueChars = common.getNumFromStr(value,
                                                    numbers='0123456789/')
    valueNumbers = valueNumbers.strip()  # remove whitespace
    valueChars = valueChars.strip()  # remove whitespace
    if 'slow' in valueChars.lower():
        tempoIndication = 'slow'
    elif 'fast' in valueChars.lower():
        tempoIndication = 'fast'

    matches = re.match(r'(\d+)/(\d+)', valueNumbers)
    if matches is not None:
        n = int(matches.group(1))
        d = int(matches.group(2))
        return MeterTerminalTuple(n, d, tempoIndication)
    else:
        environLocal.printDebug(['slashToTuple() cannot find two part fraction', value])
        return None


def slashCompoundToFraction(value: str) -> NumDenomTupleList:
    '''
    Change a compount meter into a list of simple numberator, demoninator values

    >>> meter.tools.slashCompoundToFraction('3/8+2/8')
    [(3, 8), (2, 8)]
    >>> meter.tools.slashCompoundToFraction('5/8')
    [(5, 8)]
    >>> meter.tools.slashCompoundToFraction('5/8+2/4+6/8')
    [(5, 8), (2, 4), (6, 8)]
    '''
    post = []
    value = value.strip()  # rem whitespace
    value = value.split('+')
    for part in value:
        m = slashToTuple(part)
        if m is None:
            pass
        else:
            post.append((m.numerator, m.denominator))
    return post


def slashMixedToFraction(valueSrc: str) -> Tuple[NumDenomTupleList, bool]:
    '''
    Given a mixture if possible meter fraction representations, return a list
    of pairs. If originally given as a summed numerator; break into separate
    fractions and return True as the second element of the tuple

    >>> meter.tools.slashMixedToFraction('4/4')
    ([(4, 4)], False)

    >>> meter.tools.slashMixedToFraction('3/8+2/8')
    ([(3, 8), (2, 8)], False)

    >>> meter.tools.slashMixedToFraction('3+2/8')
    ([(3, 8), (2, 8)], True)

    >>> meter.tools.slashMixedToFraction('3+2+5/8')
    ([(3, 8), (2, 8), (5, 8)], True)

    >>> meter.tools.slashMixedToFraction('3+2+5/8+3/4')
    ([(3, 8), (2, 8), (5, 8), (3, 4)], True)

    >>> meter.tools.slashMixedToFraction('3+2+5/8+3/4+2+1+4/16')
    ([(3, 8), (2, 8), (5, 8), (3, 4), (2, 16), (1, 16), (4, 16)], True)

    >>> meter.tools.slashMixedToFraction('3+2+5/8+3/4+2+1+4')
    Traceback (most recent call last):
    music21.exceptions21.MeterException: cannot match denominator to numerator in: 3+2+5/8+3/4+2+1+4
    '''
    pre = []
    post = []
    summedNumerator = False
    value = valueSrc.strip()  # rem whitespace
    value = value.split('+')
    for part in value:
        if '/' in part:
            tup = slashToTuple(part)
            if tup is None:
                raise TimeSignatureException('cannot create time signature from:', valueSrc)
            pre.append([tup.numerator, tup.denominator])
        else:  # its just a numerator
            try:
                pre.append([int(part), None])
            except ValueError:
                raise Music21Exception(
                    'Cannot parse this file -- this error often comes '
                    + 'up if the musicxml pickled file is out of date after a change '
                    + 'in musicxml/__init__.py . '
                    + 'Clear your temp directory of .p and .p.gz files and try again...; '
                    + f'Time Signature: {valueSrc} ')

    # when encountering a missing denominator, find the first defined
    # and apply to all previous
    for i in range(len(pre)):
        if pre[i][1] is not None:  # there is a denominator
            post.append(tuple(pre[i]))
        else:  # search ahead for next defined denominator
            summedNumerator = True
            match = None
            for j in range(i, len(pre)):
                if pre[j][1] is not None:
                    match = pre[j][1]
                    break
            if match is None:
                raise MeterException(f'cannot match denominator to numerator in: {valueSrc}')

            pre[i][1] = match
            post.append(tuple(pre[i]))

    return post, summedNumerator


def fractionToSlashMixed(fList: NumDenomTupleList) -> List[Tuple[str, int]]:
    '''
    Given a list of fraction values, compact numerators by sum if denominators
    are the same

    >>> from music21.meter.tools import fractionToSlashMixed
    >>> fractionToSlashMixed([(3, 8), (2, 8), (5, 8), (3, 4), (2, 16), (1, 16), (4, 16)])
    [('3+2+5', 8), ('3', 4), ('2+1+4', 16)]
    '''
    pre = []
    for i in range(len(fList)):
        n, d = fList[i]
        # look at previous fraction and determine if denominator is the same

        match = None
        search = list(range(len(pre)))
        search.reverse()  # go backwards
        for j in search:
            if pre[j][1] == d:
                match = j  # index to add numerator
                break
            else:
                break  # if not found in one less

        if match is None:
            pre.append([[n], d])
        else:  # append numerator
            pre[match][0].append(n)
    # create string representation
    post = []
    for part in pre:
        n = [str(x) for x in part[0]]
        n = '+'.join(n)
        d = part[1]
        post.append((n, d))

    return post


def fractionSum(fList: NumDenomTupleList) -> NumDenomTuple:
    '''
    Given a list of fractions represented as a list,
    find the sum; does NOT reduce to lowest terms.

    >>> from music21.meter.tools import fractionSum
    >>> fractionSum([(3, 8), (5, 8), (1, 8)])
    (9, 8)
    >>> fractionSum([(1, 6), (2, 3)])
    (5, 6)
    >>> fractionSum([(3, 4), (1, 2)])
    (5, 4)
    >>> fractionSum([(1, 13), (2, 17)])
    (43, 221)
    >>> fractionSum([])
    (0, 1)

    This method might seem like an easy place to optimize and simplify
    by just doing a fractions.Fraction() sum (I tried!), but not reducing to lowest
    terms is a feature of this method. 3/8 + 3/8 = 6/8, not 3/4:

    >>> fractionSum([(3, 8), (3, 8)])
    (6, 8)
    '''
    nList = []
    dList = []
    dListUnique = []

    for n, d in fList:
        nList.append(n)
        dList.append(d)
        if d not in dListUnique:
            dListUnique.append(d)

    if len(dListUnique) == 1:
        n = sum(nList)
        d = dListUnique[0]
        # Does not reduce to lowest terms...
        return (n, d)
    else:  # there might be a better way to do this
        d = 1
        d = common.lcm(dListUnique)
        # after finding d, multiply each numerator
        nShift = []
        for i in range(len(nList)):
            nSrc = nList[i]
            dSrc = dList[i]
            scalar = d // dSrc
            nShift.append(nSrc * scalar)
        return (sum(nShift), d)


def proportionToFraction(value: float) -> NumDenomTuple:
    '''
    Given a floating point proportional value between 0 and 1, return the
    best-fit slash-base fraction

    >>> from music21.meter.tools import proportionToFraction
    >>> proportionToFraction(0.5)
    (1, 2)
    >>> proportionToFraction(0.25)
    (1, 4)
    >>> proportionToFraction(0.75)
    (3, 4)
    >>> proportionToFraction(0.125)
    (1, 8)
    >>> proportionToFraction(0.375)
    (3, 8)
    >>> proportionToFraction(0.625)
    (5, 8)
    >>> proportionToFraction(0.333)
    (1, 3)
    >>> proportionToFraction(0.83333)
    (5, 6)
    '''
    f = fractions.Fraction(value).limit_denominator(16)
    return (f.numerator, f.denominator)


def divisionOptionsFractionsUpward(n, d, opts=None):
    '''
    This simply gets restatements of the same fraction in smaller units,
    up to the largest valid denominator.

    >>> meter.tools.divisionOptionsFractionsUpward(2, 4)
    [['4/8'], ['8/16'], ['16/32'], ['32/64'], ['64/128']]
    >>> meter.tools.divisionOptionsFractionsUpward(3, 4)
    [['6/8'], ['12/16'], ['24/32'], ['48/64'], ['96/128']]
    '''
    if opts is None:
        opts = []
    # equivalent fractions upward
    if d < validDenominators[-1]:
        nMod = n * 2
        dMod = d * 2
        while True:
            if dMod > validDenominators[-1]:
                break
            opts.append([f'{nMod}/{dMod}'])
            dMod = dMod * 2
            nMod = nMod * 2
    return opts

# -------------------------------------------------------------------------
# load common meter templates into this sequence

def divisionOptionsFractionsDownward(n, d, opts=None):
    '''
    Get restatements of the same fraction in larger units

    >>> meter.tools.divisionOptionsFractionsDownward(2, 4)
    [['1/2']]
    >>> meter.tools.divisionOptionsFractionsDownward(12, 16)
    [['6/8'], ['3/4']]
    '''
    if opts is None:
        opts = []
    if d > validDenominators[0] and n % 2 == 0:
        nMod = n // 2
        dMod = d // 2
        while True:
            if dMod < validDenominators[0]:
                break
            opts.append([f'{nMod}/{dMod}'])
            if nMod % 2 != 0:  # no longer even
                break
            dMod = dMod // 2
            nMod = nMod // 2
    return opts

def divisionOptionsAdditiveMultiplesDownward(n, d, opts=None):
    '''
    >>> meter.tools.divisionOptionsAdditiveMultiplesDownward(1, 16)
    [['1/32', '1/32'], ['1/64', '1/64', '1/64', '1/64'],
     ['1/128', '1/128', '1/128', '1/128', '1/128', '1/128', '1/128', '1/128']]
    '''
    if opts is None:
        opts = []
    # this only takes n == 1
    if d < validDenominators[-1] and n == 1:
        i = 2
        dMod = d * 2
        while True:
            if dMod > validDenominators[-1]:
                break
            seq = []
            for j in range(i):
                seq.append(f'{n}/{dMod}')
            opts.append(seq)
            dMod = dMod * 2
            i *= 2
    return opts

def divisionOptionsAdditiveMultiples(n, d, opts=None):
    '''
    Additive multiples with the same denominators.

    >>> meter.tools.divisionOptionsAdditiveMultiples(4, 16)
    [['2/16', '2/16']]
    >>> meter.tools.divisionOptionsAdditiveMultiples(6, 4)
    [['3/4', '3/4']]
    '''
    if opts is None:
        opts = []
    if n > 3 and n % 2 == 0:
        div = 2
        i = div
        nMod = n // div
        while True:
            if nMod <= 1:
                break
            seq = []
            for j in range(i):
                seq.append(f'{nMod}/{d}')
            if seq not in opts:  # may be cases defined elsewhere
                opts.append(seq)
            nMod = nMod // div
            i *= div
    return opts

def divisionOptionsAdditiveMultiplesEvenDivision(n, d, opts=None):
    '''
    >>> meter.tools.divisionOptionsAdditiveMultiplesEvenDivision(4, 16)
    [['1/8', '1/8']]
    >>> meter.tools.divisionOptionsAdditiveMultiplesEvenDivision(4, 4)
    [['1/2', '1/2']]
    >>> meter.tools.divisionOptionsAdditiveMultiplesEvenDivision(3, 4)
    []
    '''
    if opts is None:
        opts = []
        # divided additive multiples
    # if given 4/4, get 2/4+2/4
    if n % 2 == 0 and d // 2 >= 1:
        nMod = n // 2
        dMod = d // 2
        while True:
            if dMod < 1 or nMod <= 1:
                break
            seq = []
            for j in range(int(nMod)):
                seq.append(f'{1}/{dMod}')
            opts.append(seq)
            if nMod % 2 != 0:  # if no longer even must stop
                break
            dMod = dMod // 2
            nMod = nMod // 2
    return opts

def divisionOptionsAdditiveMultiplesUpward(n, d, opts=None):
    '''
    >>> meter.tools.divisionOptionsAdditiveMultiplesUpward(4, 16)
    [['1/16', '1/16', '1/16', '1/16'],
     ['1/32', '1/32', '1/32', '1/32', '1/32', '1/32', '1/32', '1/32'],
     ['1/64', '1/64', '1/64', '1/64', '1/64', '1/64', '1/64', '1/64',
      '1/64', '1/64', '1/64', '1/64', '1/64', '1/64', '1/64', '1/64']]
    >>> meter.tools.divisionOptionsAdditiveMultiplesUpward(3, 4)
    [['1/4', '1/4', '1/4'], ['1/8', '1/8', '1/8', '1/8', '1/8', '1/8'],
    ['1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16',
     '1/16', '1/16', '1/16', '1/16']]
    '''
    if opts is None:
        opts = []
    if n > 1 and d >= 1:
        dCurrent = d
        nCount = n
        if n > 16:  # go up to n if greater than 16
            nCountLimit = n
        else:
            nCountLimit = 16

        while True:
            # place practical limits on number of units to get
            if dCurrent > validDenominators[-1] or nCount > nCountLimit:
                break
            seq = []
            for j in range(nCount):
                seq.append(f'{1}/{dCurrent}')
            opts.append(seq)
            # double count, double denominator
            dCurrent *= 2
            nCount *= 2
    return opts


def divisionOptionsAlgo(n, d):
    '''
    This is a primitive approach to algorithmic division production.
    This can be extended.

    It is assumed that these values are provided in order of priority

    >>> meter.tools.divisionOptionsAlgo(4, 4)
    [['1/4', '1/4', '1/4', '1/4'],
     ['1/8', '1/8', '1/8', '1/8', '1/8', '1/8', '1/8', '1/8'],
     ['1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16',
      '1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16'],
     ['1/2', '1/2'],
     ['4/4'],
     ['2/4', '2/4'],
     ['2/2'],
     ['1/1'],
     ['8/8'],
     ['16/16'],
     ['32/32'],
     ['64/64'],
     ['128/128']]

    >>> meter.tools.divisionOptionsAlgo(1, 4)
    [['1/4'],
     ['1/8', '1/8'],
     ['1/16', '1/16', '1/16', '1/16'],
     ['1/32', '1/32', '1/32', '1/32', '1/32', '1/32', '1/32', '1/32'],
     ['1/64', '1/64', '1/64', '1/64', '1/64', '1/64', '1/64', '1/64',
      '1/64', '1/64', '1/64', '1/64', '1/64', '1/64', '1/64', '1/64'],
     ['1/128', '1/128', '1/128', '1/128', '1/128', '1/128', '1/128', '1/128',
      '1/128', '1/128', '1/128', '1/128', '1/128', '1/128', '1/128', '1/128',
      '1/128', '1/128', '1/128', '1/128', '1/128', '1/128', '1/128', '1/128',
      '1/128', '1/128', '1/128', '1/128', '1/128', '1/128', '1/128', '1/128'],
     ['2/8'], ['4/16'], ['8/32'], ['16/64'], ['32/128']]

    >>> meter.tools.divisionOptionsAlgo(2, 2)
    [['1/2', '1/2'],
     ['1/4', '1/4', '1/4', '1/4'],
     ['1/8', '1/8', '1/8', '1/8', '1/8', '1/8', '1/8', '1/8'],
     ['1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16',
      '1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16'],
      ['2/2'], ['1/1'], ['4/4'], ['8/8'], ['16/16'], ['32/32'], ['64/64'], ['128/128']]

    >>> meter.tools.divisionOptionsAlgo(3, 8)
    [['1/8', '1/8', '1/8'], ['1/16', '1/16', '1/16', '1/16', '1/16', '1/16'],
     ['1/32', '1/32', '1/32', '1/32', '1/32', '1/32',
      '1/32', '1/32', '1/32', '1/32', '1/32', '1/32'],
     ['3/8'], ['6/16'], ['12/32'], ['24/64'], ['48/128']]

    >>> meter.tools.divisionOptionsAlgo(6, 8)
    [['3/8', '3/8'],
     ['1/8', '1/8', '1/8', '1/8', '1/8', '1/8'],
     ['1/16', '1/16', '1/16', '1/16', '1/16', '1/16',
      '1/16', '1/16', '1/16', '1/16', '1/16', '1/16'],
     ['1/4', '1/4', '1/4'], ['6/8'], ['3/4'], ['12/16'],
     ['24/32'], ['48/64'], ['96/128']]

    >>> meter.tools.divisionOptionsAlgo(12, 8)
    [['3/8', '3/8', '3/8', '3/8'],
     ['1/8', '1/8', '1/8', '1/8', '1/8', '1/8', '1/8', '1/8', '1/8', '1/8', '1/8', '1/8'],
     ['1/4', '1/4', '1/4', '1/4', '1/4', '1/4'],
     ['1/2', '1/2', '1/2'],
     ['12/8'], ['6/8', '6/8'],
     ['6/4'], ['3/2'], ['24/16'], ['48/32'], ['96/64'], ['192/128']]

    >>> meter.tools.divisionOptionsAlgo(5, 8)
    [['2/8', '3/8'], ['3/8', '2/8'], ['1/8', '1/8', '1/8', '1/8', '1/8'],
     ['1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16', '1/16'],
     ['5/8'], ['10/16'], ['20/32'], ['40/64'], ['80/128']]

    >>> meter.tools.divisionOptionsAlgo(18, 4)
    [['3/4', '3/4', '3/4', '3/4', '3/4', '3/4'],
     ['1/4', '1/4', '1/4', '1/4', '1/4', '1/4', '1/4', '1/4', '1/4', '1/4',
      '1/4', '1/4', '1/4', '1/4', '1/4', '1/4', '1/4', '1/4'],
     ['1/2', '1/2', '1/2', '1/2', '1/2', '1/2', '1/2', '1/2', '1/2'],
     ['18/4'],
     ['9/4', '9/4'],
     ['4/4', '4/4', '4/4', '4/4'],
     ['2/4', '2/4', '2/4', '2/4', '2/4', '2/4', '2/4', '2/4'],
     ['9/2'],
     ['36/8'],
     ['72/16'],
     ['144/32'],
     ['288/64'],
     ['576/128']]

    >>> meter.tools.divisionOptionsAlgo(3, 128)
    [['1/128', '1/128', '1/128'], ['3/128']]
    '''
    opts = []

    # compound meters; 6, 9, 12, 15, 18
    # 9/4, 9/2, 6/2 are all considered compound without d>4
    # if n % 3 == 0 and n > 3 and d > 4:
    if n % 3 == 0 and n > 3:
        nMod = n / 3
        seq = []
        for j in range(int(n / 3)):
            seq.append(f'{3}/{d}')
        opts.append(seq)
    # odd meters with common groupings
    if n == 5:
        for group in [[2, 3], [3, 2]]:
            seq = []
            for nMod in group:
                seq.append(f'{nMod}/{d}')
            opts.append(seq)
    if n == 7:
        for group in [[2, 2, 3], [3, 2, 2], [2, 3, 2]]:
            seq = []
            for nMod in group:
                seq.append(f'{nMod}/{d}')
            opts.append(seq)
    # not really necessary but an example of a possibility
    if n == 10:
        for group in [[2, 2, 3, 3]]:
            seq = []
            for nMod in group:
                seq.append(f'{nMod}/{d}')
            opts.append(seq)

    # simple additive options uses the minimum numerator of 1
    # given 3/4, get 1/4 three times
    divisionOptionsAdditiveMultiplesUpward(n, d, opts)
    # divided additive multiples
    # if given 4/4, get 2/4+2/4
    divisionOptionsAdditiveMultiplesEvenDivision(n, d, opts)
    # add src representation
    opts.append([f'{n}/{d}'])
    # additive multiples with the same denominators
    # add to opts in-place
    divisionOptionsAdditiveMultiples(n, d, opts)
    # additive multiples with smaller denominators
    # only doing this for numerators of 1 for now
    divisionOptionsAdditiveMultiplesDownward(n, d, opts)
    # equivalent fractions downward
    divisionOptionsFractionsDownward(n, d, opts)
    # equivalent fractions upward
    divisionOptionsFractionsUpward(n, d, opts)
    return opts

def divisionOptionsPreset(n, d):
    '''
    Provide fixed set of meter divisions that will not be easily
    obtained algorithmically.

    Currently does nothing except to allow partitioning 5/8 as 2/8, 2/8, 1/8 as a possibility
    (sim for 5/16, etc.)

    >>> meter.tools.divisionOptionsPreset(5, 8)
    [['2/8', '2/8', '1/8'], ['2/8', '1/8', '2/8']]

    >>> ms2 = meter.MeterSequence('5/32')
    >>> ms2._getOptions()
    [['2/32', '3/32'], ['3/32', '2/32'], ['1/32', '1/32', '1/32', '1/32', '1/32'],
     ['1/64', '1/64', '1/64', '1/64', '1/64', '1/64', '1/64', '1/64', '1/64', '1/64'],
     ['5/32'], ['10/64'], ['20/128'], ['2/32', '2/32', '1/32'], ['2/32', '1/32', '2/32']]
    '''
    opts = []
    if n == 5:
        opts.append([f'2/{d}', f'2/{d}', f'1/{d}'])
        opts.append([f'2/{d}', f'1/{d}', f'2/{d}'])
    return opts



if __name__ == '__main__':
    import music21
    music21.mainTest()
