from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterCrs
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsExpression
import processing


class Catchment(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('startpoint', 'Start point(s)', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('network', 'Network', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber('isochronediametermeter', 'Isochrone diameter(meter)', type=QgsProcessingParameterNumber.Double, minValue=0, maxValue=5000, defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber('bufferdiameter', 'Buffer diameter', type=QgsProcessingParameterNumber.Double, defaultValue=0))
        self.addParameter(QgsProcessingParameterCrs('defaultcrs', 'Default CRS', defaultValue='EPSG:4326'))
        self.addParameter(QgsProcessingParameterCrs('projectedcrs', 'Projected CRS', defaultValue='EPSG:32756'))
        self.addParameter(QgsProcessingParameterFeatureSink('Catchment', 'Catchment', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))

 
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(6, model_feedback)
        results = {}
        outputs = {}

        # Snap geometries to layer
        alg_params = {
            'BEHAVIOR': 0,
            'INPUT': parameters['startpoint'],
            'REFERENCE_LAYER': parameters['network'],
            'TOLERANCE': 10,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['SnapGeometriesToLayer'] = processing.run('qgis:snapgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Service area (from layer)
        alg_params = {
            'DEFAULT_DIRECTION': 2,
            'DEFAULT_SPEED': 50,
            'DIRECTION_FIELD': None,
            'INCLUDE_BOUNDS': False,
            'INPUT': parameters['network'],
            'SPEED_FIELD': None,
            'START_POINTS': outputs['SnapGeometriesToLayer']['OUTPUT'],
            'STRATEGY': 0,
            'TOLERANCE': 0,
            'TRAVEL_COST': QgsExpression(' @isochronediametermeter - @bufferdiameter ').evaluate(),
            'VALUE_BACKWARD': '',
            'VALUE_BOTH': '',
            'VALUE_FORWARD': '',
            'OUTPUT_LINES': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ServiceAreaFromLayer'] = processing.run('qgis:serviceareafromlayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Reproject layer
        alg_params = {
            'INPUT': outputs['ServiceAreaFromLayer']['OUTPUT_LINES'],
            'TARGET_CRS': parameters['projectedcrs'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ReprojectLayer'] = processing.run('native:reprojectlayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Buffer
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': parameters['bufferdiameter'],
            'END_CAP_STYLE': 0,
            'INPUT': outputs['ReprojectLayer']['OUTPUT'],
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Buffer'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Delete holes
        alg_params = {
            'INPUT': outputs['Buffer']['OUTPUT'],
            'MIN_AREA': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DeleteHoles'] = processing.run('native:deleteholes', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Reproject layer
        alg_params = {
            'INPUT': outputs['DeleteHoles']['OUTPUT'],
            'TARGET_CRS': parameters['defaultcrs'],
            'OUTPUT': parameters['Catchment']
        }
        outputs['ReprojectLayer'] = processing.run('native:reprojectlayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Catchment'] = outputs['ReprojectLayer']['OUTPUT']
        return results

    def name(self):
        return 'Catchment'

    def displayName(self):
        return 'Catchment'

    def group(self):
        return 'Bahman'

    def groupId(self):
        return 'Bahman'

    def createInstance(self):
        return Catchment()
