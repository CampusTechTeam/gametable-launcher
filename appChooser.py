#!/usr/bin/env python
# Copyright (C) 2009
#    Martin Heistermann, <mh at sponc dot de>
#
# appChooser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# appChooser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with appChooser.  If not, see <http://www.gnu.org/licenses/>.

import config
from libavg import avg, Point2D, anim
from libavg.mathutil import getScaledDim, getOffsetForMovedPivot

from libavg import AVGMTAppStarter, AVGAppStarter, AVGApp

import math
import os
import sys
import random

g_player = avg.Player.get()

class AppChooser (AVGApp):
    def __init__(self, parentNode):
        self.__parentNode = parentNode
        parentNode.mediadir="media/"

        bgNode = g_player.createNode('image', {
            'href': "bgpixel.png"})
        bgNode.size = parentNode.size
        parentNode.appendChild(bgNode)

        self.__gridNode = g_player.createNode('div', {})
        self.__gridNode.size = parentNode.size
        parentNode.appendChild(self.__gridNode)

        self.__appsNode = g_player.createNode('div', {
            'sensitive': False})
        self.__appsNode.size = parentNode.size
        parentNode.appendChild(self.__appsNode)

        self.__loadApps(self.__appsNode)
        self.__createGrid()

    def __loadApps(self, parentNode):
        appDirs = []
        def handleEntry(maindir, dirname, fname):
            if maindir == dirname: # only top-level
                appDirs.extend([name for name in fname if name[0] != '.'])
            while len(fname):
                del fname[0]

        os.path.walk(config.appDir, handleEntry, config.appDir)
        oldSysPath = sys.path
        sys.path.insert(0, config.appDir)

        self.__apps = {}
        for appName in appDirs:
            print "loading app ", appName
            appModule = __import__(appName)

            for app in appModule.apps:
                appNode = g_player.createNode('div', {
                    'opacity': 0,
                    'sensitive': False,
                    'active': False,
                    })
                appNode.size = self.__appsNode.size
                self.__appsNode.appendChild(appNode)

                appInstance = app['class'](appNode)

                self.__apps[appName] = {
                        'createPreviewNode': app['createPreviewNode'],
                        'instance': appInstance,
                        'node': appNode,
                        }

        sys.path = oldSysPath

    def __createGrid(self):
        gridResolution = int(math.ceil(math.sqrt(len(self.__apps))))
        print "grid resolution: ", gridResolution

        paddedCellSize = self.__parentNode.size / gridResolution
        cellSize = paddedCellSize - 2 * config.cellPadding

        def appNameGenerator():
            for appName in self.__apps:
                yield appName
        appNames = appNameGenerator()
        appIndex = 0 # ugly but readable
        for y in xrange(gridResolution):
            for x in xrange(gridResolution):
                try:
                    appName = appNames.next()
                except StopIteration:
                    continue
                app = self.__apps[appName]

                node = app['createPreviewNode'](maxSize = cellSize)
                node.size = getScaledDim(node.size, max = cellSize)

                node.pos = Point2D(
                        x * paddedCellSize.x,
                        y * paddedCellSize.y
                        ) + (paddedCellSize - node.size)/2

                self.__gridNode.appendChild(node)
                self.__apps[appName]['previewNode'] = node

                node.setEventHandler(avg.CURSORDOWN, avg.MOUSE | avg.TOUCH,
                        lambda event, appName=appName: self.onCellClick(event, appName))

    def onCellClick(self, event, appName):
        print "switching to", appName
        app = self.__apps[appName]
        previewNode = app['previewNode']
        appNode = app['node']

        def disableApp():
            appNode.sensitive = False
            appNode.active = False
            self.__appsNode.sensitive = False

        def disableGrid():
            self.__gridNode.sensitive = False
            self.__gridNode.active = False

        appNode.sensitive = True
        appNode.active = True
        self.__appsNode.sensitive = True

        parent= previewNode.getParent()
        parent.reorderChild(previewNode, parent.getNumChildren() - 1)
        zoomAnim = createRandomZoomAnim(previewNode, appNode)

        def zoomOut():
            self.__gridNode.sensitive = True
            self.__gridNode.active = True
            zoomAnim.zoomOut(onDone = disableApp)

        app['instance'].enter(onLeave = zoomOut)
        zoomAnim.zoomIn(onDone = disableGrid)

def getNodeParams(node):
    params = {}
    for paramName in ('pos','size','angle','pivot'):
        params[paramName] = getattr(node, paramName)
    return params

class ZoomAnimBase(object):
    def __init__(self, previewNode, appNode):
        if self.__class__ == ZoomAnimBase:
            assert False
        self._previewNode = previewNode
        self._appNode = appNode
        self._backupPreviewNode()
        self._backupAppNode()

    def _backupPreviewNode(self):
        self._previewNodeParams = getNodeParams(self._previewNode)

    def _backupAppNode(self):
        self._appNodeParams = getNodeParams(self._appNode)

    def zoomIn(self, onDone):
        pass

    def zoomOut(self, onDone):
        pass

class ZoomAnimSimple(ZoomAnimBase):
    scaleDuration = 300
    fadeDuration = 600
    def _fadeToApp(self, onDone):
        anim.fadeIn(self._appNode,
                ZoomAnimSimple.fadeDuration,
                onStop = onDone)
    def zoomIn(self, onDone = lambda: None):
        # TODO: non-linear?
        for attr, target in (
                ('pos', Point2D(0,0)),
                ('size', self._appNode.size),
                ):
            anim.LinearAnim(self._previewNode,
                    attr,
                    ZoomAnimRotate.scaleDuration,
                    getattr(self._previewNode, attr),
                    target)

        g_player.setTimeout(ZoomAnimRotate.scaleDuration,
                lambda: self._fadeToApp(onDone))

    def _zoomOut(self, onDone):
        for attr in ('pos', 'size'):
            anim.LinearAnim(self._previewNode,
                    attr,
                    ZoomAnimSimple.scaleDuration,
                    getattr(self._previewNode, attr),
                    self._previewNodeParams[attr])
        g_player.setTimeout(ZoomAnimSimple.scaleDuration, onDone)
    def zoomOut(self, onDone):
        anim.fadeOut(self._appNode,
                ZoomAnimSimple.fadeDuration,
                onStop = lambda: self._zoomOut(onDone))

class ZoomAnimRotate(ZoomAnimSimple):
    def zoomIn(self, onDone = lambda: None):
        newPivot = self._previewNode.size / 2
        self._previewNode.pos += getOffsetForMovedPivot(
                oldPivot = self._previewNode.pivot,
                newPivot = newPivot,
                angle = self._previewNode.angle)

        anim.LinearAnim(self._previewNode,
                'angle',
                ZoomAnimRotate.scaleDuration,
                self._previewNode.angle,
                self._appNode.angle + 2*math.pi)

        super(ZoomAnimRotate,self).zoomIn(onDone)
    def _zoomOut(self, onDone):
        anim.LinearAnim(self._previewNode,
                'angle',
                ZoomAnimRotate.scaleDuration,
                self._previewNode.angle,
                self._previewNodeParams['angle'] - 2 * math.pi)
        super(ZoomAnimRotate,self)._zoomOut(onDone)

def createRandomZoomAnim(*args, **kwargs):
    """ ZoomAnim factory."""
    # TODO: random anim
    klasses = (ZoomAnimRotate, ZoomAnimSimple)
    klass = random.choice(klasses)
    #klass = ZoomAnimRotate
    return klass(*args, **kwargs)

if __name__ == '__main__':
    AVGMTAppStarter(appClass = AppChooser, resolution = config.resolution)
    #AVGAppStarter(app = AppChooser, resolution = config.resolution)



