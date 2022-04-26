# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Name:         testDocumentation.py
# Purpose:      tests from or derived from the Documentation
#
# Authors:      Michael Scott Asato Cuthbert
#
# Copyright:    Copyright © 2010-2012 Michael Scott Asato Cuthbert and the music21 Project
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------
'''
Module to test all the code excerpts in the .rst files in the music21 documentation
and those generated by Jupyter Notebook.
'''
import time
import re
import os.path
import sys
import doctest
import io
from typing import Union

from collections import namedtuple
# noinspection PyPackageRequirements
from docutils.core import publish_doctree  # pylint: disable=import-error

import nbvalNotebook

from music21.exceptions21 import Music21Exception
from music21.test import testRunner


ModTuple = namedtuple('ModTuple', 'module fullModulePath moduleNoExtension autoGen')


class Unbuffered:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


class NoOutput:
    def __init__(self, streamSave):
        self.stream = streamSave

    def write(self, data):
        pass

    def release(self):
        return self.stream

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


sys.stdout = Unbuffered(sys.stdout)

skipModules = [
    'documenting.rst',  # contains info that screws up testing
]


def getDocumentationFromAutoGen(fullModulePath):

    def is_code_or_literal_block(node):
        if node.tagname != 'literal_block':
            return False
        classes = node.attributes['classes']
        if 'ipython-result' in classes:
            return True
        if 'code' in classes and 'python' in classes:
            return True
        return False


    with io.open(fullModulePath, 'r', encoding='utf-8') as f:
        contents = f.read()
    sys.stderr = NoOutput(sys.stderr)
    doctree = publish_doctree(contents)
    sys.stderr = sys.stderr.release()
    allCodeExpects = []
    lastCode = None

    for child in doctree.traverse(is_code_or_literal_block):
        childText = child.astext()
        if '#_DOCS_SHOW' in childText:
            continue
        if 'ipython-result' in child.attributes['classes']:
            childText = childText.strip()
            childText = testRunner.stripAddresses(childText, '...')
            if lastCode is not None:
                allCodeExpects.append((lastCode, childText))
                lastCode = None
        else:
            if lastCode not in (None, ""):
                allCodeExpects.append((lastCode, ""))
            lastCode = None  # unneeded but clear
            childTextSplit = childText.split('\n')
            if len(childTextSplit) == 0:
                continue
            childTextArray = [childTextSplit[0]]
            matchesShow = re.search(r'\.show\((.*)\)', childTextSplit[0])
            if matchesShow is not None and not matchesShow.group(1).startswith('t'):
                childTextArray = []
            if re.search(r'.plot\(.*\)', childTextSplit[0]):
                childTextArray = []

            if '#_RAISES_ERROR' in childTextSplit[0]:
                childTextArray = []
            if childTextSplit[0].startswith('%'):
                childTextArray = []

            for line in childTextSplit[1:]:  # split into multiple examples unless indented
                if '#_RAISES_ERROR' in childTextSplit[0]:
                    childTextArray = []
                elif re.search(r'.plot\(.*\)', childTextSplit[0]):
                    continue
                elif line.startswith('%'):
                    childTextArray = []
                elif line.startswith(' '):
                    matchesShow = re.search(r'\.show\((.*)\)', line)
                    if matchesShow is not None and not matchesShow.group(1).startswith('t'):
                        continue
                    else:
                        childTextArray.append(line)
                else:
                    lastCode = '\n'.join(childTextArray)
                    if lastCode not in (None, ""):
                        allCodeExpects.append((lastCode, ""))
                        lastCode = None
                    childTextArray = [line]
            lastCode = '\n'.join(childTextArray)

    return allCodeExpects


def getDocumentationFiles(runOne=False):
    '''
    returns a list of namedtuples for each module that should be run

    >>> from documentation import testDocumentation
    >>> testDocumentation.getDocumentationFiles()
    [ModTuple(module='index.rst', fullModulePath='...documentation/source/index.rst',
    moduleNoExtension='index', autoGen=False),
    ...]
    '''
    from music21 import common
    music21basedir = common.getRootFilePath()
    buildDocRstDir = music21basedir / 'documentation' / 'source'
    if not buildDocRstDir.exists():
        raise Music21Exception(
            "Cannot run tests on documentation because the rst files "
            + "in documentation/source do not exist")

    allModules = []
    for root, unused_dir_names, filenames in os.walk(str(buildDocRstDir)):
        for module in sorted(filenames):
            fullModulePath = os.path.join(root, module)
            if not module.endswith('.rst'):
                continue
            if module.startswith('module'):  # we have this already...
                continue
            if module in skipModules:
                continue
            if runOne is not False:
                runOne: str
                if not module.endswith(runOne):
                    continue

            with io.open(fullModulePath, 'r', encoding='utf-8') as f:
                incipit = f.read(1000)
                if 'AUTOMATICALLY GENERATED' in incipit:
                    autoGen = True
                else:
                    autoGen = False

            moduleNoExtension = module[:-4]
            modTuple = ModTuple(module, fullModulePath, moduleNoExtension, autoGen)
            allModules.append(modTuple)
    return allModules


def main(runOne: Union[str, bool] = False):
    if runOne is False:
        nbvalNotebook.runAll()
    totalTests = 0
    totalFailures = 0

    timeStart = time.time()
    unused_dtr = doctest.DocTestRunner(doctest.OutputChecker(),
                                verbose=False,
                                optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)

    for mt in getDocumentationFiles(runOne):
        # if 'examples' in mt.module:
        #     continue
        print(mt.module + ": ", end="")
        try:
            if mt.autoGen is False:
                (failCount, testCount) = doctest.testfile(
                    mt.fullModulePath,
                    module_relative=False,
                    optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
                )
            else:
                print('ipython/autogenerated; no tests')
                continue

                # ## this was an attempt to run the ipynb through the doctest, but
                # ## it required too many compromises in how we'd like to write a user's
                # ## guide -- i.e., dicts can change order, etc.  better just to
                # ## monthly run through the User's Guide line by line and update.
                # examples = getDocumentationFromAutoGen(mt.fullModulePath)
                # dt = doctest.DocTest([doctest.Example(e[0], e[1]) for e in examples], {},
                #                      mt.moduleNoExtension, mt.fullModulePath, 0, None)
                # (failCount, testCount) = dtr.run(dt)


            if failCount > 0:
                print(f"{mt.module} had {failCount} failures in {testCount} tests")
            elif testCount == 0:
                print("no tests")
            else:
                print(f"all {testCount} tests ran successfully")
            totalTests += testCount
            totalFailures += failCount
        except Exception as e:  # pylint: disable=broad-except
            print(f"failed miserably! {str(e)}")
            import traceback
            tb = traceback.format_exc()
            print(f"Here's the traceback for the exception: \n{tb}")


    elapsedTime = time.time() - timeStart
    print(f"Ran {totalTests} tests ({totalFailures} failed) in {elapsedTime:.4f} seconds")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        main()
    else:
        main(sys.argv[1])
    # main('usersGuide_02_notes.rst')
    # main('overviewPostTonal.rst')
