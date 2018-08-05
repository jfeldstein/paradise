# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from PyQt5.QtCore import (QVariant,
                          QCoreApplication)

from qgis.core import (QgsField,
                       QgsPoint,
                       QgsFields,
                       QgsRaster,
                       QgsFeature,
                       QgsMessageLog,
                       QgsWkbTypes,
                       QgsGeometry,
                       QgsProcessing,
                       QgsFeatureSink,
                       QgsRasterLayer,
                       QgsVectorLayer,
                       QgsFeatureRequest,
                       QgsVectorFileWriter,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterExtent,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterFolderDestination)

from qgis.analysis import ( QgsRasterCalculator,
                            QgsRasterCalculatorEntry)

import qgis.utils

import processing
import os
from urllib.parse import quote

def chunks(l, t, n):
    a = []
    for e in l:
        a.append(e)
        if len(a) == n:
            yield a
            a = []
    yield a

class ExampleProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    SLOPE = 'SLOPE'
    SLOPE_CUTOFF = 'SLOPE_CUTOFF'
    POINT_SPACING = 'POINT_SPACING'
    EXTENT = 'EXTENT'
    OUTPUT_DIR = 'OUTPUT_DIR'
    CONCAVE_THRESHOLD = 'CONCAVE_THRESHOLD'


    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ExampleProcessingAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'basinfind'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Basin Finder')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Paradise')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'paradise'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Find basins where a lower area is at least partially bordered by inclined terrain")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.SLOPE,
                self.tr('Input Slopes')
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.SLOPE_CUTOFF,
                self.tr('Slope High-Pass Filter (0-???)'),
                QgsProcessingParameterNumber.Integer,
                0,
                False,
                0,
                90
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.POINT_SPACING,
                self.tr('Point Spacing'),
                QgsProcessingParameterNumber.Double,
                0.001,
                False,
                0.0001,
                0.001
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.CONCAVE_THRESHOLD,
                self.tr('Concave Hull Threshold Value'),
                QgsProcessingParameterNumber.Double,
                0.1,
                False,
                0.1,
                0.3
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_DIR,
                self.tr('Output Directory'),
                '/Users/jordan/Google_Drive/Desktop/Basins/'
            )
        )
        
        self.addParameter(
            QgsProcessingParameterExtent(
                self.EXTENT,
                self.tr('Extent'),
                None,
                False
            )
        )

    def processSlopeHighpassAlgorithm(self, INPUT_CUTOFF, INPUT_SLOPE, INPUT_EXTENT, OUTPUT_FILE, feedback):
        if (os.path.isfile(OUTPUT_FILE)):
            return 0

        ras = QgsRasterCalculatorEntry()
        ras.ref = 'slope@1'
        ras.raster = INPUT_SLOPE
        ras.bandNumber = 1

        entries = [
            ras
        ]

        calc = QgsRasterCalculator(
            'slope@1 >= {}'.format(INPUT_CUTOFF),
            OUTPUT_FILE,
            'GTiff',
            INPUT_EXTENT,
            ras.raster.width(),
            ras.raster.height(),
            entries
        )

        return calc.processCalculation()

    def processRegularPointsAlgorithm(self, INPUT_SPACING, INPUT_EXTENT, OUTPUT_FILE, feedback):
        pass
        # if (os.path.isfile(OUTPUT_FILE)):
        #     return 0

        # return processing.run('qgis:regularpoints', {
        #     'EXTENT': INPUT_EXTENT,
        #     'SPACING': INPUT_SPACING,
        #     'INSET': 0,
        #     'IS_SPACING': True,
        #     'RANDOMIZE': False,
        #     'CRS': 'ProjectCrs',
        #     'OUTPUT': OUTPUT_FILE
        # },
        #     feedback=feedback
        # )

    def processSampleRasterAlgorithm(self, pointSpacing, INPUT_EXTENT, SAMPLE_FILE, OUTPUT_FILE, feedback):
        if (os.path.isfile(OUTPUT_FILE)):
            return 0

        fields = QgsFields()
        fields.append(QgsField("slope", QVariant.Double))
        
        sampleLayer = QgsRasterLayer(SAMPLE_FILE, 'Reclassified Slope', 'gdal')

        #pointLayerPath = quote(INPUT_POINTS)
        #pointLayer = QgsVectorLayer(pointLayerPath, 'points', 'ogr')
        QgsMessageLog.logMessage('Now generate points: extent={} crs={}'.format(INPUT_EXTENT.toString(), sampleLayer.crs().description()))
        pointLayer = processing.run('qgis:regularpoints', {
            'EXTENT': INPUT_EXTENT,
            'SPACING': pointSpacing,
            'INSET': 0,
            'IS_SPACING': True,
            'RANDOMIZE': False,
            'CRS': sampleLayer.crs().description(),
            'OUTPUT': 'memory:'
        },
            feedback=feedback
        )['OUTPUT']

        #QgsMessageLog.logMessage("Points done!")
        #QgsMessageLog.logMessage("Now build sample points destination")
        sampledPointsLayerPath = OUTPUT_FILE
        sampledPointsLayer = QgsVectorFileWriter(
            sampledPointsLayerPath.replace(' ', "\ "),
            "utf-8",
            fields,
            QgsWkbTypes.Point,
            sampleLayer.crs(),
            "ESRI Shapefile"
        )
        
        result = sampledPointsLayer.hasError()
        QgsMessageLog.logMessage("INITIAL ERROR CHECK, CODE: {}, MSG: {}".format(result, sampledPointsLayer.errorMessage()))
        if result > 0:
            return result

        #QgsMessageLog.logMessage("Does writer have error? {}, {}".format(sampledPointsLayer.hasError(), sampledPointsLayer.errorMessage()))
        #QgsMessageLog.logMessage("Will sample {} points".format(pointLayer.featureCount()))

        count = pointLayer.featureCount()
        total = 100.0 / count if count else 0
        features = pointLayer.getFeatures(QgsFeatureRequest())
        current = 0
        featureGroups = chunks(features, count, 100)
        QgsMessageLog.logMessage("FEATURE COUNT: {}".format(count))
        for group in featureGroups:
            for feature in group:
                # Stop the algorithm if cancel button has been clicked
                #QgsMessageLog.logMessage("Current: {}".format(current))
                #QgsMessageLog.logMessage("Feature: {}".format(feature))
                if feedback.isCanceled():
                    break
                current = current + 1
                ident = sampleLayer.dataProvider().identify(feature.geometry().asPoint(), QgsRaster.IdentifyFormatValue)
                if (ident.results()[1]) is not None and int(ident.results()[1]) == 1:
                    out_point = QgsFeature(fields)
                    out_point.setGeometry(feature.geometry())
                    out_point.setAttribute('slope', ident.results()[1])
                    sampledPointsLayer.addFeature(out_point, QgsFeatureSink.FastInsert)

            # Update the progress bar
            feedback.setProgress(int(current * total))

        result = sampledPointsLayer.hasError()
        del sampledPointsLayer
        return result


    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
            
        OUTPUT_DIR = self.parameterAsString(
            parameters,
            self.OUTPUT_DIR,
            context
        )#.replace(' ', '\ ')

        ##
        #   Reclassify slope, applying high-pass filter
        ##
        slopeLayer = self.parameterAsRasterLayer(
            parameters,
            self.SLOPE,
            context
        )
        slopeCutoff = self.parameterAsInt(
            parameters,
            self.SLOPE_CUTOFF,
            context
        )
        
                
        INPUT_EXTENT = self.parameterAsExtent(
            parameters,
            self.EXTENT,
            context
        )
        
        if INPUT_EXTENT is None:
            INPUT_EXTENT = slopeLayer.extent()
        
        slopeProcessedFile = OUTPUT_DIR + 'slope_cutoff_at_{}.tif'.format(slopeCutoff)
        SLOPE_HIGHPASS_RESULT = self.processSlopeHighpassAlgorithm(slopeCutoff, slopeLayer, INPUT_EXTENT, slopeProcessedFile, feedback)

        if SLOPE_HIGHPASS_RESULT > 0:
            return {'SLOPE_FAIL': SLOPE_HIGHPASS_RESULT}


        ##
        #   Generate points onto which we'll map the reclassified slope values
        ##
        pointSpacing = self.parameterAsDouble(parameters, self.POINT_SPACING, context)
        pointProcessedFile = OUTPUT_DIR + 'points_spacing_{}.shp'.format(pointSpacing)
        # POINTS_RESULT = self.processRegularPointsAlgorithm(pointSpacing, INPUT_EXTENT, pointProcessedFile, feedback)

        # if POINTS_RESULT > 0:
        #     return {'POINTS_FAIL': POINTS_RESULT}

        ##
        #   Sample reclassified slope value to corresponding points
        ##
        sampleProcessedFile = OUTPUT_DIR + 'sampled_points_spacing_{}_cutoff_{}.shp'.format(pointSpacing, slopeCutoff)
        QgsMessageLog.logMessage("SAMPLE FILE LOCATION: {}".format(sampleProcessedFile))
        SAMPLE_RESULT = self.processSampleRasterAlgorithm(pointSpacing, INPUT_EXTENT, slopeProcessedFile, sampleProcessedFile, feedback)

        if SAMPLE_RESULT > 0:
            return {'SAMPLE_FAIL': SAMPLE_RESULT}


        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {
            'RESULT_SLOP_HIGHPASS': SLOPE_HIGHPASS_RESULT,
            #'RESULT_POINTS': POINTS_RESULT,
            'SAMPLE_RESULT': SAMPLE_RESULT,
            'OUTPUTS': {
                'SLOPE_CUTOFF': slopeProcessedFile,
                'POINT_SPACING': pointProcessedFile,
                'POINT_SAMPLE': sampleProcessedFile
            }
        }
